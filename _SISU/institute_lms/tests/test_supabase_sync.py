import importlib
import os
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest import mock


if "frappe" not in sys.modules:
    sys.modules["frappe"] = types.ModuleType("frappe")

sync = importlib.import_module("institute_lms.supabase_sync")


class FakeUtils:
    @staticmethod
    def get_datetime(value):
        return datetime.fromisoformat(value)

    @staticmethod
    def get_system_timezone():
        return "Asia/Colombo"


def valid_environment(**overrides):
    values = {
        "SISU_SUPABASE_SYNC_ENABLED": "1",
        "SISU_SUPABASE_DATABASE_URL": (
            "postgresql://sisu_reporting_writer.example:password"
            "@aws-0-region.pooler.supabase.com:5432/postgres?sslmode=require"
        ),
        "SISU_SUPABASE_SOURCE_SITE_ID": "sisu-academy",
    }
    values.update(overrides)
    return values


class SupabaseSyncTests(unittest.TestCase):
    def test_disabled_configuration_is_fail_closed(self):
        self.assertIsNone(sync.configuration({}))
        self.assertIsNone(sync.configuration({"SISU_SUPABASE_SYNC_ENABLED": "0"}))

    def test_configuration_rejects_unsafe_database_urls(self):
        unsafe_urls = [
            "https://example.supabase.co",
            "postgresql://user:password@evil.example:5432/postgres?sslmode=require",
            "postgresql://user:password@aws.pooler.supabase.com:6543/postgres?sslmode=require",
            "postgresql://user:password@aws.pooler.supabase.com:5432/postgres",
            "postgresql://user@aws.pooler.supabase.com:5432/postgres?sslmode=require",
        ]
        for database_url in unsafe_urls:
            with self.subTest(database_url=database_url):
                with self.assertRaises(sync.SupabaseSyncConfigurationError):
                    sync.configuration(
                        valid_environment(SISU_SUPABASE_DATABASE_URL=database_url)
                    )

    def test_configuration_accepts_supabase_session_pooler_with_ssl(self):
        config = sync.configuration(valid_environment())
        self.assertEqual(config.source_site_id, "sisu-academy")
        self.assertTrue(config.database_url.startswith("postgresql://"))

    def test_snapshot_has_strict_non_pii_allowlist(self):
        institutes = [
            {
                "name": "inst-hash",
                "code": "SISU",
                "title": "SISU Academy",
                "language": "en",
                "school_mode": "0",
                "creation": "2026-09-29 10:00:00",
                "modified": "2026-09-29 11:00:00",
                "phone": "PRIVATE-INSTITUTE-PHONE",
                "support_email": "PRIVATE-INSTITUTE-EMAIL",
                "address": "PRIVATE-ADDRESS",
                "base_fee": 99999,
            }
        ]
        members = [
            {
                "name": "member-hash",
                "institute": "inst-hash",
                "role": "Admin",
                "active": "1",
                "creation": "2026-09-29 10:10:00",
                "modified": "2026-09-29 11:10:00",
                "user": "PRIVATE-USER-EMAIL",
                "full_name": "PRIVATE-FULL-NAME",
                "phone": "PRIVATE-MEMBER-PHONE",
                "contact_email": "PRIVATE-CONTACT-EMAIL",
            }
        ]

        with mock.patch.object(sync.frappe, "utils", FakeUtils(), create=True):
            institute_rows, member_rows = sync.build_snapshot(
                institutes, members, "sisu-academy"
            )

        flattened = " ".join(
            str(value) for row in institute_rows + member_rows for value in row
        )
        self.assertEqual(len(institute_rows), 1)
        self.assertEqual(len(member_rows), 1)
        self.assertIs(institute_rows[0][5], False)
        self.assertIs(member_rows[0][4], True)
        self.assertEqual(institute_rows[0][6].tzinfo, timezone.utc)
        self.assertNotIn("PRIVATE-", flattened)

    def test_run_does_not_touch_network_when_disabled(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(
                sync, "_source_rows", side_effect=AssertionError("source read")
            ),
            mock.patch.object(
                sync, "_write_snapshot", side_effect=AssertionError("network call")
            ),
        ):
            self.assertEqual(sync.run(), {"enabled": False, "synced": False})


if __name__ == "__main__":
    unittest.main()
