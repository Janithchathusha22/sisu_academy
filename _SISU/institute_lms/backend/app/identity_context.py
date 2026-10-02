"""Build the application's authorization view from the normalized Supabase schema."""

from typing import Any
from postgrest.exceptions import APIError


def _optional_rows(query) -> list[dict[str, Any]]:
    """Allow an additive schema rollout without making authentication unavailable."""
    try:
        return query.execute().data or []
    except APIError as exc:
        if exc.code in {"42P01", "PGRST205"}:  # table not present in the older schema
            return []
        raise


def _profile_rows(client, user_id: str) -> list[dict[str, Any]]:
    try:
        query = client.table("profiles").select("id,email,full_name,profile_kind,status")
        return query.eq("id", user_id).limit(1).execute().data or []
    except APIError as exc:
        if exc.code not in {"42703", "PGRST204"}:  # column absent in the older schema
            raise
    query = client.table("profiles").select("id,email,full_name,role,institution_id")
    return query.eq("id", user_id).limit(1).execute().data or []


def load_identity(client, user_id: str) -> dict[str, Any] | None:
    profiles = _profile_rows(client, user_id)
    if not profiles:
        return None

    profile = profiles[0]
    platform_roles = _optional_rows(
        client.table("platform_roles")
        .select("role")
        .eq("user_id", user_id)
        .eq("active", True)
    )
    memberships = _optional_rows(
        client.table("institution_memberships")
        .select("id,institution_id,role,status,member_code")
        .eq("user_id", user_id)
        .eq("status", "active")
        .limit(1)
    )

    membership = memberships[0] if memberships else {}
    platform_role = next((row["role"] for row in platform_roles if row.get("role") == "super_admin"), None)
    profile_status = profile.get("status") or profile.get("account_status")
    legacy_role = profile.get("role")
    verified = profile_status in {"verified", "active"} or (profile_status is None and bool(legacy_role))
    # The profile kind is safe identity metadata, not an authorization grant.
    # active_user still requires a verified profile before any role check.
    role = platform_role or membership.get("role") or profile.get("profile_kind") or legacy_role
    return {
        **profile,
        "role": role,
        "institution_id": membership.get("institution_id") or profile.get("institution_id"),
        "account_status": "active" if verified else (profile_status or "pending"),
        "membership_id": membership.get("id"),
        "member_code": membership.get("member_code"),
    }
