"""One-way, privacy-minimised reporting sync from Frappe to Supabase.

MariaDB/Frappe remains authoritative.  This module is intentionally not
whitelisted and must only run in a trusted backend worker or through
``bench execute``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import frappe


ENABLED_VALUES = {"1", "true", "yes", "on"}
SECURE_SSL_MODES = {"require", "verify-ca", "verify-full"}
SUPABASE_HOST_SUFFIXES = (".supabase.co", ".supabase.com")
SOURCE_SITE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
TENANT_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")

INSTITUTE_SOURCE_FIELDS = (
    "name",
    "code",
    "title",
    "language",
    "school_mode",
    "creation",
    "modified",
)
MEMBER_SOURCE_FIELDS = (
    "name",
    "institute",
    "role",
    "active",
    "creation",
    "modified",
)

INSTITUTE_UPSERT = """
    INSERT INTO reporting.institutes AS current_row (
        source_site_id, frappe_name, code, title, language, school_mode,
        source_created_at, source_modified_at, synced_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (source_site_id, frappe_name) DO UPDATE SET
        code = EXCLUDED.code,
        title = EXCLUDED.title,
        language = EXCLUDED.language,
        school_mode = EXCLUDED.school_mode,
        source_created_at = EXCLUDED.source_created_at,
        source_modified_at = EXCLUDED.source_modified_at,
        synced_at = NOW()
    WHERE EXCLUDED.source_modified_at >= current_row.source_modified_at
"""

MEMBER_UPSERT = """
    INSERT INTO reporting.members AS current_row (
        source_site_id, frappe_name, institute_frappe_name, role, active,
        source_created_at, source_modified_at, synced_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (source_site_id, frappe_name) DO UPDATE SET
        institute_frappe_name = EXCLUDED.institute_frappe_name,
        role = EXCLUDED.role,
        active = EXCLUDED.active,
        source_created_at = EXCLUDED.source_created_at,
        source_modified_at = EXCLUDED.source_modified_at,
        synced_at = NOW()
    WHERE EXCLUDED.source_modified_at >= current_row.source_modified_at
"""


class SupabaseSyncConfigurationError(ValueError):
    """Raised for a fail-closed sync configuration error."""


@dataclass(frozen=True)
class SyncConfiguration:
    database_url: str
    source_site_id: str


def configuration(environ: Mapping[str, str] | None = None) -> SyncConfiguration | None:
    """Return validated configuration, or ``None`` when sync is disabled."""
    values = environ if environ is not None else os.environ
    enabled = str(values.get("SISU_SUPABASE_SYNC_ENABLED", "0")).strip().lower()
    if enabled not in ENABLED_VALUES:
        return None

    database_url = str(values.get("SISU_SUPABASE_DATABASE_URL", "")).strip()
    source_site_id = str(values.get("SISU_SUPABASE_SOURCE_SITE_ID", "")).strip().lower()
    if not database_url:
        raise SupabaseSyncConfigurationError("SISU_SUPABASE_DATABASE_URL is required")
    if not SOURCE_SITE_ID_PATTERN.fullmatch(source_site_id):
        raise SupabaseSyncConfigurationError("SISU_SUPABASE_SOURCE_SITE_ID is invalid")

    try:
        parsed = urlparse(database_url)
        port = parsed.port
    except ValueError as exc:
        raise SupabaseSyncConfigurationError("Supabase database URL is invalid") from exc

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise SupabaseSyncConfigurationError("Supabase database URL must use PostgreSQL")
    if not parsed.hostname or not parsed.username or not parsed.password:
        raise SupabaseSyncConfigurationError("Supabase database URL is incomplete")

    hostname = parsed.hostname.lower()
    if not any(hostname.endswith(suffix) for suffix in SUPABASE_HOST_SUFFIXES):
        raise SupabaseSyncConfigurationError("Database host is not a Supabase host")
    if port not in {None, 5432}:
        raise SupabaseSyncConfigurationError("Use direct or Session Pooler port 5432")

    ssl_mode = parse_qs(parsed.query).get("sslmode", [""])[-1].lower()
    if ssl_mode not in SECURE_SSL_MODES:
        raise SupabaseSyncConfigurationError("Supabase database URL must enforce SSL")

    return SyncConfiguration(database_url=database_url, source_site_id=source_site_id)


def _utc_timestamp(value) -> datetime:
    if not isinstance(value, datetime):
        value = frappe.utils.get_datetime(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(frappe.utils.get_system_timezone()))
    return value.astimezone(timezone.utc)


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ENABLED_VALUES
    return bool(value)


def build_snapshot(institutes, members, source_site_id: str):
    """Map only the approved, non-PII reporting fields."""
    institute_rows = []
    institute_names = set()
    institute_codes = set()

    for row in institutes:
        name = str(row.get("name") or "").strip()
        code = str(row.get("code") or "").strip().upper()
        title = str(row.get("title") or "").strip()
        language = str(row.get("language") or "").strip().lower()
        if not name or not title:
            raise SupabaseSyncConfigurationError("Institute identity is incomplete")
        if not TENANT_CODE_PATTERN.fullmatch(code):
            raise SupabaseSyncConfigurationError("Institute code is invalid")
        if language not in {"en", "si", "ta"}:
            raise SupabaseSyncConfigurationError("Institute language is invalid")
        if name in institute_names or code in institute_codes:
            raise SupabaseSyncConfigurationError("Institute identity is duplicated")

        institute_names.add(name)
        institute_codes.add(code)
        institute_rows.append(
            (
                source_site_id,
                name,
                code,
                title,
                language,
                _as_bool(row.get("school_mode")),
                _utc_timestamp(row.get("creation")),
                _utc_timestamp(row.get("modified")),
            )
        )

    if not institute_rows:
        raise SupabaseSyncConfigurationError("No institute exists on the source site")

    member_rows = []
    for row in members:
        institute_name = str(row.get("institute") or "").strip()
        role = str(row.get("role") or "").strip()
        name = str(row.get("name") or "").strip()
        if institute_name not in institute_names:
            raise SupabaseSyncConfigurationError("Member has an unknown institute")
        if not name or role not in {"Student", "Teacher", "Admin"}:
            raise SupabaseSyncConfigurationError("Member identity or role is invalid")
        member_rows.append(
            (
                source_site_id,
                name,
                institute_name,
                role,
                _as_bool(row.get("active")),
                _utc_timestamp(row.get("creation")),
                _utc_timestamp(row.get("modified")),
            )
        )

    return institute_rows, member_rows


def _source_rows():
    institutes = frappe.get_all(
        "IL Institute",
        fields=list(INSTITUTE_SOURCE_FIELDS),
        order_by="name asc",
        limit_page_length=1000,
    )

    members = []
    start = 0
    page_size = 500
    while True:
        page = frappe.get_all(
            "IL Member",
            fields=list(MEMBER_SOURCE_FIELDS),
            order_by="name asc",
            start=start,
            limit_page_length=page_size,
        )
        members.extend(page)
        if len(page) < page_size:
            break
        start += page_size

    return institutes, members


def _write_snapshot(database_url: str, institute_rows, member_rows):
    import psycopg2
    from psycopg2.extras import execute_batch

    connection = psycopg2.connect(
        database_url,
        connect_timeout=10,
        application_name="sisu_reporting_sync",
        options="-c statement_timeout=30000 -c lock_timeout=5000",
    )
    try:
        connection.autocommit = False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_regclass('reporting.institutes'), "
                "to_regclass('reporting.members')"
            )
            if cursor.fetchone() != ("reporting.institutes", "reporting.members"):
                raise SupabaseSyncConfigurationError(
                    "Supabase reporting schema has not been initialized"
                )
            execute_batch(cursor, INSTITUTE_UPSERT, institute_rows, page_size=100)
            if member_rows:
                execute_batch(cursor, MEMBER_UPSERT, member_rows, page_size=500)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def validate_source_snapshot(source_site_id: str = "sisu-academy"):
    """Validate the live source mapping without opening a network connection."""
    source_site_id = str(source_site_id).strip().lower()
    if not SOURCE_SITE_ID_PATTERN.fullmatch(source_site_id):
        raise SupabaseSyncConfigurationError("Source site ID is invalid")
    institutes, members = _source_rows()
    institute_rows, member_rows = build_snapshot(institutes, members, source_site_id)
    return {
        "valid": True,
        "institutes": len(institute_rows),
        "members": len(member_rows),
        "personal_fields_included": False,
    }


def run():
    """Synchronise a privacy-minimised snapshot when explicitly enabled."""
    config = configuration()
    if config is None:
        return {"enabled": False, "synced": False}

    lock_key = f"il_supabase_reporting_sync:{config.source_site_id}"
    try:
        with frappe.cache.lock(lock_key, timeout=300, blocking_timeout=1):
            institutes, members = _source_rows()
            institute_rows, member_rows = build_snapshot(
                institutes, members, config.source_site_id
            )
            _write_snapshot(config.database_url, institute_rows, member_rows)
            return {
                "enabled": True,
                "synced": True,
                "institutes": len(institute_rows),
                "members": len(member_rows),
            }
    except Exception as exc:
        error_code = getattr(exc, "pgcode", None)
        safe_message = type(exc).__name__
        if error_code:
            safe_message += f" (PostgreSQL code {error_code})"
        frappe.log_error(safe_message, "Supabase reporting sync failed")
        raise
