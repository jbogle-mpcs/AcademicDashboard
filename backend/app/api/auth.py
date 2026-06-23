from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from app.core.security import get_current_user

router = APIRouter()

security = HTTPBearer()


@router.get("/me")
async def me(
    current_user=Depends(get_current_user)
):
    return current_user


@router.get("/groups")
async def groups(
    current_user=Depends(get_current_user)
):
    return {
        "user": current_user["upn"],
        "groups": current_user["groups"]
    }


@router.get("/permissions")
async def permissions(
    current_user=Depends(get_current_user)
):
    permissions = []

    groups = current_user["groups"]

    if "Assessment_Admins" in groups:
        permissions.append("admin")

    if "Assessment_Counselors" in groups:
        permissions.append("counselor")

    if "Assessment_HS" in groups:
        permissions.append("high_school")

    if "Assessment_MS" in groups:
        permissions.append("middle_school")

    if "Assessment_LS" in groups:
        permissions.append("lower_school")

    return {
        "user": current_user["upn"],
        "permissions": permissions
    }