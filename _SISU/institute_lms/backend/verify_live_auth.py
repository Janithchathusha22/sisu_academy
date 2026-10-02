"""Run destructive-only-to-temporary-users live Supabase authentication checks."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip().isidentifier():
                values[key.strip()] = value.strip().strip('"').strip("'")
    for key in (
        "VITE_SUPABASE_URL", "SUPABASE_URL", "VITE_SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY",
    ):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def run(env_file: Path) -> dict[str, str]:
    values = read_env(env_file)
    url = (values.get("VITE_SUPABASE_URL") or values.get("SUPABASE_URL", "")).rstrip("/")
    public_key = values.get("VITE_SUPABASE_PUBLISHABLE_KEY") or values.get("SUPABASE_PUBLISHABLE_KEY", "")
    secret_key = values.get("SUPABASE_SECRET_KEY", "")
    if not url or not public_key:
        raise RuntimeError("SUPABASE_URL and a publishable key are required")
    admin_available = bool(secret_key) and not secret_key.startswith(("PASTE_", "ROTATED_", "GENERATE_"))
    if not admin_available:
        raise RuntimeError("A valid server secret is required to verify and clean up temporary Auth users")

    report = {name: "FAIL" for name in (
        "supabase_auth_connection", "student_signup", "student_auth_user", "student_profile_role",
        "student_login", "teacher_signup", "teacher_auth_user", "teacher_profile_role",
        "teacher_login", "wrong_password", "api_without_token", "api_invalid_token",
        "student_api_token", "teacher_api_token",
    )}
    created: list[str] = []
    nonce = secrets.token_hex(6)
    password = "Sisu-test-" + secrets.token_urlsafe(18)
    public_headers = {"apikey": public_key, "Content-Type": "application/json"}
    admin_headers = {"apikey": secret_key, "Authorization": f"Bearer {secret_key}"}

    # Configure the imported FastAPI application without writing secrets to disk.
    os.environ.update({
        "SUPABASE_URL": url,
        "SUPABASE_PUBLISHABLE_KEY": public_key,
        "FRONTEND_URL": "http://127.0.0.1:5178",
        "CORS_ORIGINS": "http://127.0.0.1:5178",
    })

    with httpx.Client(timeout=20) as client:
        settings_response = client.get(f"{url}/auth/v1/settings", headers={"apikey": public_key})
        settings_response.raise_for_status()
        report["supabase_auth_connection"] = "PASS"

        try:
            tokens: dict[str, str] = {}
            for role in ("student", "teacher"):
                email = f"codex-auth-{role}-{nonce}@gmail.com"
                signup = client.post(
                    f"{url}/auth/v1/signup",
                    headers=public_headers,
                    json={
                        "email": email,
                        "password": password,
                        "data": {"full_name": f"Codex {role.title()} Test", "account_type": role},
                    },
                )
                if signup.status_code >= 400:
                    problem = signup.json()
                    reason = problem.get("msg") or problem.get("error_description") or problem.get("message") or "request rejected"
                    report[f"{role}_signup"] = f"FAIL ({signup.status_code}: {reason})"
                    if not admin_available:
                        report[f"{role}_auth_user"] = "FAIL (server secret unavailable)"
                        continue
                    provision = client.post(
                        f"{url}/auth/v1/admin/users",
                        headers={**admin_headers, "Content-Type": "application/json"},
                        json={
                            "email": email,
                            "password": password,
                            "email_confirm": True,
                            "user_metadata": {"full_name": f"Codex {role.title()} Test", "account_type": role},
                        },
                    )
                    if provision.status_code >= 400:
                        report[f"{role}_auth_user"] = f"FAIL ({provision.status_code})"
                        continue
                    signup_body = provision.json()
                else:
                    signup_body = signup.json()
                user_id = signup_body.get("user", {}).get("id") or signup_body.get("id")
                if not user_id:
                    report[f"{role}_auth_user"] = "FAIL (no user UUID)"
                    continue
                created.append(user_id)
                if signup.status_code < 400:
                    report[f"{role}_signup"] = "PASS"

                if admin_available:
                    auth_user = client.get(f"{url}/auth/v1/admin/users/{user_id}", headers=admin_headers)
                    report[f"{role}_auth_user"] = "PASS" if auth_user.status_code == 200 else f"FAIL ({auth_user.status_code})"
                else:
                    report[f"{role}_auth_user"] = "FAIL (admin verification unavailable)"

                profile_headers = admin_headers if admin_available else {
                    "apikey": public_key,
                    "Authorization": f"Bearer {signup_body.get('access_token', '')}",
                }
                profile = client.get(
                    f"{url}/rest/v1/profiles",
                    headers={**profile_headers, "Accept": "application/json"},
                    params={"id": f"eq.{user_id}", "select": "*"},
                )
                rows = profile.json() if profile.status_code == 200 else []
                actual_role = (rows[0].get("profile_kind") or rows[0].get("role")) if rows else None
                report[f"{role}_profile_role"] = "PASS" if actual_role == role else f"FAIL (role={actual_role or 'missing'})"

                # Confirm the temporary address so password login can be tested regardless of project email policy.
                if admin_available:
                    confirmed = client.put(
                        f"{url}/auth/v1/admin/users/{user_id}",
                        headers={**admin_headers, "Content-Type": "application/json"},
                        json={"email_confirm": True},
                    )
                    confirmed.raise_for_status()
                login = client.post(
                    f"{url}/auth/v1/token",
                    headers=public_headers,
                    params={"grant_type": "password"},
                    json={"email": email, "password": password},
                )
                token = login.json().get("access_token") if login.status_code == 200 else None
                report[f"{role}_login"] = "PASS" if token else f"FAIL ({login.status_code})"
                if token:
                    tokens[role] = token

            wrong = client.post(
                f"{url}/auth/v1/token",
                headers=public_headers,
                params={"grant_type": "password"},
                json={"email": f"codex-auth-student-{nonce}@gmail.com", "password": "definitely-wrong"},
            )
            report["wrong_password"] = "PASS" if wrong.status_code == 400 else f"FAIL ({wrong.status_code})"

            from fastapi.testclient import TestClient
            from app.config import get_settings

            get_settings.cache_clear()
            from app.main import app

            with TestClient(app) as api:
                report["api_without_token"] = "PASS" if api.get("/api/me").status_code == 401 else "FAIL"
                report["api_invalid_token"] = "PASS" if api.get(
                    "/api/me", headers={"Authorization": "Bearer invalid"}
                ).status_code == 401 else "FAIL"
                for role, token in tokens.items():
                    response = api.get("/api/me", headers={"Authorization": f"Bearer {token}"})
                    body = response.json() if response.status_code == 200 else {}
                    actual_role = body.get("application_role") or body.get("role")
                    expected_status = 200 if role == "student" else 403
                    role_matches = actual_role == role if role == "student" else True
                    report[f"{role}_api_token"] = (
                        "PASS" if response.status_code == expected_status and role_matches
                        else f"FAIL ({response.status_code}, role={actual_role or 'pending'})"
                    )
        finally:
            if admin_available:
                for user_id in created:
                    client.delete(f"{url}/auth/v1/admin/users/{user_id}", headers=admin_headers)

    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    try:
        report = run(args.env_file.resolve())
    except Exception as exc:
        report = {"live_auth_test": f"FAIL ({type(exc).__name__})"}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report and all(value == "PASS" for value in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
