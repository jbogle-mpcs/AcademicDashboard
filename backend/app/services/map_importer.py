"""
MAP Growth score importer (NWEA).

Expects a CombinedDataFile or AssessmentResults CSV from NWEA.
Key columns (normalised):
  student_id, term_name, season, school_year, subject, test_date,
  rit_score, percentile, standard_error,
  lexile_low, lexile_high, quantile_low, quantile_high,
  norm_rit_mean, norm_percentile, growth_rit, projected_growth,
  met_projected_growth, grade_at_testing

NWEA exports include one row per student per subject per term.
"""

import csv
import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.map import MAPScore
from app.models.student import Student

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


_COL_MAP: dict[str, str] = {
    # Student identification
    "student_id":                    "student_id_str",
    "local_student_id":              "student_id_str",
    # Term / timing
    "term_name":                     "term_name",
    "season":                        "season",
    "school_year":                   "school_year",
    "test_start_date":               "test_date_str",
    "test_date":                     "test_date_str",
    # Subject
    "discipline":                    "subject",
    "subject":                       "subject",
    # Scores
    "test_rit_score":                "rit_score",
    "rit_score":                     "rit_score",
    "test_percentile":               "percentile",
    "percentile":                    "percentile",
    "test_standard_error":           "standard_error",
    "standard_error":                "standard_error",
    # Lexile / Quantile
    "lexile_min":                    "lexile_low",
    "lexile_low":                    "lexile_low",
    "lexile_max":                    "lexile_high",
    "lexile_high":                   "lexile_high",
    "quantile_min":                  "quantile_low",
    "quantile_low":                  "quantile_low",
    "quantile_max":                  "quantile_high",
    "quantile_high":                 "quantile_high",
    # Norms / growth
    "norm_mean_rit":                 "norm_rit_mean",
    "norm_rit_mean":                 "norm_rit_mean",
    "norm_percentile":               "norm_percentile",
    "conditional_growth_index":      "growth_rit",
    "growth_rit":                    "growth_rit",
    "typical_growth":                "projected_growth",
    "projected_growth":              "projected_growth",
    "met_projected_growth":          "met_projected_growth",
    # Grade
    "grade_level_tested":            "grade_at_testing",
    "grade_at_testing":              "grade_at_testing",
}


def _dec_or_none(val: str) -> Optional[Decimal]:
    val = val.strip()
    if not val or val in ("-", "N/A", "n/a"):
        return None
    try:
        return Decimal(val)
    except InvalidOperation:
        return None


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
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%Y", "%b %Y", "%B %Y"):
        try:
            dt = datetime.strptime(val, fmt)
            if fmt in ("%m/%Y", "%b %Y", "%B %Y"):
                return date(dt.year, dt.month, 1)
            return dt.date()
        except ValueError:
            continue
    logger.warning("Could not parse MAP date: %r", val)
    return None


def import_map_file(
    file_path: str | Path,
    db: Optional[Session] = None,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Parse an NWEA MAP CSV export and upsert scores into the database.

    Unique key: (student_id, term_name, subject, test_date).

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

            for row_num, row in enumerate(reader, start=2):
                try:
                    data: dict = {}
                    for norm_col, field_name in _COL_MAP.items():
                        orig = header_map.get(norm_col)
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

                    term_name = data.get("term_name", "").strip()
                    subject   = data.get("subject", "").strip()
                    if not term_name or not subject:
                        logger.warning("Row %d: missing term_name or subject, skipping", row_num)
                        stats["skipped"] += 1
                        continue

                    test_date = _parse_date(data.get("test_date_str", ""))
                    if test_date is None:
                        logger.warning("Row %d: invalid test date, skipping", row_num)
                        stats["errors"] += 1
                        continue

                    existing = db.query(MAPScore).filter(
                        MAPScore.student_id == student.id,
                        MAPScore.term_name == term_name,
                        MAPScore.subject == subject,
                        MAPScore.test_date == test_date,
                    ).first()

                    score_obj = existing or MAPScore(
                        student_id=student.id,
                        term_name=term_name,
                        subject=subject,
                        test_date=test_date,
                    )

                    score_obj.season             = data.get("season") or None
                    score_obj.school_year        = data.get("school_year") or None
                    score_obj.rit_score          = _dec_or_none(data.get("rit_score", ""))
                    score_obj.percentile         = _int_or_none(data.get("percentile", ""))
                    score_obj.standard_error     = _dec_or_none(data.get("standard_error", ""))
                    score_obj.lexile_low         = _int_or_none(data.get("lexile_low", ""))
                    score_obj.lexile_high        = _int_or_none(data.get("lexile_high", ""))
                    score_obj.quantile_low       = _int_or_none(data.get("quantile_low", ""))
                    score_obj.quantile_high      = _int_or_none(data.get("quantile_high", ""))
                    score_obj.norm_rit_mean      = _dec_or_none(data.get("norm_rit_mean", ""))
                    score_obj.norm_percentile    = _int_or_none(data.get("norm_percentile", ""))
                    score_obj.growth_rit         = _dec_or_none(data.get("growth_rit", ""))
                    score_obj.projected_growth   = _dec_or_none(data.get("projected_growth", ""))
                    score_obj.met_projected_growth = data.get("met_projected_growth") or None
                    score_obj.grade_at_testing   = _int_or_none(data.get("grade_at_testing", ""))
                    score_obj.source_file        = path.name

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

    logger.info("MAP import complete: %s", stats)
    return stats
