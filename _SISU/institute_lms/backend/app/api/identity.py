from fastapi import APIRouter, Depends, Query

from ..dependencies.auth import Principal, get_current_user
from ..dependencies.authorization import resolve_institution
from ..services.repository import Repository, alias_record, get_repository

router = APIRouter(tags=["identity"])


def principal_payload(principal: Principal) -> dict:
    memberships = [
        {
            "id": item.id,
            "name": item.id,
            "institution_id": item.institution_id,
            "role": item.role,
            "status": item.status,
            "member_code": item.member_code,
        }
        for item in principal.memberships
    ]
    role = "super_admin" if principal.is_super_admin else memberships[0]["role"] if len(memberships) == 1 else None
    return {
        "id": principal.id,
        "email": principal.email,
        "role": role,
        "profile": alias_record(principal.profile),
        "memberships": memberships,
        "platform_roles": sorted(principal.platform_roles),
    }


@router.get("/me")
def me(principal: Principal = Depends(get_current_user)) -> dict:
    return principal_payload(principal)


@router.get("/dashboard/bootstrap")
def bootstrap(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    selected = resolve_institution(principal, institution_id, allow_platform_all=True)
    institution = repository.get("institutions", selected) if selected else None
    member = principal.membership_for(selected) if selected else None
    result = principal_payload(principal)
    result.update(
        {
            "authenticated": True,
            "mode": "live",
            "institute": alias_record(institution),
            "member": {
                "id": member.id,
                "name": member.id,
                "role": member.role,
                "institution_id": member.institution_id,
            }
            if member
            else None,
        }
    )
    return result


@router.get("/dashboard/summary")
def dashboard_summary(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    return {
        "institution_id": selected,
        "courses": repository.count("courses", filters={"institution_id": selected}),
        "classes": repository.count("classes", filters={"institution_id": selected, "active": True}),
        "students": repository.count(
            "institution_memberships",
            filters={"institution_id": selected, "role": "student", "status": "active"},
        ),
        "teachers": repository.count(
            "institution_memberships",
            filters={"institution_id": selected, "role": "teacher", "status": "active"},
        ),
        "enrollments": repository.count("enrollments", filters={"institution_id": selected, "status": "active"}),
        "open_invoices": repository.count("invoices", filters={"institution_id": selected, "status": "unpaid"}),
    }
