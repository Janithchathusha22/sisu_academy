from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import profiles as profile_routes
from app.dependencies import auth as auth_dependency
from app.main import app


ORIGIN = "http://127.0.0.1:5178"
ADMIN_ID = "10000000-0000-0000-0000-000000000001"
STUDENT_ID = "20000000-0000-0000-0000-000000000002"
INSTITUTION_ID = "30000000-0000-0000-0000-000000000003"


class Query:
    def __init__(self, client, table):
        self.client = client
        self.name = table
        self.filters = []
        self.columns = None
        self.row_range = None

    def select(self, *args):
        if args and args[0] != "*":
            self.columns = args[0].split(",")
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.filters.append((column, set(values)))
        return self

    def limit(self, *args):
        return self

    def range(self, start, end):
        self.row_range = (start, end + 1)
        return self

    def execute(self):
        rows = self.client.rows.get(self.name, [])
        for column, expected in self.filters:
            if isinstance(expected, set):
                rows = [row for row in rows if row.get(column) in expected]
            else:
                rows = [row for row in rows if row.get(column) == expected]
        if self.row_range:
            rows = rows[slice(*self.row_range)]
        if self.columns:
            rows = [{column: row[column] for column in self.columns if column in row} for row in rows]
        return SimpleNamespace(data=rows)


class Rpc:
    def __init__(self, client, name, arguments=None):
        self.client = client
        self.name = name
        self.arguments = arguments or {}

    def execute(self):
        if self.name == "provision_current_profile":
            raise AssertionError("Existing profile should not be provisioned again")
        assert self.name == "assign_student"
        student_id = self.arguments["student_profile"]
        institution_id = self.arguments["institution"]
        profile = next(row for row in self.client.rows["profiles"] if row["id"] == student_id)
        assert profile["profile_kind"] == "student"
        assert profile["status"] == "verified"
        assert any(row["id"] == institution_id for row in self.client.rows["institutions"])
        assert not any(
            row["user_id"] == student_id and row["institution_id"] != institution_id
            and row["status"] in {"pending", "active"}
            for row in self.client.rows["institution_memberships"]
        )
        self.client.rpc_calls.append((self.name, self.arguments))
        self.client.rows["institution_memberships"].append({
            "id": "40000000-0000-0000-0000-000000000004",
            "user_id": student_id,
            "institution_id": institution_id,
            "role": "student",
            "status": "active",
            "member_code": "STU-1",
        })
        return SimpleNamespace(data=None)


class Auth:
    def __init__(self):
        self.user_id = ADMIN_ID

    def get_user(self, token):
        assert token == "valid-token"
        return SimpleNamespace(user=SimpleNamespace(id=self.user_id, email="admin@example.test"))


class SupabaseClient:
    def __init__(self, profiles=None, platform_roles=None, memberships=None, institutions=None):
        self.auth = Auth()
        self.rows = {
            "profiles": profiles or [],
            "platform_roles": platform_roles or [],
            "institution_memberships": memberships or [],
            "institutions": institutions or [],
        }
        self.rpc_calls = []

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, arguments=None):
        return Rpc(self, name, arguments)


@pytest.fixture
def api_client(monkeypatch):
    student = {
        "id": STUDENT_ID,
        "email": "student@example.test",
        "full_name": "Verified Student",
        "profile_kind": "student",
        "status": "verified",
    }
    institution = {
        "id": INSTITUTION_ID,
        "title": "Sisu Institute",
        "code": "SISU01",
    }
    supabase = SupabaseClient(
        profiles=[
            {
                "id": ADMIN_ID,
                "email": "admin@example.test",
                "full_name": "Platform Admin",
                "profile_kind": "institute",
                "status": "verified",
            },
            student,
        ],
        platform_roles=[{"user_id": ADMIN_ID, "role": "super_admin", "active": True}],
        institutions=[institution],
    )
    monkeypatch.setattr(auth_dependency, "user_client", lambda token, settings=None: supabase)
    monkeypatch.setattr(auth_dependency, "validate_access_token", lambda token, settings: {"sub": supabase.auth.user_id})
    monkeypatch.setattr(profile_routes, "user_client", lambda token: supabase)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client, supabase, student, institution


def auth_headers():
    return {"Authorization": "Bearer valid-token"}


def test_super_admin_reads_only_verified_students_without_pending_or_active_memberships(api_client):
    test_client, supabase, student, _ = api_client
    supabase.rows["profiles"].extend([
        {
            "id": "50000000-0000-0000-0000-000000000005",
            "email": "unverified@example.test",
            "full_name": "Unverified Student",
            "profile_kind": "student",
            "status": "pending",
        },
        {
            "id": "60000000-0000-0000-0000-000000000006",
            "email": "teacher@example.test",
            "full_name": "Verified Teacher",
            "profile_kind": "teacher",
            "status": "verified",
        },
    ])
    supabase.rows["institution_memberships"].extend([
        {
            "user_id": "70000000-0000-0000-0000-000000000007",
            "role": "student",
            "status": "pending",
        },
        {
            "user_id": "80000000-0000-0000-0000-000000000008",
            "role": "teacher",
            "status": "active",
        },
    ])
    supabase.rows["profiles"].extend([
        {
            "id": "70000000-0000-0000-0000-000000000007",
            "email": "pending-member@example.test",
            "full_name": "Pending Member",
            "profile_kind": "student",
            "status": "verified",
        },
        {
            "id": "80000000-0000-0000-0000-000000000008",
            "email": "active-member@example.test",
            "full_name": "Active Member",
            "profile_kind": "student",
            "status": "verified",
        },
    ])

    response = test_client.get("/api/profiles/unassigned", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == [{
        "id": student["id"],
        "email": student["email"],
        "full_name": student["full_name"],
    }]


def test_unassigned_student_listing_includes_students_after_first_page(api_client):
    test_client, supabase, _, _ = api_client
    late_student_ids = []
    for index in range(101):
        profile_id = f"90000000-0000-0000-0000-{index:012d}"
        late_student_ids.append(profile_id)
        supabase.rows["profiles"].append({
            "id": profile_id,
            "email": f"student-{index}@example.test",
            "full_name": f"Student {index}",
            "profile_kind": "student",
            "status": "verified",
        })

    response = test_client.get("/api/profiles/unassigned", headers=auth_headers())

    assert response.status_code == 200
    assert {row["id"] for row in response.json()} >= set(late_student_ids)


def test_super_admin_reads_institutions_with_required_fields(api_client):
    test_client, _, _, institution = api_client

    response = test_client.get("/api/institutions", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == [institution]
    assert "/api/institutions" in app.openapi()["paths"]


def test_assign_student_calls_rpc_and_me_returns_active_institution(api_client):
    test_client, supabase, student, _ = api_client

    response = test_client.post(
        f"/api/profiles/{student['id']}/institution",
        headers=auth_headers(),
        json={"institution_id": INSTITUTION_ID},
    )

    assert response.status_code == 200
    assert supabase.rpc_calls == [("assign_student", {
        "student_profile": STUDENT_ID,
        "institution": INSTITUTION_ID,
    })]

    supabase.rows["platform_roles"] = []
    supabase.auth.user_id = STUDENT_ID
    me = test_client.get("/api/me", headers=auth_headers())

    assert me.status_code == 200
    assert me.json()["application_role"] == "student"
    assert me.json()["account_status"] == "active"
    assert me.json()["institution_id"] == INSTITUTION_ID


def test_normal_student_cannot_assign_students(api_client):
    test_client, supabase, student, _ = api_client
    supabase.rows["platform_roles"] = []
    supabase.auth.user_id = ADMIN_ID
    supabase.rows["profiles"] = [{
        **supabase.rows["profiles"][0],
        "profile_kind": "student",
    }]

    response = test_client.post(
        f"/api/profiles/{student['id']}/institution",
        headers=auth_headers(),
        json={"institution_id": INSTITUTION_ID},
    )

    assert response.status_code == 403
    assert not supabase.rpc_calls


def test_unverified_student_cannot_be_assigned(api_client):
    test_client, supabase, student, _ = api_client
    student["status"] = "pending"

    response = test_client.post(
        f"/api/profiles/{student['id']}/institution",
        headers=auth_headers(),
        json={"institution_id": INSTITUTION_ID},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "A verified student is required."
    assert not supabase.rpc_calls


def test_student_visibility_migration_allows_only_active_platform_admins():
    from pathlib import Path

    migration = (
        Path(__file__).parents[2]
        / "supabase"
        / "migrations"
        / "202610020002_platform_student_profile_visibility.sql"
    ).read_text(encoding="utf-8").lower()

    assert "create policy profiles_verified_students_platform_select" in migration
    assert "profile_kind = 'student'" in migration
    assert "status = 'verified'" in migration
    assert "private.is_active_profile()" in migration
    assert "private.is_platform_admin()" in migration
