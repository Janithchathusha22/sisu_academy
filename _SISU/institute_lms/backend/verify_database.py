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
    "institutions": {"id", "title", "code"},
    "institution_memberships": {"id", "institution_id", "user_id", "role", "status"},
    "account_applications": {"id", "user_id", "account_type", "status"},
    "app_sessions": {"id", "session_hash", "user_id", "token_ciphertext", "csrf_hash", "expires_at"},
    "courses": {"id", "institution_id", "title"},
    "classes": {"id", "institution_id", "title", "subject", "active", "published"},
    "enrollments": {"id", "institution_id", "class_id", "student_membership_id", "status"},
}
REQUIRED_POLICIES = {
    ("profiles", "profiles_own_select"),
    ("profiles", "profiles_own_update"),
    ("profiles", "profiles_verified_students_platform_select"),
    ("platform_roles", "platform_roles_own_or_platform_select"),
    ("institutions", "institutions_member_select"),
    ("institutions", "institutions_admin_insert"),
    ("institutions", "active_profile"),
    ("account_applications", "applications_read_own"),
    ("institution_memberships", "active_profile"),
    ("institution_memberships", "institution_memberships_scoped_select"),
    ("courses", "active_profile"),
    ("courses", "courses_scoped_select"),
    ("classes", "active_profile"),
    ("classes", "classes_catalog_or_member_select"),
    ("classes", "classes_admin_insert"),
    ("enrollments", "active_profile"),
    ("enrollments", "enrollments_scoped_select"),
    ("enrollments", "enrollments_admin_insert"),
}
FORCED_RLS_TABLES = {
    "profiles",
    "platform_roles",
    "institutions",
    "institution_memberships",
    "courses",
    "classes",
    "enrollments",
}


def run() -> tuple[dict, int]:
    settings = get_settings()
    required = {
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_PUBLISHABLE_KEY": settings.supabase_publishable_key,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
        "SUPABASE_DATABASE_URL": settings.supabase_database_url,
        "SESSION_SECRET": settings.session_secret,
    }
    missing = sorted(name for name, value in required.items() if not value)
    report = {
        "supabase_configuration": "PASS" if not missing else "FAIL",
        "missing_configuration": missing,
        "auth_configuration": "NOT TESTED",
        "database_connection": "NOT TESTED",
        "auth_users": "NOT TESTED",
        "required_schema": "NOT TESTED",
        "rls": "NOT TESTED",
        "rpc_permissions": "NOT TESTED",
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
            auth_users_exists = connection.execute("""
                select exists (
                  select 1
                  from pg_class c
                  join pg_namespace n on n.oid = c.relnamespace
                  where n.nspname = 'auth' and c.relname = 'users' and c.relkind = 'r'
                )
            """).fetchone()[0]
            report["auth_users"] = "PASS" if auth_users_exists else "FAIL"

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
                select c.relname, c.relrowsecurity, c.relforcerowsecurity
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
            missing_rls = []
            for table in REQUIRED_COLUMNS:
                enabled, forced = rls.get(table, (False, False))
                if not enabled:
                    missing_rls.append(f"RLS disabled: {table}")
                elif table in FORCED_RLS_TABLES and not forced:
                    missing_rls.append(f"RLS not forced: {table}")
            missing_rls += [f"policy missing: {table}.{policy}" for table, policy in sorted(REQUIRED_POLICIES - policies)]
            if not trigger:
                missing_rls.append("Auth provisioning trigger missing")
            report["rls_findings"] = missing_rls
            report["rls"] = "PASS" if not missing_rls else "FAIL"

            rpc_checks = connection.execute("""
                select p.proname, p.prosecdef,
                       has_function_privilege('authenticated', p.oid, 'EXECUTE'),
                       not has_function_privilege('anon', p.oid, 'EXECUTE')
                from pg_proc p
                where p.oid in (
                  to_regprocedure('public.review_application(uuid,text,uuid)'),
                  to_regprocedure('public.assign_student(uuid,uuid)')
                )
            """).fetchall()
            required_rpcs = {"review_application", "assign_student"}
            report["rpc_permissions"] = (
                "PASS"
                if {row[0] for row in rpc_checks} == required_rpcs
                and all(row[1] and row[2] and row[3] for row in rpc_checks)
                else "FAIL"
            )
            connection.rollback()
    except psycopg.Error:
        report["database_connection"] = "FAIL"

    ok = all(report[key] == "PASS" for key in (
        "supabase_configuration", "auth_configuration", "database_connection", "auth_users",
        "required_schema", "rls", "rpc_permissions"
    ))
    return report, 0 if ok else 1


if __name__ == "__main__":
    result, exit_code = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(exit_code)
