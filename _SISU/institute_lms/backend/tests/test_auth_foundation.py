from fastapi.testclient import TestClient

from app.main import app
from app.identity_context import load_identity


class IdentityClient:
    def __init__(self, rows):
        self.rows = rows
        self.name = ""

    def table(self, name):
        self.name = name
        return self

    def select(self, *args): return self
    def eq(self, *args): return self
    def limit(self, *args): return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=self.rows.get(self.name, []))


def test_health_does_not_claim_database_connectivity():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["connectivity_verified"] is False
    assert body["supabase_project_ref"] == "yfdettlsvgsslzjjhoxo"
    assert body["token_issuer"] == "https://yfdettlsvgsslzjjhoxo.supabase.co/auth/v1"
    assert body["jwks_url"] == (
        "https://yfdettlsvgsslzjjhoxo.supabase.co/auth/v1/.well-known/jwks.json"
    )


def test_protected_api_rejects_missing_bearer_token():
    response = TestClient(app).get("/api/courses")
    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token required"


def test_mutation_rejects_missing_bearer_token():
    response = TestClient(app).post("/api/courses", json={
        "title": "Course", "description": "", "institution_id": "00000000-0000-0000-0000-000000000000"
    })
    assert response.status_code == 401


def test_student_identity_uses_verified_profile_without_membership():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "student", "profile_kind": "student", "status": "verified"}],
        "platform_roles": [], "institution_memberships": [],
    }), "student")
    assert identity["application_role"] == "student"
    assert identity["role"] == "student"
    assert identity["account_status"] == "active"


def test_pending_teacher_keeps_kind_but_cannot_be_active():
    identity = load_identity(IdentityClient({
        "profiles": [{"id": "teacher", "profile_kind": "teacher", "status": "pending"}],
        "platform_roles": [], "institution_memberships": [],
    }), "teacher")
    assert identity["application_role"] is None
    assert identity["role"] is None
    assert identity["account_status"] == "pending"
