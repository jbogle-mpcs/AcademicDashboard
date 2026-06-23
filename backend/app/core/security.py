from functools import lru_cache

import requests
from jose import jwt
from jose.exceptions import JWTError

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPBearer
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer()


@lru_cache
def get_jwks():
    url = (
        f"https://login.microsoftonline.com/"
        f"{settings.ENTRA_TENANT_ID}"
        f"/discovery/v2.0/keys"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        unverified_header = jwt.get_unverified_header(token)

        jwks = get_jwks()

        key = next(
            (
                k
                for k in jwks["keys"]
                if k["kid"] == unverified_header["kid"]
            ),
            None,
        )

        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signing key"
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
            "groups": payload.get("groups", [])
        }

    except JWTError as ex:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(ex)
        )