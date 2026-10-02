"""Build application identity from the normalized Supabase schema."""

from typing import Any
def _profile_rows(client, user_id: str) -> list[dict[str, Any]]:
    return (
        client.table("profiles")
        .select("id,email,full_name,profile_kind,status")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data or []
    )


def load_identity(client, user_id: str) -> dict[str, Any] | None:
    profiles = _profile_rows(client, user_id)
    if not profiles:
        return None

    profile = profiles[0]
    platform_roles = (
        client.table("platform_roles")
        .select("role")
        .eq("user_id", user_id)
        .eq("active", True)
        .execute().data or []
    )
    memberships = (
        client.table("institution_memberships")
        .select("id,institution_id,role,status,member_code")
        .eq("user_id", user_id)
        .eq("status", "active")
        .limit(1)
        .execute().data or []
    )

    membership = memberships[0] if memberships else {}
    platform_role = next((row["role"] for row in platform_roles if row.get("role") == "super_admin"), None)
    profile_status = profile["status"]
    approved = profile_status == "verified"
    role = (platform_role or membership.get("role") or ("student" if profile["profile_kind"] == "student" else None)) if approved else None
    return {
        **profile,
        "role": role,
        "institution_id": membership.get("institution_id"),
        "account_status": "active" if approved else profile_status,
        "membership_id": membership.get("id"),
        "member_code": membership.get("member_code"),
    }
