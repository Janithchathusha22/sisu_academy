from fastapi import APIRouter, Depends

from .dependencies import Principal, require_roles
from .services.repository import Repository, get_repository

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview")
def admin_overview(
    user: Principal = Depends(require_roles("super_admin")),
    repo: Repository = Depends(get_repository),
):
    return {
        "role": user.role,
        "email": user.email,
        "full_name": user.profile.get("full_name"),
        "institutions": repo.count("institutions"),
        "verified_students": repo.count(
            "profiles",
            filters={"profile_kind": "student", "status": "verified"},
        ),
        "active_students": repo.count(
            "institution_memberships",
            filters={"role": "student", "status": "active"},
        ),
        "active_teachers": repo.count(
            "institution_memberships",
            filters={"role": "teacher", "status": "active"},
        ),
        "pending_applications": repo.count(
            "account_applications",
            filters={"status": "pending"},
        ),
    }
