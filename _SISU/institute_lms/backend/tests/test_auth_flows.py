"""Bearer-token authentication regressions; live verification is separate."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.dependencies import auth as auth_dependency
from app.main import app


ORIGIN = "http://127.0.0.1:5178"
UID = "10000000-0000-0000-0000-000000000001"


class Query:
    def __init__(self, client, table):
        self.client = client
        self.name = table

    def select(self, *args): return self
    def eq(self, *args): return self
    def limit(self, *args): return self

    def execute(self):
        return SimpleNamespace(data=self.client.rows.get(self.name, []))


class Auth:
    def __init__(self, valid=True):
        self.valid = valid

    def get_user(self, token):
        if not self.valid or token != "valid-token":
            raise ValueError("invalid token")
        return SimpleNamespace(user=SimpleNamespace(id=UID, email="student@example.test"))


class SupabaseClient:
    def __init__(self, profile=None, valid=True):
        self.auth = Auth(valid)
        self.rows = {
            "profiles": [profile] if profile else [],
            "platform_roles": [],
            "institution_memberships": [],
        }

    def table(self, name):
        return Query(self, name)


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
    monkeypatch.setattr(main, "user_client", lambda token: supabase)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client, supabase


def test_valid_bearer_token_loads_verified_profile(client):
    test_client, _ = client
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json()["id"] == UID
    assert response.json()["role"] == "student"


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
    assert response.json()["detail"] == "Invalid or expired token"


def test_unprovisioned_profile_is_forbidden(client):
    test_client, supabase = client
    supabase.rows["profiles"] = []
    response = test_client.get("/api/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_pending_profile_cannot_read_business_data(client):
    test_client, supabase = client
    supabase.rows["profiles"][0]["status"] = "pending"
    response = test_client.get("/api/courses", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_student_cannot_call_super_admin_route(client):
    test_client, _ = client
    response = test_client.get("/api/applications", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403


def test_cors_preflight_allows_authorization_header(client):
    test_client, _ = client
    response = test_client.options("/api/me", headers={
        "Origin": ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
