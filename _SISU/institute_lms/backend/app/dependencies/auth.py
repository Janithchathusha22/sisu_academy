"""Authenticate a Supabase access token and load server-owned authorization."""

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError

from ..config import Settings
from ..database import user_client
from ..identity_context import load_identity


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Membership:
    id: str
    institution_id: str
    role: str
    status: str
    member_code: str | None = None


@dataclass(frozen=True)
class Principal:
    id: str
    email: str | None
    token: str
    profile: dict[str, Any]
    memberships: tuple[Membership, ...]
    platform_roles: frozenset[str]

    @property
    def is_super_admin(self) -> bool:
        return "super_admin" in self.platform_roles

    @property
    def role(self) -> str | None:
        return self.profile.get("role")

    @property
    def institution_id(self) -> str | None:
        value = self.profile.get("institution_id")
        return str(value) if value else None

    @property
    def account_status(self) -> str:
        return str(self.profile.get("account_status") or "pending")

    def membership_for(self, institution_id: str) -> Membership | None:
        return next((item for item in self.memberships if item.institution_id == institution_id), None)


def runtime_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings were not initialized")
    return settings


def _optional_rows(query) -> list[dict[str, Any]]:
    try:
        return query.execute().data or []
    except APIError as exc:
        if exc.code in {"42P01", "PGRST205"}:
            return []
        raise


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(runtime_settings),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")

    try:
        client = user_client(token, settings)
        auth_response = client.auth.get_user(token)
        auth_user = getattr(auth_response, "user", None)
        if auth_user is None:
            raise ValueError("Supabase returned no user")
        user_id = str(auth_user.id)
        profile = load_identity(client, user_id)
        if not profile:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Profile not provisioned")
        role_rows = _optional_rows(
            client.table("platform_roles")
            .select("role,active")
            .eq("user_id", user_id)
            .eq("active", True)
        )
        membership_rows = _optional_rows(
            client.table("institution_memberships")
            .select("id,institution_id,user_id,role,status,member_code")
            .eq("user_id", user_id)
            .eq("status", "active")
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    memberships = tuple(
        Membership(
            id=str(row["id"]),
            institution_id=str(row["institution_id"]),
            role=str(row["role"]),
            status=str(row["status"]),
            member_code=row.get("member_code"),
        )
        for row in membership_rows
    )
    return Principal(
        id=user_id,
        email=getattr(auth_user, "email", None),
        token=token,
        profile=profile,
        memberships=memberships,
        platform_roles=frozenset(str(row["role"]) for row in role_rows),
    )
