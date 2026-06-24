"""
SAT score importer.

Expects a College Board score export CSV with columns similar to:
  Last Name, First Name, Middle Name, Student ID, Registration Number,
  Test Date, Test Type, Total Score, EBRW Score, Math Score,
  EBRW Percentile, Math Percentile, Total Percentile,
  Reading Test Score, Writing and Language Test Score, Math Test Score,
  Analysis in History/Social Studies Score, Analysis in Science Score

Column names are normalised to lowercase/underscored before matching so
minor header variations are handled gracefully.
"""

import csv
import io
import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.sat import SATScore
from app.models.student import Student

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column-name normalisation helpers
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """Lower-case, collapse whitespace to underscores, strip punctuation."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# Maps normalised CSV header → model field
_COL_MAP: dict[str, str] = {
    "student_id":                        "student_id_str",
    "registration_number":               "registration_number",
    "test_date":                         "test_date_str",
    "test_type":                         "test_type",
    "total_score":                       "total_score",
    "ebrw_score":                        "ebrw_score",
    "math_score":                        "math_score",
    "ebrw_percentile":                   "ebrw_percentile",
    "math_percentile":                   "math_percentile",
    "total_percentile":                  "total_percentile",
    "reading_test_score":                "reading_test_score",
    "writing_and_language_test_score":   "writing_test_score",
    "math_test_score":                   "math_test_score",
    "analysis_in_history_social_studies_score": "analysis_history_score",
    "analysis_in_science_score":         "analysis_science_score",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _int_or_none(val: str) -> Optional[int]:
    val = val.strip()
    if not val or val in ("-", "N/A", "n/a"):
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


def _parse_date(val: str) -> Optional[date]:
    """Accept MM/YYYY, YYYY-MM-DD, or Mon YYYY formats."""
    val = val.strip()
    if not val:
        return None
    for fmt in ("%m/%Y", "%Y-%m-%d", "%b %Y", "%B %Y", "%m/%d/%Y"):
        try:
            from datetime import datetime
            dt = datetime.strptime(val, fmt)
            return dt.date() if fmt != "%m/%Y" and fmt != "%b %Y" and fmt != "%B %Y" else date(dt.year, dt.month, 1)
        except ValueError:
            continue
    logger.warning("Could not parse date: %r", val)
    return None


# ---------------------------------------------------------------------------
# Public import function
# ---------------------------------------------------------------------------

def import_sat_file(
    file_path: str | Path,
    db: Optional[Session] = None,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Parse a SAT CSV export and upsert scores into the database.

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

            # Build a mapping from normalised header → original header
            header_map: dict[str, str] = {_norm(h): h for h in reader.fieldnames}

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Remap to intermediate dict using our canonical field names
                    data: dict = {}
                    for norm_col, field_name in _COL_MAP.items():
                        orig_header = header_map.get(norm_col)
                        data[field_name] = row.get(orig_header, "").strip() if orig_header else ""

                    student_id_str = data.get("student_id_str", "")
                    if not student_id_str:
                        logger.debug("Row %d: no student ID, skipping", row_num)
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

                    test_type = data.get("test_type") or "SAT"

                    # Upsert by (student_id, test_date, test_type)
                    existing = db.query(SATScore).filter(
                        SATScore.student_id == student.id,
                        SATScore.test_date == test_date,
                        SATScore.test_type == test_type,
                    ).first()

                    score_obj = existing or SATScore(
                        student_id=student.id,
                        test_date=test_date,
                        test_type=test_type,
                    )

                    score_obj.registration_number = data.get("registration_number") or None
                    score_obj.ebrw_score         = _int_or_none(data.get("ebrw_score", ""))
                    score_obj.math_score         = _int_or_none(data.get("math_score", ""))
                    score_obj.total_score        = _int_or_none(data.get("total_score", ""))
                    score_obj.ebrw_percentile    = _int_or_none(data.get("ebrw_percentile", ""))
                    score_obj.math_percentile    = _int_or_none(data.get("math_percentile", ""))
                    score_obj.total_percentile   = _int_or_none(data.get("total_percentile", ""))
                    score_obj.reading_test_score = _int_or_none(data.get("reading_test_score", ""))
                    score_obj.writing_test_score = _int_or_none(data.get("writing_test_score", ""))
                    score_obj.math_test_score    = _int_or_none(data.get("math_test_score", ""))
                    score_obj.analysis_history_score = _int_or_none(data.get("analysis_history_score", ""))
                    score_obj.analysis_science_score = _int_or_none(data.get("analysis_science_score", ""))
                    score_obj.source_file        = path.name

                    if not dry_run:
                        if existing is None:
                            db.add(score_obj)
                        db.commit()

                    stats["imported"] += 1

                except Exception as exc:  # noqa: BLE001
                    logger.error("Row %d: unexpected error — %s", row_num, exc, exc_info=True)
                    db.rollback()
                    stats["errors"] += 1

    finally:
        if close_db:
            db.close()

    logger.info("SAT import complete: %s", stats)
    return stats
