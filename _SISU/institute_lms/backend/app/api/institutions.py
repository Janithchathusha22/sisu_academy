from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..dependencies.auth import Principal, get_current_user
from ..dependencies.authorization import institution_membership, require_institution_role, require_platform_role, resolve_institution
from ..schemas.resources import (
    InstitutionCreate,
    InstitutionUpdate,
    MembershipCreate,
    MembershipUpdate,
    ProfileCreate,
    ProfileUpdate,
)
from ..services.access import ensure_read, require_record
from ..services.repository import Repository, alias_record, alias_rows, get_repository, json_values

router = APIRouter(tags=["institutions and people"])


@router.get("/institutions")
def list_institutions(
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    if principal.is_super_admin:
        return alias_rows(repository.list("institutions", limit=500, order="title", desc=False))
    ids = sorted({item.institution_id for item in principal.memberships})
    if not ids:
        return []
    return alias_rows(repository.list("institutions", in_filters={"id": ids}, limit=500, order="title", desc=False))


@router.post("/institutions", status_code=status.HTTP_201_CREATED)
def create_institution(
    body: InstitutionCreate,
    principal: Principal = Depends(require_platform_role("super_admin")),
    repository: Repository = Depends(get_repository),
) -> dict:
    values = json_values(body)
    values["owner_user_id"] = principal.id
    return alias_record(repository.create("institutions", values)) or {}


@router.get("/institutions/{institution_id}")
def get_institution(
    institution_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    ensure_read(principal, institution_id)
    return alias_record(require_record(repository, "institutions", institution_id)) or {}


@router.patch("/institutions/{institution_id}")
def update_institution(
    institution_id: str,
    body: InstitutionUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    require_institution_role(principal, institution_id, "institute_admin")
    return alias_record(repository.update("institutions", institution_id, json_values(body))) or {}


@router.delete("/institutions/{institution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_institution(
    institution_id: str,
    principal: Principal = Depends(require_platform_role("super_admin")),
    repository: Repository = Depends(get_repository),
) -> Response:
    require_record(repository, "institutions", institution_id)
    repository.delete("institutions", institution_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _can_manage_profile(principal: Principal, repository: Repository, user_id: str) -> None:
    if principal.id == user_id or principal.is_super_admin:
        return
    rows = repository.list("institution_memberships", filters={"user_id": user_id}, limit=500)
    for row in rows:
        own = principal.membership_for(str(row["institution_id"]))
        if own and own.role == "institute_admin":
            return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Profile access denied")


@router.get("/profiles")
def list_profiles(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id, allow_platform_all=True)
    if selected is None:
        return alias_rows(repository.list("profiles", limit=500, order="full_name", desc=False))
    memberships = repository.list("institution_memberships", filters={"institution_id": selected}, limit=500)
    user_ids = [str(row["user_id"]) for row in memberships]
    if not user_ids:
        return []
    return alias_rows(repository.list("profiles", in_filters={"id": user_ids}, limit=500, order="full_name", desc=False))


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
def create_profile(
    body: ProfileCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    requested_id = str(body.user_id or principal.id)
    if requested_id != principal.id and not principal.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot provision another user's profile")
    values = json_values(body)
    values.pop("user_id", None)
    values.update(id=requested_id, status="verified" if body.profile_kind == "student" else "pending")
    return alias_record(repository.create("profiles", values)) or {}


@router.get("/profiles/{user_id}")
def get_profile(
    user_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    _can_manage_profile(principal, repository, user_id)
    return alias_record(require_record(repository, "profiles", user_id)) or {}


@router.patch("/profiles/{user_id}")
def update_profile(
    user_id: str,
    body: ProfileUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    _can_manage_profile(principal, repository, user_id)
    return alias_record(repository.update("profiles", user_id, json_values(body))) or {}


@router.delete("/profiles/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    user_id: str,
    principal: Principal = Depends(require_platform_role("super_admin")),
    repository: Repository = Depends(get_repository),
) -> Response:
    require_record(repository, "profiles", user_id)
    repository.delete("profiles", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _list_members(
    institution_id: str | None,
    role: str | None,
    principal: Principal,
    repository: Repository,
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    filters: dict[str, object] = {"institution_id": selected}
    if role:
        filters["role"] = role
    return alias_rows(repository.list("institution_memberships", filters=filters, limit=500, order="created_at", desc=True))


@router.get("/members")
def list_members(
    institution_id: str | None = Query(default=None),
    role: Literal["institute_admin", "teacher", "student"] | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    return _list_members(institution_id, role, principal, repository)


@router.get("/students")
def list_students(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    return _list_members(institution_id, "student", principal, repository)


@router.get("/teachers")
def list_teachers(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    return _list_members(institution_id, "teacher", principal, repository)


@router.post("/members", status_code=status.HTTP_201_CREATED)
def create_member(
    body: MembershipCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    institution_id = str(body.institution_id)
    require_institution_role(principal, institution_id, "institute_admin")
    values = json_values(body)
    values["status"] = "active"
    return alias_record(repository.create("institution_memberships", values)) or {}


@router.get("/members/{membership_id}")
def get_member(
    membership_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "institution_memberships", membership_id)
    ensure_read(principal, str(row["institution_id"]))
    return alias_record(row) or {}


@router.patch("/members/{membership_id}")
def update_member(
    membership_id: str,
    body: MembershipUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "institution_memberships", membership_id)
    require_institution_role(principal, str(row["institution_id"]), "institute_admin")
    return alias_record(repository.update("institution_memberships", membership_id, json_values(body))) or {}


@router.delete("/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_member(
    membership_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "institution_memberships", membership_id)
    require_institution_role(principal, str(row["institution_id"]), "institute_admin")
    repository.update("institution_memberships", membership_id, {"status": "left"})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
