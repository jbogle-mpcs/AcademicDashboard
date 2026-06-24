"""
Active Directory student sync service.

Reads student accounts from AD (via ldap3) and upserts them into the
students table.  Division and grade are inferred from group membership
or OU path.

Required settings (all read from environment via pydantic-settings):
    AD_SERVER      — e.g. dc01.mpcs.mtparanschool.com
    AD_BASE_DN     — e.g. OU=zUsers,DC=mpcs,DC=mtparanschool,DC=com
    AD_BIND_USER   — e.g. svc_dashboard@mpcs.mtparanschool.com
    AD_BIND_PASSWORD

Optional settings (fall back to defaults if absent):
    AD_STUDENT_FILTER   — LDAP filter string; default targets "Student" as
                          the department attribute
    AD_PAGE_SIZE        — int, default 500

The service uses the Graph API path when STUDENT_SYNC_SOURCE=graph (see
graph_service.py).  The AD path is used when STUDENT_SYNC_SOURCE=ad.
"""

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.student import Student

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — ldap3 is only needed at runtime
# ---------------------------------------------------------------------------

def _ldap3():
    try:
        import ldap3
        return ldap3
    except ImportError as exc:
        raise ImportError(
            "ldap3 is required for AD sync — add it to requirements.txt"
        ) from exc


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _get_ad_settings():
    """Pull AD settings from environment; raise clearly if any are missing."""
    import os
    required = ["AD_SERVER", "AD_BASE_DN", "AD_BIND_USER", "AD_BIND_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing AD environment variables: {', '.join(missing)}")
    return {
        "server":        os.environ["AD_SERVER"],
        "base_dn":       os.environ["AD_BASE_DN"],
        "bind_user":     os.environ["AD_BIND_USER"],
        "bind_password": os.environ["AD_BIND_PASSWORD"],
        "filter":        os.getenv("AD_STUDENT_FILTER", "(department=Student)"),
        "page_size":     int(os.getenv("AD_PAGE_SIZE", "500")),
    }


# ---------------------------------------------------------------------------
# LDAP attribute → model field mapping
# ---------------------------------------------------------------------------

_ATTRS = [
    "sAMAccountName",   # → student_id (school login / student ID)
    "objectGUID",       # → ad_object_id (stable unique identifier)
    "givenName",        # → first_name
    "sn",               # → last_name
    "displayName",      # used to derive preferred_name when it differs
    "mail",             # → email
    "department",       # "Student" sanity check
    "physicalDeliveryOfficeName",  # sometimes encodes grade/division
    "description",      # sometimes encodes grade
    "memberOf",         # group DNs — used to infer division / grade
    "distinguishedName",
    "userAccountControl",
]

# Group DN substrings → (division, grade)
# Customise these to match your AD group naming convention.
_GROUP_GRADE_MAP: dict[str, tuple[str, int]] = {
    "grade_1":  ("LS", 1),  "grade1":  ("LS", 1),
    "grade_2":  ("LS", 2),  "grade2":  ("LS", 2),
    "grade_3":  ("LS", 3),  "grade3":  ("LS", 3),
    "grade_4":  ("LS", 4),  "grade4":  ("LS", 4),
    "grade_5":  ("LS", 5),  "grade5":  ("LS", 5),
    "grade_6":  ("MS", 6),  "grade6":  ("MS", 6),
    "grade_7":  ("MS", 7),  "grade7":  ("MS", 7),
    "grade_8":  ("MS", 8),  "grade8":  ("MS", 8),
    "grade_9":  ("HS", 9),  "grade9":  ("HS", 9),
    "grade_10": ("HS", 10), "grade10": ("HS", 10),
    "grade_11": ("HS", 11), "grade11": ("HS", 11),
    "grade_12": ("HS", 12), "grade12": ("HS", 12),
}

_DISABLED_FLAG = 0x2  # bit in userAccountControl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(val) -> str:
    """Extract a string from an ldap3 attribute value."""
    if val is None:
        return ""
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val)


def _guid_to_str(raw) -> Optional[str]:
    """Convert an AD objectGUID bytes value to a hex string."""
    if isinstance(raw, bytes):
        return raw.hex()
    return str(raw) if raw else None


def _infer_division_grade(member_of: list[str]) -> tuple[Optional[str], Optional[int]]:
    """Walk group memberships to find a grade/division match."""
    for dn in member_of:
        dn_lower = dn.lower()
        for key, (div, grade) in _GROUP_GRADE_MAP.items():
            if key in dn_lower:
                return div, grade
    return None, None


def _graduation_year(grade: Optional[int]) -> Optional[int]:
    if grade is None:
        return None
    from datetime import date
    today = date.today()
    # School year: if before July, graduation is (current_year + (12 - grade))
    # After July the cohort has moved up one year
    offset = 12 - grade
    return today.year + offset if today.month < 7 else today.year + offset


def _is_disabled(uac_raw) -> bool:
    try:
        uac = int(_str(uac_raw))
        return bool(uac & _DISABLED_FLAG)
    except (ValueError, TypeError):
        return False


def _preferred_name(display_name: str, first_name: str) -> Optional[str]:
    """
    Return the preferred first name when displayName differs from givenName.
    E.g. displayName="Alex Smith", givenName="Alexander" → preferred="Alex".
    """
    display_first = display_name.split()[0] if display_name else ""
    if display_first and display_first.lower() != first_name.lower():
        return display_first
    return None


# ---------------------------------------------------------------------------
# Public sync function
# ---------------------------------------------------------------------------

def sync_students_from_ad(
    db: Optional[Session] = None,
    *,
    dry_run: bool = False,
    deactivate_missing: bool = True,
) -> dict:
    """
    Pull student accounts from Active Directory and upsert into students table.

    If deactivate_missing is True, any student currently marked active in the
    DB who was not returned by the LDAP query will be set to is_active=False.

    Returns {created, updated, deactivated, errors}.
    """
    ldap3 = _ldap3()
    cfg   = _get_ad_settings()

    close_db = db is None
    if db is None:
        db = SessionLocal()

    stats: dict[str, int] = {"created": 0, "updated": 0, "deactivated": 0, "errors": 0}
    seen_student_ids: set[str] = set()

    try:
        server = ldap3.Server(cfg["server"], get_info=ldap3.ALL, use_ssl=True)
        conn = ldap3.Connection(
            server,
            user=cfg["bind_user"],
            password=cfg["bind_password"],
            authentication=ldap3.NTLM,
            auto_bind=True,
        )

        conn.search(
            search_base=cfg["base_dn"],
            search_filter=cfg["filter"],
            search_scope=ldap3.SUBTREE,
            attributes=_ATTRS,
            paged_size=cfg["page_size"],
        )

        # Handle paged results
        all_entries = list(conn.entries)
        cookie = conn.result.get("controls", {}).get("1.2.840.113556.1.4.319", {}).get("value", {}).get("cookie")
        while cookie:
            conn.search(
                search_base=cfg["base_dn"],
                search_filter=cfg["filter"],
                search_scope=ldap3.SUBTREE,
                attributes=_ATTRS,
                paged_size=cfg["page_size"],
                paged_cookie=cookie,
            )
            all_entries.extend(conn.entries)
            cookie = conn.result.get("controls", {}).get("1.2.840.113556.1.4.319", {}).get("value", {}).get("cookie")

        logger.info("AD returned %d entries", len(all_entries))

        for entry in all_entries:
            try:
                attrs = entry.entry_attributes_as_dict

                student_id_str = _str(attrs.get("sAMAccountName"))
                if not student_id_str:
                    stats["errors"] += 1
                    continue

                first_name = _str(attrs.get("givenName"))
                last_name  = _str(attrs.get("sn"))
                if not first_name or not last_name:
                    logger.debug("Skipping %r: missing name", student_id_str)
                    stats["errors"] += 1
                    continue

                display_name = _str(attrs.get("displayName"))
                email        = _str(attrs.get("mail")) or None
                is_active    = not _is_disabled(attrs.get("userAccountControl"))

                member_of = [_str(g) for g in (attrs.get("memberOf") or [])]
                division, grade = _infer_division_grade(member_of)

                ad_object_id = _guid_to_str(
                    attrs.get("objectGUID", [None])[0]
                    if isinstance(attrs.get("objectGUID"), list)
                    else attrs.get("objectGUID")
                )

                seen_student_ids.add(student_id_str)

                # Try to find existing by AD object ID first, then student_id
                student = None
                if ad_object_id:
                    student = db.query(Student).filter(
                        Student.ad_object_id == ad_object_id
                    ).first()
                if student is None:
                    student = db.query(Student).filter(
                        Student.student_id == student_id_str
                    ).first()

                created = student is None
                if created:
                    student = Student(student_id=student_id_str)

                student.ad_object_id    = ad_object_id
                student.first_name      = first_name
                student.last_name       = last_name
                student.preferred_name  = _preferred_name(display_name, first_name)
                student.email           = email
                student.division        = division
                student.grade           = grade
                student.graduation_year = _graduation_year(grade)
                student.is_active       = is_active
                # Preserve student_id in case we found the record via ad_object_id
                if not student.student_id:
                    student.student_id = student_id_str

                if not dry_run:
                    if created:
                        db.add(student)
                    db.commit()

                if created:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

            except Exception as exc:  # noqa: BLE001
                logger.error("Entry %s: %s", entry.entry_dn, exc, exc_info=True)
                db.rollback()
                stats["errors"] += 1

        # Deactivate students no longer in AD
        if deactivate_missing and not dry_run:
            active_students = db.query(Student).filter(Student.is_active == True).all()  # noqa: E712
            for s in active_students:
                if s.student_id not in seen_student_ids:
                    s.is_active = False
                    stats["deactivated"] += 1
            db.commit()

    except Exception as exc:  # noqa: BLE001
        logger.error("AD sync failed: %s", exc, exc_info=True)
        stats["errors"] += 1
    finally:
        if close_db:
            db.close()

    logger.info("AD sync complete: %s", stats)
    return stats
