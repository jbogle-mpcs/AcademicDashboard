from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.core.roles import Groups

router = APIRouter()


@router.get("/me")
async def me(
    current_user=Depends(get_current_user),
):
    return current_user


@router.get("/groups")
async def groups(
    current_user=Depends(get_current_user),
):
    return {
        "user": current_user["upn"],
        "groups": current_user["groups"],
    }


@router.get("/permissions")
async def permissions(
    current_user=Depends(get_current_user),
):
    """
    Translate raw Entra group GUIDs from the JWT into human-readable
    permission labels for the frontend.
    """
    user_groups = current_user["groups"]
    result = []

    if Groups.ADMINS in user_groups:
        result.append("admin")

    if Groups.COUNSELORS in user_groups:
        result.append("counselor")

    if Groups.HS in user_groups:
        result.append("high_school")

    if Groups.MS in user_groups:
        result.append("middle_school")

    if Groups.LS in user_groups:
        result.append("lower_school")

    return {
        "user": current_user["upn"],
        "permissions": result,
    }