"""Authenticate a Supabase access token and load server-owned authorization."""

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError, AuthRetryableError
import httpx

from ..config import Settings
from ..database import user_client
from ..identity_context import load_identity
from ..token_validation import validate_access_token


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


def _provision_profile(client) -> None:
    """Complete confirmed-user onboarding through the database-owned policy."""
    try:
        client.rpc("provision_current_profile").execute()
    except APIError as exc:
        # A hosted project that has not received the provisioning migration must
        # fail closed instead of falling back to a server secret or guessed table.
        if exc.code in {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Application profile provisioning is unavailable in the recovered database",
            ) from exc
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

    claims = validate_access_token(token, settings)
    client = user_client(token, settings)
    try:
        auth_response = client.auth.get_user(token)
        auth_user = getattr(auth_response, "user", None)
        if auth_user is None:
            raise ValueError("Supabase returned no user")
    except (AuthRetryableError, httpx.HTTPError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase authentication service is unavailable") from exc
    except AuthApiError as exc:
        if exc.status >= 500:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase authentication service is unavailable") from exc
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    if str(auth_user.id) != str(claims["sub"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    # Authentication succeeded. Keep profile/RLS/provisioning failures outside
    # the token-validation exception boundary so they are never mislabeled 401.
    user_id = str(auth_user.id)
    profile = load_identity(client, user_id)
    if not profile:
        _provision_profile(client)
        profile = load_identity(client, user_id)
    if not profile:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Application profile provisioning is pending",
        )
    role_rows = (
        client.table("platform_roles")
        .select("role,active")
        .eq("user_id", user_id)
        .eq("active", True)
        .execute().data or []
    )
    membership_rows = (
        client.table("institution_memberships")
        .select("id,institution_id,user_id,role,status,member_code")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute().data or []
    )

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
        platform_roles=frozenset(str(row["role"]) for row in role_rows) if profile["account_status"] == "active" else frozenset(),
    )
