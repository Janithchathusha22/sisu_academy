"""Read-only Supabase configuration, Auth, schema, and RLS diagnostic.

Credentials and row contents are never printed. This does not create test users
or replace the live end-to-end registration test.
"""
from __future__ import annotations

import json
import httpx
import psycopg

from app.config import get_settings


REQUIRED_COLUMNS = {
    "profiles": {"id", "username", "email", "full_name", "profile_kind", "status"},
    "platform_roles": {"user_id", "role", "active"},
    "institution_memberships": {"id", "institution_id", "user_id", "role", "status"},
    "account_applications": {"id", "user_id", "account_type", "status"},
}
REQUIRED_POLICIES = {
    ("profiles", "profiles_own_select"),
    ("profiles", "profiles_own_update"),
    ("profiles", "profiles_verified_students_platform_select"),
    ("account_applications", "applications_read_own"),
    ("institution_memberships", "active_profile"),
    ("courses", "active_profile"),
}


def run() -> tuple[dict, int]:
    settings = get_settings()
    required = {
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_PUBLISHABLE_KEY": settings.supabase_publishable_key,
    }
    missing = sorted(name for name, value in required.items() if not value)
    report = {
        "supabase_configuration": "PASS" if not missing else "FAIL",
        "missing_configuration": missing,
        "auth_configuration": "NOT TESTED",
        "database_connection": "NOT TESTED",
        "required_schema": "NOT TESTED",
        "rls": "NOT TESTED",
        "limitations": [
            "No accounts are created and no database rows are changed.",
            "Student/teacher signup, login, persistence, and cross-user RLS require the live flow test.",
        ],
    }
    try:
        settings.validate_runtime()
        if not settings.supabase_url or not settings.supabase_publishable_key:
            raise ValueError("Public Auth configuration is incomplete")
        response = httpx.get(
            settings.supabase_url.rstrip("/") + "/auth/v1/settings",
            headers={"apikey": settings.supabase_publishable_key},
            timeout=10,
        )
        report["auth_configuration"] = "PASS" if response.is_success else "FAIL"
    except (RuntimeError, ValueError, httpx.HTTPError):
        report["auth_configuration"] = "FAIL"

    if not settings.supabase_database_url:
        return report, 2

    try:
        with psycopg.connect(settings.supabase_database_url, connect_timeout=10) as connection:
            connection.execute("set transaction read only")
            connection.execute("set local statement_timeout='15s'")
            connection.execute("select 1").fetchone()
            report["database_connection"] = "PASS"

            rows = connection.execute("""
                select c.relname, a.attname
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                join pg_attribute a on a.attrelid = c.oid
                where n.nspname = 'public' and c.relkind = 'r'
                  and a.attnum > 0 and not a.attisdropped
            """).fetchall()
            actual: dict[str, set[str]] = {}
            for table, column in rows:
                actual.setdefault(table, set()).add(column)
            missing_schema = [
                f"{table}.{column}"
                for table, columns in REQUIRED_COLUMNS.items()
                for column in sorted(columns - actual.get(table, set()))
            ]
            report["missing_schema"] = missing_schema
            report["required_schema"] = "PASS" if not missing_schema else "FAIL"

            rls = dict(connection.execute("""
                select c.relname, c.relrowsecurity
                from pg_class c join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public' and c.relname = any(%s)
            """, (list(REQUIRED_COLUMNS),)).fetchall())
            policies = set(connection.execute("""
                select tablename, policyname from pg_policies where schemaname = 'public'
            """).fetchall())
            trigger = connection.execute("""
                select exists (
                  select 1 from pg_trigger
                  where tgrelid = 'auth.users'::regclass
                    and tgname = 'on_auth_user_created' and tgenabled = 'O'
                )
            """).fetchone()[0]
            missing_rls = [f"RLS disabled: {table}" for table in REQUIRED_COLUMNS if not rls.get(table)]
            missing_rls += [f"policy missing: {table}.{policy}" for table, policy in sorted(REQUIRED_POLICIES - policies)]
            if not trigger:
                missing_rls.append("Auth provisioning trigger missing")
            report["rls_findings"] = missing_rls
            report["rls"] = "PASS" if not missing_rls else "FAIL"
            connection.rollback()
    except psycopg.Error:
        report["database_connection"] = "FAIL"

    ok = all(report[key] == "PASS" for key in (
        "supabase_configuration", "auth_configuration", "database_connection", "required_schema", "rls"
    ))
    return report, 0 if ok else 1


if __name__ == "__main__":
    result, exit_code = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(exit_code)
