"""Reusable tenant and role checks based only on database-backed grants."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from .auth import Membership, Principal
from . import active_user


INSTITUTE_ROLES = frozenset({"institute_admin", "teacher", "student"})
MANAGER_ROLES = frozenset({"institute_admin"})
TEACHING_ROLES = frozenset({"institute_admin", "teacher"})


def require_platform_role(*allowed: str) -> Callable[..., Principal]:
    expected = frozenset(allowed)

    def dependency(principal: Principal = Depends(active_user)) -> Principal:
        if not principal.platform_roles.intersection(expected):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform role required")
        return principal

    return dependency


def institution_membership(principal: Principal, institution_id: str) -> Membership:
    membership = principal.membership_for(str(institution_id))
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Institution access denied")
    return membership


def require_institution_role(principal: Principal, institution_id: str, *roles: str) -> Membership | None:
    if principal.is_super_admin:
        return None
    membership = institution_membership(principal, institution_id)
    if membership.role not in set(roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient institution permissions")
    return membership


def resolve_institution(principal: Principal, requested: str | None, *, allow_platform_all: bool = False) -> str | None:
    if requested:
        if not principal.is_super_admin:
            institution_membership(principal, requested)
        return str(requested)
    institutions = {membership.institution_id for membership in principal.memberships}
    if len(institutions) == 1:
        return next(iter(institutions))
    if principal.is_super_admin and allow_platform_all:
        return None
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "institution_id is required")
