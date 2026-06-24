"""
ACT score importer.

Expects an ACT score export CSV with columns similar to:
  Student ID, Registration Number, Test Date, Test Type,
  English Score, Mathematics Score, Reading Score, Science Score,
  Composite Score, Writing Score, ELA Score, STEM Score,
  English Percentile, Mathematics Percentile, Reading Percentile,
  Science Percentile, Composite Percentile

test_type defaults to "ACT" when absent; PreACT files should include
"PreACT" in the test_type column or filename.
"""

import csv
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.act import ACTScore
from app.models.student import Student

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


_COL_MAP: dict[str, str] = {
    "student_id":             "student_id_str",
    "registration_number":    "registration_number",
    "test_date":              "test_date_str",
    "test_type":              "test_type",
    "english_score":          "english_score",
    "mathematics_score":      "math_score",
    "math_score":             "math_score",          # alternate header
    "reading_score":          "reading_score",
    "science_score":          "science_score",
    "composite_score":        "composite_score",
    "writing_score":          "writing_score",
    "ela_score":              "ela_score",
    "stem_score":             "stem_score",
    "english_percentile":     "english_percentile",
    "mathematics_percentile": "math_percentile",
    "math_percentile":        "math_percentile",    # alternate header
    "reading_percentile":     "reading_percentile",
    "science_percentile":     "science_percentile",
    "composite_percentile":   "composite_percentile",
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
    logger.warning("Could not parse ACT date: %r", val)
    return None


def import_act_file(
    file_path: str | Path,
    db: Optional[Session] = None,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Parse an ACT CSV export and upsert scores into the database.

    The unique constraint is (student_id, test_date); multiple sittings on
    different dates are stored separately.

    Returns a summary dict: {imported, skipped, errors, not_found}.
    """
    path = Path(file_path)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    # Infer test type from filename as a fallback
    default_test_type = "PreACT" if "preact" in path.stem.lower() else "ACT"

    stats = {"imported": 0, "skipped": 0, "errors": 0, "not_found": 0}

    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError("CSV has no header row")

            header_map: dict[str, str] = {_norm(h): h for h in reader.fieldnames}

            for row_num, row in enumerate(reader, start=2):
                try:
                    data: dict = {}
                    for norm_col, field_name in _COL_MAP.items():
                        orig = header_map.get(norm_col)
                        # Don't overwrite a field already filled by an earlier alias
                        if field_name not in data or not data[field_name]:
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

                    existing = db.query(ACTScore).filter(
                        ACTScore.student_id == student.id,
                        ACTScore.test_date == test_date,
                    ).first()

                    score_obj = existing or ACTScore(
                        student_id=student.id,
                        test_date=test_date,
                    )

                    score_obj.test_type            = test_type
                    score_obj.registration_number  = data.get("registration_number") or None
                    score_obj.english_score        = _int_or_none(data.get("english_score", ""))
                    score_obj.math_score           = _int_or_none(data.get("math_score", ""))
                    score_obj.reading_score        = _int_or_none(data.get("reading_score", ""))
                    score_obj.science_score        = _int_or_none(data.get("science_score", ""))
                    score_obj.composite_score      = _int_or_none(data.get("composite_score", ""))
                    score_obj.writing_score        = _int_or_none(data.get("writing_score", ""))
                    score_obj.ela_score            = _int_or_none(data.get("ela_score", ""))
                    score_obj.stem_score           = _int_or_none(data.get("stem_score", ""))
                    score_obj.english_percentile   = _int_or_none(data.get("english_percentile", ""))
                    score_obj.math_percentile      = _int_or_none(data.get("math_percentile", ""))
                    score_obj.reading_percentile   = _int_or_none(data.get("reading_percentile", ""))
                    score_obj.science_percentile   = _int_or_none(data.get("science_percentile", ""))
                    score_obj.composite_percentile = _int_or_none(data.get("composite_percentile", ""))
                    score_obj.source_file          = path.name

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

    logger.info("ACT import complete: %s", stats)
    return stats
