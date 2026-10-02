"""Build the application's authorization view from the normalized Supabase schema."""

from typing import Any


def load_identity(client, user_id: str) -> dict[str, Any] | None:
    profiles = (
        client.table("profiles")
        .select("id,email,full_name,profile_kind,status")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not profiles:
        return None

    profile = profiles[0]
    platform_roles = (
        client.table("platform_roles")
        .select("role")
        .eq("user_id", user_id)
        .eq("active", True)
        .execute()
        .data
        or []
    )
    memberships = (
        client.table("institution_memberships")
        .select("id,institution_id,role,status,member_code")
        .eq("user_id", user_id)
        .eq("status", "active")
        .limit(1)
        .execute()
        .data
        or []
    )

    membership = memberships[0] if memberships else {}
    platform_role = next((row["role"] for row in platform_roles if row.get("role") == "super_admin"), None)
    verified = profile.get("status") == "verified"
    expected_membership_role = {
        "student": "student",
        "teacher": "teacher",
        "institute": "institute_admin",
    }.get(profile.get("profile_kind"))
    membership_role = membership.get("role")
    if membership_role != expected_membership_role:
        membership = {}
        membership_role = None
    role = platform_role or membership_role
    return {
        **profile,
        "role": role,
        "institution_id": membership.get("institution_id"),
        "account_status": "active" if verified else profile.get("status", "pending"),
        "membership_id": membership.get("id"),
        "member_code": membership.get("member_code"),
    }
