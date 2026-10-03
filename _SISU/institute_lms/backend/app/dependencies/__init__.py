"""Canonical FastAPI authentication and role dependencies."""

from fastapi import Depends, HTTPException

from .auth import Membership, Principal, get_current_user
from ..errors import public_error


current_user = get_current_user


def active_user(user: Principal = Depends(current_user)) -> Principal:
    if user.account_status == "pending":
        raise public_error(403, "profile_pending", "Your application is awaiting approval.")
    if user.account_status == "rejected":
        raise public_error(403, "account_rejected", "Your application was not approved.")
    if user.account_status == "suspended":
        raise public_error(403, "account_suspended", "Your account is suspended. Contact the administrator.")
    if user.account_status != "active" or not user.role:
        raise public_error(403, "account_not_approved", "Your account is not approved for this workspace.")
    return user


def require_roles(*roles: str):
    def check(user: Principal = Depends(active_user)) -> Principal:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return check


__all__ = ["Membership", "Principal", "active_user", "current_user", "get_current_user", "require_roles"]
