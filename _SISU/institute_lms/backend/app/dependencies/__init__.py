"""Canonical FastAPI authentication and role dependencies."""

from fastapi import Depends, HTTPException

from .auth import Membership, Principal, get_current_user


current_user = get_current_user


def active_user(user: Principal = Depends(current_user)) -> Principal:
    if user.account_status != "active" or not user.role:
        raise HTTPException(403, "Account approval required")
    return user


def require_roles(*roles: str):
    def check(user: Principal = Depends(active_user)) -> Principal:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return check


__all__ = ["Membership", "Principal", "active_user", "current_user", "get_current_user", "require_roles"]
