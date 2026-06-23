from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user


def require_group(group_id: str):

    def dependency(
        current_user=Depends(get_current_user)
    ):
        groups = current_user.get("groups", [])

        if group_id not in groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return current_user

    return dependency


def require_any_group(group_ids: list[str]):

    def dependency(
        current_user=Depends(get_current_user)
    ):
        groups = current_user.get("groups", [])

        if not any(g in groups for g in group_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return current_user

    return dependency