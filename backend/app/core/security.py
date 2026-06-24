from datetime import datetime, timedelta
from threading import Lock
from typing import Any

import requests
from jose import jwt
from jose.exceptions import JWTError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer()

# ---------------------------------------------------------------------------
# JWKS cache — refreshed every 24 hours so key rotations are picked up.
# Using a manual TTL cache rather than @lru_cache (which never expires).
# ---------------------------------------------------------------------------

_JWKS_TTL = timedelta(hours=24)

_jwks_cache: dict[str, Any] = {}   # {"keys": [...], "fetched_at": datetime}
_jwks_lock = Lock()


def _jwks_url() -> str:
    return (
        f"https://login.microsoftonline.com/"
        f"{settings.ENTRA_TENANT_ID}"
        f"/discovery/v2.0/keys"
    )


def get_jwks() -> dict:
    """Return JWKS, fetching from Microsoft if the cache is stale or empty."""
    with _jwks_lock:
        fetched_at: datetime | None = _jwks_cache.get("fetched_at")
        if fetched_at is None or datetime.utcnow() - fetched_at > _JWKS_TTL:
            response = requests.get(_jwks_url(), timeout=10)
            response.raise_for_status()
            _jwks_cache["keys"] = response.json()
            _jwks_cache["fetched_at"] = datetime.utcnow()
        return _jwks_cache["keys"]


def _find_key(kid: str) -> dict | None:
    """Look up a signing key by kid, refreshing the cache once on a miss."""
    jwks = get_jwks()
    key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if key is not None:
        return key

    # Key not found — Microsoft may have rotated; force one immediate refresh.
    with _jwks_lock:
        _jwks_cache.clear()
    jwks = get_jwks()
    return next((k for k in jwks["keys"] if k["kid"] == kid), None)


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    try:
        unverified_header = jwt.get_unverified_header(token)
        key = _find_key(unverified_header["kid"])
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signing key",
            )
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.ENTRA_CLIENT_ID,
            issuer=(
                f"https://login.microsoftonline.com/"
                f"{settings.ENTRA_TENANT_ID}/v2.0"
            ),
        )
        return {
            "oid": payload.get("oid"),
            "name": payload.get("name"),
            "upn": payload.get("preferred_username"),
            "email": payload.get("preferred_username"),
            "groups": payload.get("groups", []),
        }
    except JWTError as ex:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ex)
        )