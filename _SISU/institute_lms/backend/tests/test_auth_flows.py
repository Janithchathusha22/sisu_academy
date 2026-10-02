"""Bearer-token authentication regressions; live verification is separate."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app import main
from app.services.repository import get_repository
from app import profiles as profile_routes
from app.dependencies import auth as auth_dependency
from app.main import app


ORIGIN = "http://127.0.0.1:5178"
UID = "10000000-0000-0000-0000-000000000001"


class Query:
    def __init__(self, client, table):
        self.client = client
        self.name = table
        self.filters = []

    def select(self, *args): return self
    def eq(self, column, value):
        self.filters.append((column, value))
        return self
    def limit(self, *args): return self

    def execute(self):
        if self.client.database_error:
            raise RuntimeError("database unavailable")
        rows = self.client.rows.get(self.name, [])
        rows = [row for row in rows if all(row.get(column) == value for column, value in self.filters)]
        return SimpleNamespace(data=rows)


class Rpc:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def execute(self):
        if self.name != "provision_current_profile":
            raise AssertionError(f"Unexpected RPC: {self.name}")
        kind = self.client.account_type
        self.client.rows["profiles"] = [{
            "id": UID,
            "email": "student@example.test",
            "full_name": "Test User",
            "profile_kind": kind,
            "status": "verified" if kind == "student" else "pending",
        }]
        if kind in {"teacher", "institute"}:
            self.client.application_created = True
        return SimpleNamespace(data=self.client.rows["profiles"][0])


class Auth:
    def __init__(self, valid=True):
        self.valid = valid

    def get_user(self, token):
        if not self.valid or token != "valid-token":
            raise AuthApiError("invalid token", 401, None)
        return SimpleNamespace(user=SimpleNamespace(id=UID, email="student@example.test"))


class SupabaseClient:
    def __init__(self, profile=None, valid=True, account_type="student"):
        self.auth = Auth(valid)
        self.account_type = account_type
        self.application_created = False
        self.database_error = False
        self.rows = {
            "profiles": [profile] if profile else [],
            "platform_roles": [],
            "institution_memberships": [],
        }

    def table(self, name):
        return Query(self, name)

    def rpc(self, name):
        return Rpc(self, name)


@pytest.fixture
def client(monkeypatch):
    profile = {
        "id": UID,
        "email": "student@example.test",
        "full_name": "Test Student",
        "profile_kind": "student",
        "status": "verified",
    }
    supabase = SupabaseClient(profile)
    monkeypatch.setattr(auth_dependency, "user_client", lambda token, settings=None: supabase)
    monkeypatch.setattr(auth_dependency, "validate_access_token", lambda token, settings: {"sub": UID})
    monkeypatch.setattr(main, "user_client", lambda token: supabase)
    monkeypatch.setattr(profile_routes, "user_client", lambda token: supabase)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client, supabase


def test_valid_bearer_token_loads_verified_profile(client):
    test_client, _ = client
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["id"] == UID
    assert response.json()["role"] == "student"


def test_resource_read_routes_use_v2_without_colliding_with_connected_api(client):
    test_client, _ = client
    assert test_client.get("/api/courses").status_code == 401
    assert test_client.get(
        "/api/v2/modules", params={"course_id": UID}
    ).status_code == 401
    assert test_client.post("/api/v2/modules").status_code == 405


@pytest.mark.parametrize("header", [None, "Basic value", "Bearer "])
def test_missing_or_malformed_bearer_is_rejected(client, header):
    test_client, _ = client
    headers = {"Authorization": header} if header else {}
    response = test_client.get("/api/me", headers=headers)
    assert response.status_code == 401


def test_invalid_or_expired_token_is_rejected(client):
    test_client, _ = client
    response = test_client.get("/api/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Supabase rejected the sign-in session"


def test_supabase_auth_outage_is_503(client):
    test_client, supabase = client
    def unavailable(token):
        raise AuthApiError("service unavailable", 503, None)
    supabase.auth.get_user = unavailable
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Supabase authentication service is unavailable"


def test_profile_database_failure_is_not_mislabeled_as_invalid_token(client):
    test_client, supabase = client
    supabase.database_error = True
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Server configuration is incomplete. Contact the administrator."


def test_confirmed_student_without_profile_is_provisioned(client):
    test_client, supabase = client
    supabase.rows["profiles"] = []
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["id"] == UID
    assert response.json()["profile_kind"] == "student"


def test_unprovisioned_teacher_gets_application_but_remains_pending(monkeypatch):
    supabase = SupabaseClient(account_type="teacher")
    monkeypatch.setattr(auth_dependency, "user_client", lambda token, settings=None: supabase)
    monkeypatch.setattr(auth_dependency, "validate_access_token", lambda token, settings: {"sub": UID})
    with TestClient(app, base_url=ORIGIN) as test_client:
        response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Application profile approval is pending"
    assert supabase.application_created is True


def test_pending_profile_cannot_read_business_data(client):
    test_client, supabase = client
    supabase.rows["profiles"][0]["status"] = "pending"
    response = test_client.get("/api/courses", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


@pytest.mark.parametrize("account_status", ["rejected", "suspended"])
def test_rejected_or_suspended_profile_is_not_reactivated(client, account_status):
    test_client, supabase = client
    supabase.rows["profiles"][0]["status"] = account_status
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403
    assert supabase.rows["profiles"][0]["status"] == account_status


def test_pending_profile_is_not_returned_by_me(client):
    test_client, supabase = client
    supabase.rows["profiles"][0]["profile_kind"] = "teacher"
    supabase.rows["profiles"][0]["status"] = "pending"
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Application profile approval is pending"


def test_verified_provider_without_membership_gets_no_provider_access(client):
    test_client, supabase = client
    supabase.rows["profiles"][0]["profile_kind"] = "teacher"
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Application profile is not approved"


def test_other_users_profile_is_not_used(client):
    test_client, supabase = client
    supabase.rows["profiles"][0]["id"] = "20000000-0000-0000-0000-000000000002"
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["id"] == UID


def test_user_metadata_cannot_grant_platform_role(client):
    test_client, supabase = client
    supabase.auth.get_user = lambda token: SimpleNamespace(user=SimpleNamespace(
        id=UID, email="student@example.test", user_metadata={"role": "super_admin", "status": "verified"}
    ))
    response = test_client.get("/api/applications", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_pending_profile_cannot_use_platform_role_row(client):
    test_client, supabase = client
    supabase.rows["profiles"][0]["status"] = "pending"
    supabase.rows["platform_roles"] = [{"role": "super_admin", "active": True}]
    response = test_client.get("/api/applications", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_student_cannot_call_super_admin_route(client):
    test_client, _ = client
    response = test_client.get("/api/applications", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_verified_super_admin_routes_from_active_platform_grant(client):
    test_client, supabase = client
    supabase.rows["platform_roles"] = [{"user_id": UID, "role": "super_admin", "active": True}]
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == UID
    assert body["profile_kind"] == "student"
    assert body["application_role"] == "super_admin"
    assert body["role"] == "super_admin"
    assert body["institution_id"] is None
    assert test_client.get("/api/applications", headers={"Authorization": "Bearer valid-token"}).status_code == 200


def test_super_admin_overview_returns_live_repository_counts(client, monkeypatch):
    test_client, supabase = client
    supabase.rows["platform_roles"] = [{"user_id": UID, "role": "super_admin", "active": True}]
    counts = {
        ("institutions", None): 3,
        ("profiles", (("profile_kind", "student"), ("status", "verified"))): 12,
        ("institution_memberships", (("role", "student"), ("status", "active"))): 8,
        ("institution_memberships", (("role", "teacher"), ("status", "active"))): 4,
        ("account_applications", (("status", "pending"),)): 2,
    }

    class OverviewRepository:
        def count(self, table, *, filters=None):
            key = (table, tuple(sorted((filters or {}).items())) or None)
            return counts[key]

    monkeypatch.setitem(app.dependency_overrides, get_repository, lambda: OverviewRepository())
    response = test_client.get("/api/admin/overview", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.json() == {
        "role": "super_admin",
        "email": "student@example.test",
        "full_name": "Test Student",
        "institutions": 3,
        "verified_students": 12,
        "active_students": 8,
        "active_teachers": 4,
        "pending_applications": 2,
    }


def test_student_cannot_read_super_admin_overview(client):
    test_client, _ = client
    response = test_client.get("/api/admin/overview", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_inactive_platform_grant_does_not_route_to_admin(client):
    test_client, supabase = client
    supabase.rows["platform_roles"] = [{"user_id": UID, "role": "super_admin", "active": False}]
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.json()["role"] == "student"


def test_institute_admin_routes_from_active_membership(client):
    test_client, supabase = client
    institution = "30000000-0000-0000-0000-000000000003"
    supabase.rows["profiles"][0]["profile_kind"] = "institute"
    supabase.rows["institution_memberships"] = [{
        "id": "40000000-0000-0000-0000-000000000004",
        "user_id": UID, "institution_id": institution, "role": "institute_admin",
        "status": "active", "member_code": "ADM-1",
    }]
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["role"] == "institute_admin"
    assert response.json()["institution_id"] == institution
    assert test_client.get("/api/institutions", headers={"Authorization": "Bearer valid-token"}).status_code == 200
    assert test_client.get("/api/applications", headers={"Authorization": "Bearer valid-token"}).status_code == 403
    other = "50000000-0000-0000-0000-000000000005"
    denied = test_client.post("/api/classes", headers={"Authorization": "Bearer valid-token"}, json={
        "title": "Wrong campus", "subject": "Math", "institution_id": other,
    })
    assert denied.status_code == 403


def test_inactive_or_other_user_membership_cannot_grant_institute_admin(client):
    test_client, supabase = client
    supabase.rows["institution_memberships"] = [
        {"id": "1", "user_id": UID, "institution_id": "2", "role": "institute_admin", "status": "pending"},
        {"id": "3", "user_id": "other", "institution_id": "4", "role": "institute_admin", "status": "active"},
    ]
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.json()["role"] == "student"


def test_admin_membership_wins_over_student_membership_without_crossing_tenants(client):
    test_client, supabase = client
    supabase.rows["institution_memberships"] = [
        {"id": "1", "user_id": UID, "institution_id": "school-a", "role": "student", "status": "active"},
        {"id": "2", "user_id": UID, "institution_id": "school-b", "role": "institute_admin", "status": "active"},
    ]
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["role"] == "institute_admin"
    assert response.json()["institution_id"] == "school-b"


def test_cors_preflight_allows_authorization_header(client):
    test_client, _ = client
    response = test_client.options("/api/me", headers={
        "Origin": ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
