"""
Canvas LMS sync service.

Pulls courses and student enrollments from the Canvas REST API and upserts
them into the local database.  Designed to be called from the Celery beat
scheduler (canvas_sync task) but can also be invoked directly.

Environment / settings required:
    CANVAS_BASE_URL  — e.g. https://canvas.yourschool.edu
    CANVAS_TOKEN     — admin API token
    CANVAS_ACCOUNT_ID (optional, defaults to 1)
"""

import logging
from datetime import date, datetime
from typing import Any, Optional

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models.canvas import CanvasCourse, CanvasEnrollment
from app.models.student import Student

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_DEFAULT_ACCOUNT_ID = getattr(settings, "CANVAS_ACCOUNT_ID", 1)


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.CANVAS_TOKEN}"}


def _get_paginated(url: str, params: Optional[dict] = None) -> list[dict]:
    """Follow Canvas Link: header pagination and collect all results."""
    results: list[dict] = []
    params = params or {}
    params.setdefault("per_page", 100)

    while url:
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        resp.raise_for_status()
        results.extend(resp.json())
        # Canvas uses RFC 5988 Link headers for pagination
        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
                break
        url = next_url  # type: ignore[assignment]
        params = {}     # params are already embedded in the next URL

    return results


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Course sync
# ---------------------------------------------------------------------------

def sync_courses(
    db: Optional[Session] = None,
    *,
    account_id: int = _DEFAULT_ACCOUNT_ID,
    enrollment_term_id: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """
    Fetch all courses for the given account and upsert into canvas_courses.

    Returns {upserted, skipped, errors}.
    """
    close_db = db is None
    if db is None:
        db = SessionLocal()

    stats: dict[str, int] = {"upserted": 0, "skipped": 0, "errors": 0}

    try:
        url = f"{settings.CANVAS_BASE_URL}/api/v1/accounts/{account_id}/courses"
        params: dict[str, Any] = {
            "include[]": ["term", "total_students"],
            "state[]":   ["available", "completed"],
        }
        if enrollment_term_id:
            params["enrollment_term_id"] = enrollment_term_id

        courses = _get_paginated(url, params)
        logger.info("Fetched %d courses from Canvas", len(courses))

        for raw in courses:
            try:
                canvas_id = raw["id"]
                term      = raw.get("term") or {}
                school_year = _school_year_from_term(term.get("name", ""))

                existing = db.query(CanvasCourse).filter(
                    CanvasCourse.canvas_course_id == canvas_id
                ).first()

                course = existing or CanvasCourse(canvas_course_id=canvas_id)
                course.name           = raw.get("name", "")
                course.course_code    = raw.get("course_code") or None
                course.sis_course_id  = raw.get("sis_course_id") or None
                course.term_name      = term.get("name") or None
                course.school_year    = school_year
                course.start_date     = _parse_date(raw.get("start_at"))
                course.end_date       = _parse_date(raw.get("end_at"))
                course.workflow_state = raw.get("workflow_state") or None

                if not dry_run:
                    if existing is None:
                        db.add(course)
                    db.commit()

                stats["upserted"] += 1

            except Exception as exc:  # noqa: BLE001
                logger.error("Course %s: %s", raw.get("id"), exc, exc_info=True)
                db.rollback()
                stats["errors"] += 1

    except Exception as exc:  # noqa: BLE001
        logger.error("sync_courses failed: %s", exc, exc_info=True)
        stats["errors"] += 1
    finally:
        if close_db:
            db.close()

    logger.info("Canvas course sync complete: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Enrollment sync
# ---------------------------------------------------------------------------

def sync_enrollments(
    db: Optional[Session] = None,
    *,
    account_id: int = _DEFAULT_ACCOUNT_ID,
    course_ids: Optional[list[int]] = None,
    dry_run: bool = False,
) -> dict:
    """
    Fetch StudentEnrollment records for all (or specified) courses and upsert
    them into canvas_enrollments, cross-referencing students by canvas_user_id.

    Returns {upserted, skipped, errors, unmatched}.
    """
    close_db = db is None
    if db is None:
        db = SessionLocal()

    stats: dict[str, int] = {"upserted": 0, "skipped": 0, "errors": 0, "unmatched": 0}

    try:
        # Determine which courses to process
        if course_ids:
            db_courses = (
                db.query(CanvasCourse)
                .filter(CanvasCourse.canvas_course_id.in_(course_ids))
                .all()
            )
        else:
            db_courses = db.query(CanvasCourse).all()

        logger.info("Syncing enrollments for %d courses", len(db_courses))

        for course in db_courses:
            try:
                url = (
                    f"{settings.CANVAS_BASE_URL}/api/v1/courses/"
                    f"{course.canvas_course_id}/enrollments"
                )
                params = {
                    "type[]":  ["StudentEnrollment"],
                    "state[]": ["active", "completed", "inactive"],
                    "include[]": ["grades"],
                }
                enrollments = _get_paginated(url, params)

                for raw_enr in enrollments:
                    try:
                        canvas_user_id = raw_enr.get("user_id")
                        if canvas_user_id is None:
                            stats["skipped"] += 1
                            continue

                        student = db.query(Student).filter(
                            Student.canvas_user_id == canvas_user_id
                        ).first()
                        if student is None:
                            stats["unmatched"] += 1
                            continue

                        canvas_enrollment_id = raw_enr.get("id")
                        existing = db.query(CanvasEnrollment).filter(
                            CanvasEnrollment.student_id == student.id,
                            CanvasEnrollment.canvas_course_id == course.canvas_course_id,
                        ).first()

                        enr = existing or CanvasEnrollment(
                            student_id=student.id,
                            canvas_course_id=course.canvas_course_id,
                        )

                        grades = raw_enr.get("grades") or {}
                        enr.canvas_enrollment_id = canvas_enrollment_id
                        enr.enrollment_type      = raw_enr.get("type", "StudentEnrollment")
                        enr.enrollment_state     = raw_enr.get("enrollment_state") or None
                        enr.current_grade        = grades.get("current_grade") or None
                        enr.current_score        = _decimal_or_none(grades.get("current_score"))
                        enr.final_grade          = grades.get("final_grade") or None
                        enr.final_score          = _decimal_or_none(grades.get("final_score"))

                        if not dry_run:
                            if existing is None:
                                db.add(enr)
                            db.commit()

                        stats["upserted"] += 1

                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "Enrollment for canvas_user %s in course %s: %s",
                            canvas_user_id, course.canvas_course_id, exc, exc_info=True,
                        )
                        db.rollback()
                        stats["errors"] += 1

            except Exception as exc:  # noqa: BLE001
                logger.error("Course %s enrollment fetch failed: %s", course.canvas_course_id, exc, exc_info=True)
                stats["errors"] += 1

    finally:
        if close_db:
            db.close()

    logger.info("Canvas enrollment sync complete: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Full sync (courses + enrollments)
# ---------------------------------------------------------------------------

def sync_all(
    db: Optional[Session] = None,
    *,
    account_id: int = _DEFAULT_ACCOUNT_ID,
    enrollment_term_id: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """Sync courses then enrollments in one call."""
    course_stats = sync_courses(
        db, account_id=account_id, enrollment_term_id=enrollment_term_id, dry_run=dry_run
    )
    enr_stats = sync_enrollments(db, account_id=account_id, dry_run=dry_run)
    return {"courses": course_stats, "enrollments": enr_stats}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decimal_or_none(val: Any):
    if val is None:
        return None
    try:
        from decimal import Decimal
        return Decimal(str(val))
    except Exception:  # noqa: BLE001
        return None


def _school_year_from_term(term_name: str) -> Optional[str]:
    """
    Try to extract a 'YYYY-YYYY' school year string from a term name.

    Examples that match:
        "2024-25 Fall Semester" → "2024-2025"
        "Fall 2024"             → "2024-2025"
        "2024-2025"             → "2024-2025"
    """
    import re

    if not term_name:
        return None

    # Explicit four-digit range: 2024-2025
    m = re.search(r"(20\d{2})[-–](20\d{2})", term_name)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    # Short form: 2024-25
    m = re.search(r"(20\d{2})[-–](\d{2})\b", term_name)
    if m:
        start = int(m.group(1))
        return f"{start}-{start + 1}"

    # Single year — assume it's the fall semester start year
    m = re.search(r"(20\d{2})", term_name)
    if m:
        start = int(m.group(1))
        return f"{start}-{start + 1}"

    return None
