import os

os.environ.setdefault("SESSION_SECRET", "test-session-secret-that-is-longer-than-32-characters")

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.sessions import decrypt_tokens, digest, encrypt_tokens
from app.identity_context import load_identity


class IdentityClient:
    def __init__(self, rows):
        self.rows = rows
        self.name = ""
        self.filters = []

    def table(self, name):
        self.name = name
        self.filters = []
        return self

    def select(self, *args): return self
    def eq(self, column, value):
        self.filters.append((column, value))
        return self
    def limit(self, *args): return self

    def execute(self):
        from types import SimpleNamespace
        rows = self.rows.get(self.name, [])
        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]
        return SimpleNamespace(data=rows)


def test_session_tokens_are_encrypted_and_round_trip():
    get_settings.cache_clear()
    encrypted = encrypt_tokens("access-value", "refresh-value")
    assert "access-value" not in encrypted
    assert "refresh-value" not in encrypted
    assert decrypt_tokens(encrypted) == ("access-value", "refresh-value")


def test_digest_is_stable_and_does_not_reveal_session_id():
    value = "opaque-browser-session"
    assert digest(value) == digest(value)
    assert value not in digest(value)


def test_health_does_not_claim_database_connectivity():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert "configured" in response.json()


def test_protected_api_rejects_missing_cookie():
    response = TestClient(app).get("/api/courses")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_mutation_rejects_missing_cookie():
    response = TestClient(app).post("/api/courses", json={
        "title": "Course", "description": "", "institution_id": "00000000-0000-0000-0000-000000000000"
    })
    assert response.status_code == 401


def test_verified_student_profile_without_membership_does_not_grant_student_role():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "student", "profile_kind": "student", "status": "verified"}],
        "platform_roles": [], "institution_memberships": [],
    }), "student")
    assert identity["role"] is None
    assert identity["account_status"] == "active"
    assert identity["institution_id"] is None


def test_student_role_and_institution_come_from_active_student_membership():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "student", "profile_kind": "student", "status": "verified"}],
        "platform_roles": [],
        "institution_memberships": [{
            "id": "membership",
            "user_id": "student",
            "institution_id": "institution",
            "role": "student",
            "status": "active",
            "member_code": "S001",
        }],
    }), "student")
    assert identity["role"] == "student"
    assert identity["institution_id"] == "institution"
    assert identity["membership_id"] == "membership"


def test_pending_teacher_keeps_kind_but_cannot_be_active():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "teacher", "profile_kind": "teacher", "status": "pending"}],
        "platform_roles": [], "institution_memberships": [],
    }), "teacher")
    assert identity["role"] is None
    assert identity["account_status"] == "pending"


def test_profile_kind_from_account_selection_does_not_grant_role():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "teacher", "profile_kind": "teacher", "status": "verified"}],
        "platform_roles": [], "institution_memberships": [],
    }), "teacher")
    assert identity["role"] is None


def test_mismatched_membership_role_does_not_set_a_student_institution():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "student", "profile_kind": "student", "status": "verified"}],
        "platform_roles": [],
        "institution_memberships": [{
            "id": "old-admin-membership",
            "user_id": "student",
            "institution_id": "wrong-institution",
            "role": "institute_admin",
            "status": "active",
        }],
    }), "student")
    assert identity["role"] is None
    assert identity["institution_id"] is None
    assert identity["membership_id"] is None


def test_super_admin_role_requires_active_database_platform_role():
    inactive_identity = load_identity(IdentityClient({
        "profiles": [{"id": "admin", "profile_kind": "student", "status": "verified"}],
        "platform_roles": [{"user_id": "admin", "role": "super_admin", "active": False}],
        "institution_memberships": [],
    }), "admin")
    assert inactive_identity["role"] is None

    active_identity = load_identity(IdentityClient({
        "profiles": [{"id": "admin", "profile_kind": "student", "status": "verified"}],
        "platform_roles": [{"user_id": "admin", "role": "super_admin", "active": True}],
        "institution_memberships": [],
    }), "admin")
    assert active_identity["role"] == "super_admin"
