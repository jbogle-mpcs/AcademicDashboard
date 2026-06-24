"""
PSAT/NMSQT score importer.

Expects a College Board PSAT export CSV.  The test_type column (or filename)
distinguishes PSAT 8/9, PSAT 10, and PSAT/NMSQT.  All three share the same
schema so they are stored in the same table differentiated by test_type.

Expected columns (normalised):
  student_id, registration_number, test_date, test_type,
  total_score, ebrw_score, math_score,
  ebrw_percentile, math_percentile, total_percentile,
  reading_test_score, writing_and_language_test_score, math_test_score,
  selection_index
"""

import csv
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.psat import PSATScore
from app.models.student import Student

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


_COL_MAP: dict[str, str] = {
    "student_id":                       "student_id_str",
    "registration_number":              "registration_number",
    "test_date":                        "test_date_str",
    "test_type":                        "test_type",
    "total_score":                      "total_score",
    "ebrw_score":                       "ebrw_score",
    "math_score":                       "math_score",
    "ebrw_percentile":                  "ebrw_percentile",
    "math_percentile":                  "math_percentile",
    "total_percentile":                 "total_percentile",
    "reading_test_score":               "reading_test_score",
    "writing_and_language_test_score":  "writing_test_score",
    "math_test_score":                  "math_test_score",
    "selection_index":                  "selection_index",
}


def _int_or_none(val: str) -> Optional[int]:
    val = val.strip()
    if not val or val in ("-", "N/A", "n/a"):
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


def _parse_date(val: str) -> Optional[date]:
    val = val.strip()
    if not val:
        return None
    for fmt in ("%m/%Y", "%Y-%m-%d", "%b %Y", "%B %Y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(val, fmt)
            if fmt in ("%m/%Y", "%b %Y", "%B %Y"):
                return date(dt.year, dt.month, 1)
            return dt.date()
        except ValueError:
            continue
    logger.warning("Could not parse PSAT date: %r", val)
    return None


def _infer_test_type(path: Path) -> str:
    """Guess test_type from the filename when the column is absent."""
    name = path.stem.upper()
    if "89" in name or "8_9" in name or "89" in name:
        return "PSAT 8/9"
    if "10" in name:
        return "PSAT 10"
    return "PSAT/NMSQT"


def import_psat_file(
    file_path: str | Path,
    db: Optional[Session] = None,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Parse a PSAT CSV export and upsert scores into the database.

    Returns a summary dict: {imported, skipped, errors, not_found}.
    """
    path = Path(file_path)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    stats = {"imported": 0, "skipped": 0, "errors": 0, "not_found": 0}

    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError("CSV has no header row")

            header_map: dict[str, str] = {_norm(h): h for h in reader.fieldnames}
            default_test_type = _infer_test_type(path)

            for row_num, row in enumerate(reader, start=2):
                try:
                    data: dict = {}
                    for norm_col, field_name in _COL_MAP.items():
                        orig = header_map.get(norm_col)
                        data[field_name] = row.get(orig, "").strip() if orig else ""

                    student_id_str = data.get("student_id_str", "")
                    if not student_id_str:
                        stats["skipped"] += 1
                        continue

                    student = db.query(Student).filter(
                        Student.student_id == student_id_str
                    ).first()
                    if student is None:
                        logger.warning("Row %d: student %r not found", row_num, student_id_str)
                        stats["not_found"] += 1
                        continue

                    test_date = _parse_date(data.get("test_date_str", ""))
                    if test_date is None:
                        logger.warning("Row %d: invalid test date, skipping", row_num)
                        stats["errors"] += 1
                        continue

                    test_type = data.get("test_type") or default_test_type

                    existing = db.query(PSATScore).filter(
                        PSATScore.student_id == student.id,
                        PSATScore.test_date == test_date,
                        PSATScore.test_type == test_type,
                    ).first()

                    score_obj = existing or PSATScore(
                        student_id=student.id,
                        test_date=test_date,
                        test_type=test_type,
                    )

                    score_obj.registration_number = data.get("registration_number") or None
                    score_obj.ebrw_score          = _int_or_none(data.get("ebrw_score", ""))
                    score_obj.math_score          = _int_or_none(data.get("math_score", ""))
                    score_obj.total_score         = _int_or_none(data.get("total_score", ""))
                    score_obj.ebrw_percentile     = _int_or_none(data.get("ebrw_percentile", ""))
                    score_obj.math_percentile     = _int_or_none(data.get("math_percentile", ""))
                    score_obj.total_percentile    = _int_or_none(data.get("total_percentile", ""))
                    score_obj.reading_test_score  = _int_or_none(data.get("reading_test_score", ""))
                    score_obj.writing_test_score  = _int_or_none(data.get("writing_test_score", ""))
                    score_obj.math_test_score     = _int_or_none(data.get("math_test_score", ""))
                    score_obj.selection_index     = _int_or_none(data.get("selection_index", ""))
                    score_obj.source_file         = path.name

                    if not dry_run:
                        if existing is None:
                            db.add(score_obj)
                        db.commit()

                    stats["imported"] += 1

                except Exception as exc:  # noqa: BLE001
                    logger.error("Row %d: %s", row_num, exc, exc_info=True)
                    db.rollback()
                    stats["errors"] += 1

    finally:
        if close_db:
            db.close()

    logger.info("PSAT import complete: %s", stats)
    return stats
