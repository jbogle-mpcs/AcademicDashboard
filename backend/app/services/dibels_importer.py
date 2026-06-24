"""
DIBELS 8 score importer (Amplify/University of Oregon).

Expects a student-level CSV export from the DIBELS Data System (DDS) or
Amplify mCLASS.  Each row represents one measure for one student in one
term.  Multiple measures per student per term are common.

Key columns (normalised):
  student_id, term_name, season, school_year, measure, score, accuracy,
  benchmark_status, percentile, grade_at_testing, test_date, edition
"""

import csv
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.dibels import DIBELSScore
from app.models.student import Student

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


_COL_MAP: dict[str, str] = {
    # Student
    "student_id":              "student_id_str",
    "local_student_id":        "student_id_str",
    # Term / timing
    "term_name":               "term_name",
    "benchmark_period":        "term_name",  # mCLASS alternate
    "season":                  "season",
    "school_year":             "school_year",
    "assessment_date":         "test_date_str",
    "test_date":               "test_date_str",
    "date":                    "test_date_str",
    # Measure
    "measure":                 "measure",
    "assessment_measure":      "measure",
    "composite_score_type":    "measure",   # some exports use this
    "edition":                 "edition",
    # Scores
    "score":                   "score",
    "composite_score":         "score",
    "accuracy":                "accuracy",
    "accuracy_percent":        "accuracy",
    "benchmark_status":        "benchmark_status",
    "benchmark_level":         "benchmark_status",
    "percentile":              "percentile",
    "national_percentile":     "percentile",
    # Grade
    "grade":                   "grade_at_testing",
    "grade_at_testing":        "grade_at_testing",
    "assessment_grade":        "grade_at_testing",
}

# DIBELSNext/DIBELS 8 measure abbreviations
_MEASURE_ALIASES: dict[str, str] = {
    "psf":   "PSF",
    "nwf_cls": "NWF-CLS",
    "nwf_wrc": "NWF-WRC",
    "nwf":   "NWF",
    "orf":   "ORF",
    "orf_accuracy": "ORF-Accuracy",
    "dorf":  "DORF",
    "dorf_accuracy": "DORF-Accuracy",
    "maze":  "Maze",
    "wrf":   "WRF",
    "lnf":   "LNF",
    "isf":   "ISF",
    "composite": "Composite",
}


def _clean_measure(raw: str) -> str:
    norm = _norm(raw)
    return _MEASURE_ALIASES.get(norm, raw.strip())


def _int_or_none(val: str) -> Optional[int]:
    val = val.strip()
    if not val or val in ("-", "N/A", "n/a", "--"):
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
    logger.warning("Could not parse DIBELS date: %r", val)
    return None


def _infer_season_from_term(term: str) -> Optional[str]:
    t = term.lower()
    if "fall" in t or "beginning" in t or "bog" in t:
        return "Fall"
    if "winter" in t or "middle" in t or "mog" in t:
        return "Winter"
    if "spring" in t or "end" in t or "eog" in t:
        return "Spring"
    return None


def import_dibels_file(
    file_path: str | Path,
    db: Optional[Session] = None,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Parse a DIBELS CSV export and upsert scores into the database.

    Unique key: (student_id, term_name, measure, test_date).

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
                    measure   = _clean_measure(data.get("measure", ""))
                    if not term_name or not measure:
                        logger.warning("Row %d: missing term_name or measure, skipping", row_num)
                        stats["skipped"] += 1
                        continue

                    test_date = _parse_date(data.get("test_date_str", ""))
                    if test_date is None:
                        logger.warning("Row %d: invalid test date, skipping", row_num)
                        stats["errors"] += 1
                        continue

                    existing = db.query(DIBELSScore).filter(
                        DIBELSScore.student_id == student.id,
                        DIBELSScore.term_name == term_name,
                        DIBELSScore.measure == measure,
                        DIBELSScore.test_date == test_date,
                    ).first()

                    score_obj = existing or DIBELSScore(
                        student_id=student.id,
                        term_name=term_name,
                        measure=measure,
                        test_date=test_date,
                    )

                    season = data.get("season") or _infer_season_from_term(term_name)
                    score_obj.season           = season
                    score_obj.school_year      = data.get("school_year") or None
                    score_obj.edition          = data.get("edition") or "DIBELS 8"
                    score_obj.score            = _int_or_none(data.get("score", ""))
                    score_obj.accuracy         = _int_or_none(data.get("accuracy", ""))
                    score_obj.benchmark_status = data.get("benchmark_status") or None
                    score_obj.percentile       = _int_or_none(data.get("percentile", ""))
                    score_obj.grade_at_testing = _int_or_none(data.get("grade_at_testing", ""))
                    score_obj.source_file      = path.name

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

    logger.info("DIBELS import complete: %s", stats)
    return stats
