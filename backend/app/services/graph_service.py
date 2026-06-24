"""
Microsoft Graph API service.

Two responsibilities:
  1. Fetch group memberships for JWT token enrichment (used in security.py
     when the token doesn't include groups claims directly).
  2. Student sync via Graph when STUDENT_SYNC_SOURCE=graph — an alternative
     to the direct LDAP path in ad_service.py.  Uses the /users endpoint
     filtered to members of a "Students" group.

Required settings:
    ENTRA_TENANT_ID
    ENTRA_CLIENT_ID
    ENTRA_CLIENT_SECRET
"""

import logging
from typing import Optional

from app.core.config import settings
from app.database import SessionLocal
from app.models.student import Student
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_URL = f"https://login.microsoftonline.com/{settings.ENTRA_TENANT_ID}/oauth2/v2.0/token"
_SCOPE = "https://graph.microsoft.com/.default"

# ---------------------------------------------------------------------------
# Token management (app-only / client credentials)
# ---------------------------------------------------------------------------

_cached_token: Optional[str] = None
_token_expiry: float = 0.0


def _get_app_token() -> str:
    """Obtain (or return cached) a client-credentials access token."""
    import time
    import requests

    global _cached_token, _token_expiry
    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token

    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type":    "client_credentials",
            "client_id":     settings.ENTRA_CLIENT_ID,
            "client_secret": settings.ENTRA_CLIENT_SECRET,
            "scope":         _SCOPE,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _cached_token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600)
    return _cached_token


def _graph_get(path: str, params: Optional[dict] = None) -> dict:
    """GET a single Graph endpoint, returning the parsed JSON body."""
    import requests
    url = path if path.startswith("https://") else f"{_GRAPH_BASE}{path}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {_get_app_token()}"},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _graph_get_all(path: str, params: Optional[dict] = None) -> list[dict]:
    """Follow @odata.nextLink pagination and collect every item."""
    results: list[dict] = []
    url: Optional[str] = path if path.startswith("https://") else f"{_GRAPH_BASE}{path}"
    first = True
    while url:
        data = _graph_get(url, params=params if first else None)
        first = False
        results.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return results


# ---------------------------------------------------------------------------
# Group membership helpers (used by security / auth pipeline)
# ---------------------------------------------------------------------------

def get_user_groups(user_oid: str) -> list[str]:
    """
    Return a list of group object IDs that user_oid belongs to.

    This is used as a fallback when groups are not included in the JWT
    (tenant exceeds the 200-group claim limit).
    """
    try:
        members = _graph_get_all(
            f"/users/{user_oid}/transitiveMemberOf/microsoft.graph.group",
            params={"$select": "id"},
        )
        return [m["id"] for m in members if "id" in m]
    except Exception as exc:  # noqa: BLE001
        logger.error("get_user_groups(%s): %s", user_oid, exc, exc_info=True)
        return []


def get_group_members(group_id: str) -> list[dict]:
    """
    Return basic user info for all members of group_id.
    Useful for seeding the student roster from a specific Entra group.
    """
    try:
        return _graph_get_all(
            f"/groups/{group_id}/members/microsoft.graph.user",
            params={
                "$select": (
                    "id,displayName,givenName,surname,"
                    "mail,userPrincipalName,department,jobTitle"
                )
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("get_group_members(%s): %s", group_id, exc, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Student sync via Graph
# ---------------------------------------------------------------------------

# Map Entra group IDs to (division, grade).
# Populated from settings at call time; override via env vars.
def _build_grade_map() -> dict[str, tuple[str, int]]:
    import os
    grade_map: dict[str, tuple[str, int]] = {}
    for grade in range(1, 13):
        env_key = f"GROUP_GRADE_{grade}"
        gid = os.getenv(env_key)
        if gid:
            div = "LS" if grade <= 5 else "MS" if grade <= 8 else "HS"
            grade_map[gid] = (div, grade)
    return grade_map


def _graduation_year(grade: Optional[int]) -> Optional[int]:
    if grade is None:
        return None
    from datetime import date
    today = date.today()
    offset = 12 - grade
    return today.year + offset if today.month < 7 else today.year + offset + 1


def sync_students_from_graph(
    db: Optional[Session] = None,
    *,
    student_group_id: Optional[str] = None,
    dry_run: bool = False,
    deactivate_missing: bool = True,
) -> dict:
    """
    Sync students from Entra ID via Microsoft Graph.

    If student_group_id is provided (or AD_STUDENTS_GROUP_ID env var is set),
    members of that group are imported.  Otherwise all users with
    department=Student are fetched.

    Returns {created, updated, deactivated, errors}.
    """
    import os

    close_db = db is None
    if db is None:
        db = SessionLocal()

    stats: dict[str, int] = {"created": 0, "updated": 0, "deactivated": 0, "errors": 0}
    seen_oids: set[str] = set()
    grade_map = _build_grade_map()

    try:
        # Determine source of users
        group_id = student_group_id or os.getenv("AD_STUDENTS_GROUP_ID")
        if group_id:
            logger.info("Syncing students from Entra group %s", group_id)
            users = get_group_members(group_id)
        else:
            logger.info("Syncing students via department=Student filter")
            users = _graph_get_all(
                "/users",
                params={
                    "$filter": "department eq 'Student'",
                    "$select": (
                        "id,displayName,givenName,surname,"
                        "mail,userPrincipalName,department"
                    ),
                },
            )

        logger.info("Graph returned %d users", len(users))

        # Pre-fetch grade group memberships for all users if grade_map is populated
        # (Only feasible for small schools; large installs should use batch requests)
        user_grade: dict[str, tuple[Optional[str], Optional[int]]] = {}
        if grade_map:
            for gid, (div, grade) in grade_map.items():
                try:
                    members = _graph_get_all(
                        f"/groups/{gid}/members/microsoft.graph.user",
                        params={"$select": "id"},
                    )
                    for m in members:
                        user_grade[m["id"]] = (div, grade)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not fetch members of grade group %s: %s", gid, exc)

        for user in users:
            try:
                oid        = user.get("id", "")
                first_name = user.get("givenName", "").strip()
                last_name  = user.get("surname", "").strip()
                upn        = user.get("userPrincipalName", "").strip()
                email      = user.get("mail") or upn or None

                if not oid or not first_name or not last_name:
                    logger.debug("Skipping incomplete user %r", oid)
                    stats["errors"] += 1
                    continue

                # student_id: use the local part of UPN (before @)
                student_id_str = upn.split("@")[0] if "@" in upn else oid

                seen_oids.add(oid)

                division, grade = user_grade.get(oid, (None, None))

                # Preferred name: display name's first word if different from givenName
                display_first = (user.get("displayName") or "").split()[0]
                preferred = display_first if display_first.lower() != first_name.lower() else None

                # Find existing student
                student = db.query(Student).filter(
                    Student.ad_object_id == oid
                ).first()
                if student is None:
                    student = db.query(Student).filter(
                        Student.student_id == student_id_str
                    ).first()

                created = student is None
                if created:
                    student = Student(student_id=student_id_str)

                student.ad_object_id    = oid
                student.first_name      = first_name
                student.last_name       = last_name
                student.preferred_name  = preferred
                student.email           = email
                student.division        = division
                student.grade           = grade
                student.graduation_year = _graduation_year(grade)
                student.is_active       = True

                if not dry_run:
                    if created:
                        db.add(student)
                    db.commit()

                if created:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

            except Exception as exc:  # noqa: BLE001
                logger.error("User %s: %s", user.get("id"), exc, exc_info=True)
                db.rollback()
                stats["errors"] += 1

        # Deactivate students whose Entra accounts are no longer in the pull
        if deactivate_missing and not dry_run:
            active_students = (
                db.query(Student)
                .filter(Student.is_active == True, Student.ad_object_id.isnot(None))  # noqa: E712
                .all()
            )
            for s in active_students:
                if s.ad_object_id not in seen_oids:
                    s.is_active = False
                    stats["deactivated"] += 1
            db.commit()

    except Exception as exc:  # noqa: BLE001
        logger.error("Graph student sync failed: %s", exc, exc_info=True)
        stats["errors"] += 1
    finally:
        if close_db:
            db.close()

    logger.info("Graph sync complete: %s", stats)
    return stats
