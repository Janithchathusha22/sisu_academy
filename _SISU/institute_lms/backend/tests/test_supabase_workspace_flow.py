from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import dependencies, main, profiles, workspace
from app.identity_context import load_identity
from app.main import app


ADMIN_ID = "10000000-0000-0000-0000-000000000001"
STUDENT_ID = "20000000-0000-0000-0000-000000000002"
APPLICATION_ID = "30000000-0000-0000-0000-000000000003"
INSTITUTION_ID = "40000000-0000-0000-0000-000000000004"
OTHER_INSTITUTION_ID = "40000000-0000-0000-0000-000000000005"
UNVERIFIED_STUDENT_ID = "20000000-0000-0000-0000-000000000006"
CLASS_ID = "50000000-0000-0000-0000-000000000005"
MEMBERSHIP_ID = "60000000-0000-0000-0000-000000000006"


@dataclass
class Principal:
    id: str
    email: str
    role: str
    institution_id: str | None
    token: str = "test-user-token"
    session_id: str = "test-session-id"
    account_status: str = "active"


class Query:
    def __init__(self, database, table):
        self.database = database
        self.table_name = table
        self.filters = []
        self.columns = None
        self.values = None
        self.offset = None

    def select(self, columns="*"):
        if columns != "*":
            self.columns = columns.split(",")
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.filters.append((column, set(values)))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args):
        return self

    def range(self, start, end):
        self.offset = (start, end + 1)
        return self

    def insert(self, values):
        self.values = values
        return self

    def execute(self):
        if self.values is not None:
            row = dict(self.values)
            generated_id = CLASS_ID if self.table_name == "classes" else (
                f"{self.table_name}-{len(self.database.rows[self.table_name])}"
            )
            row.setdefault("id", generated_id)
            if self.table_name == "classes":
                row.setdefault("active", True)
                row.setdefault("published", False)
            if self.table_name == "enrollments":
                row.setdefault("status", "active")
            if self.table_name == "institution_memberships":
                row.setdefault("id", MEMBERSHIP_ID)
            self.database.rows[self.table_name].append(row)
            return SimpleNamespace(data=[row])

        result = list(self.database.rows.get(self.table_name, []))
        for column, expected in self.filters:
            if isinstance(expected, set):
                result = [row for row in result if row.get(column) in expected]
            else:
                result = [row for row in result if row.get(column) == expected]

        if self.table_name == "classes" and self.database.actor.role == "student":
            active_memberships = {
                row["id"] for row in self.database.rows["institution_memberships"]
                if row["user_id"] == self.database.actor.id
                and row["role"] == "student"
                and row["status"] == "active"
            }
            enrolled_classes = {
                row["class_id"] for row in self.database.rows["enrollments"]
                if row["student_membership_id"] in active_memberships and row["status"] == "active"
            }
            result = [
                row for row in result
                if (row.get("active") and row.get("published")) or row["id"] in enrolled_classes
            ]

        if self.offset:
            result = result[slice(*self.offset)]
        if self.columns:
            result = [
                {column: row[column] for column in self.columns if column in row}
                for row in result
            ]
        return SimpleNamespace(data=result)


class Rpc:
    def __init__(self, database, name, arguments):
        self.database = database
        self.name = name
        self.arguments = arguments

    def execute(self):
        if self.database.actor.role != "super_admin":
            raise AssertionError("Only Super Admin RPC calls are expected in this fixture")
        self.database.rpc_calls.append((self.name, self.arguments))
        if self.name == "review_application":
            application = next(
                row for row in self.database.rows["account_applications"]
                if row["id"] == self.arguments["application"]
            )
            assert application["status"] == "pending"
            profile = next(
                row for row in self.database.rows["profiles"]
                if row["id"] == application["user_id"]
            )
            profile["status"] = "verified"
            if application["account_type"] == "student":
                assert self.arguments["institution"] is None
            else:
                assert self.arguments["institution"] == INSTITUTION_ID
                membership_role = {
                    "teacher": "teacher",
                    "institute": "institute_admin",
                }[application["account_type"]]
                self.database.rows["institution_memberships"].append({
                    "id": f"{application['account_type']}-membership",
                    "user_id": profile["id"],
                    "institution_id": self.arguments["institution"],
                    "role": membership_role,
                    "status": "active",
                    "display_name": profile["full_name"],
                })
            application["status"] = "approved"
        elif self.name == "assign_student":
            profile = next(
                row for row in self.database.rows["profiles"]
                if row["id"] == self.arguments["student_profile"]
            )
            assert profile["profile_kind"] == "student" and profile["status"] == "verified"
            assert any(
                row["id"] == self.arguments["institution"]
                for row in self.database.rows["institutions"]
            )
            self.database.rows["institution_memberships"].append({
                "id": MEMBERSHIP_ID,
                "user_id": profile["id"],
                "institution_id": self.arguments["institution"],
                "role": "student",
                "status": "active",
                "display_name": profile["full_name"],
            })
        else:
            raise AssertionError(f"Unexpected RPC {self.name}")
        return SimpleNamespace(data=None)


class Database:
    def __init__(self):
        self.actor = None
        self.rpc_calls = []
        self.rows = {
            "profiles": [{
                "id": STUDENT_ID,
                "email": "student@example.test",
                "username": "student_1",
                "full_name": "Test Student",
                "profile_kind": "student",
                "status": "pending",
            }, {
                "id": UNVERIFIED_STUDENT_ID,
                "email": "unverified@example.test",
                "username": "unverified_1",
                "full_name": "Unverified Student",
                "profile_kind": "student",
                "status": "pending",
            }],
            "platform_roles": [{"user_id": ADMIN_ID, "role": "super_admin", "active": True}],
            "institution_memberships": [],
            "account_applications": [{
                "id": APPLICATION_ID,
                "user_id": STUDENT_ID,
                "account_type": "student",
                "status": "pending",
                "details": {"full_name": "Test Student"},
            }],
            "institutions": [
                {"id": INSTITUTION_ID, "title": "Sisu Institute", "code": "SISU01"},
                {"id": OTHER_INSTITUTION_ID, "title": "Other Institute", "code": "OTHER01"},
            ],
            "classes": [],
            "enrollments": [],
            "courses": [],
            "teachers": [],
            "students": [],
            "schedule": [],
            "attendance": [],
            "assignments": [],
            "materials": [],
            "exams": [],
            "results": [],
            "payments": [],
            "notifications": [],
        }

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, arguments):
        return Rpc(self, name, arguments)


@pytest.fixture
def flow(monkeypatch):
    database = Database()
    state = {"actor": Principal(ADMIN_ID, "admin@example.test", "super_admin", None)}
    database.actor = state["actor"]

    def acting_user():
        database.actor = state["actor"]
        return state["actor"]

    monkeypatch.setitem(app.dependency_overrides, dependencies.current_user, acting_user)
    monkeypatch.setattr(main, "user_client", lambda token: database)
    monkeypatch.setattr(profiles, "user_client", lambda token: database)
    monkeypatch.setattr(workspace, "user_client", lambda token: database)
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, database=database, state=state)
    app.dependency_overrides.pop(dependencies.current_user, None)


def test_student_approval_assignment_class_enrollment_and_student_visibility(flow):
    client, database = flow.client, flow.database

    institutions = client.get("/api/institutions")
    assert institutions.status_code == 200
    assert institutions.json() == database.rows["institutions"]

    approved = client.post(f"/api/applications/{APPLICATION_ID}/review", json={
        "decision": "approved",
        "institution_id": None,
    })
    assert approved.status_code == 200
    assert database.rows["profiles"][0]["status"] == "verified"
    assert database.rows["institution_memberships"] == []

    unassigned = client.get("/api/profiles/unassigned")
    assert unassigned.status_code == 200
    assert [row["id"] for row in unassigned.json()] == [STUDENT_ID]

    unverified_assignment = client.post(
        f"/api/profiles/{UNVERIFIED_STUDENT_ID}/institution",
        json={"institution_id": INSTITUTION_ID},
    )
    assert unverified_assignment.status_code == 422

    assigned = client.post(
        f"/api/profiles/{STUDENT_ID}/institution",
        json={"institution_id": INSTITUTION_ID},
    )
    assert assigned.status_code == 200
    identity = load_identity(database, STUDENT_ID)
    assert identity["role"] == "student"
    assert identity["institution_id"] == INSTITUTION_ID
    assert database.rpc_calls[-1] == ("assign_student", {
        "student_profile": STUDENT_ID,
        "institution": INSTITUTION_ID,
    })
    assert database.rows["institution_memberships"][0]["role"] == "student"
    assert client.get("/api/profiles/unassigned").json() == []
    duplicate_assignment = client.post(
        f"/api/profiles/{STUDENT_ID}/institution",
        json={"institution_id": OTHER_INSTITUTION_ID},
    )
    assert duplicate_assignment.status_code == 409
    assert duplicate_assignment.json()["detail"] == "Student is already assigned to another institution."

    class_response = client.post("/api/classes", json={
        "title": "Algebra",
        "subject": "Mathematics",
        "institution_id": INSTITUTION_ID,
    })
    assert class_response.status_code == 201
    assert "teacher_id" not in class_response.json()
    assert class_response.json()["teacher_membership_id"] is None
    flow.state["actor"] = Principal(
        STUDENT_ID, "student@example.test", identity["role"], identity["institution_id"]
    )
    assert client.get("/api/classes").json() == []

    flow.state["actor"] = Principal(ADMIN_ID, "admin@example.test", "super_admin", None)
    enrolled = client.post("/api/enrollments", json={
        "institution_id": INSTITUTION_ID,
        "class_id": class_response.json()["id"],
        "student_id": MEMBERSHIP_ID,
    })
    assert enrolled.status_code == 201
    assert enrolled.json()["student_membership_id"] == MEMBERSHIP_ID
    assert "student_id" not in enrolled.json()

    flow.state["actor"] = Principal(
        STUDENT_ID, "student@example.test", identity["role"], identity["institution_id"]
    )
    profile = client.get("/api/me")
    assert profile.status_code == 200
    assert profile.json()["role"] == "student"
    assert profile.json()["application_role"] == "student"
    assert profile.json()["account_status"] == "active"
    assert profile.json()["institution_id"] == INSTITUTION_ID
    visible_classes = client.get("/api/classes")
    assert visible_classes.status_code == 200
    assert [row["id"] for row in visible_classes.json()] == [class_response.json()["id"]]


def test_normal_student_cannot_approve_or_assign(flow):
    flow.state["actor"] = Principal(STUDENT_ID, "student@example.test", "student", None)

    approve = flow.client.post(f"/api/applications/{APPLICATION_ID}/review", json={
        "decision": "approved",
    })
    assign = flow.client.post(
        f"/api/profiles/{STUDENT_ID}/institution",
        json={"institution_id": INSTITUTION_ID},
    )

    assert approve.status_code == 403
    assert assign.status_code == 403
    institutions = flow.client.get("/api/institutions")
    assert institutions.status_code == 403
    assert not flow.database.rpc_calls


def test_super_admin_can_create_an_institution(flow):
    response = flow.client.post("/api/institutions", json={
        "title": "New Institute",
        "code": "NEW01",
    })

    assert response.status_code == 201
    assert response.json()["title"] == "New Institute"
    assert response.json()["code"] == "NEW01"


def test_provider_approval_creates_the_correct_active_membership(flow):
    database = flow.database
    applications = []
    for account_type, user_id, application_id in (
        ("teacher", "70000000-0000-0000-0000-000000000001", "80000000-0000-0000-0000-000000000001"),
        ("institute", "70000000-0000-0000-0000-000000000002", "80000000-0000-0000-0000-000000000002"),
    ):
        database.rows["profiles"].append({
            "id": user_id,
            "full_name": f"Test {account_type}",
            "profile_kind": account_type,
            "status": "pending",
        })
        application = {
            "id": application_id,
            "user_id": user_id,
            "account_type": account_type,
            "status": "pending",
        }
        database.rows["account_applications"].append(application)
        applications.append(application)

    for application in applications:
        result = flow.client.post(
            f"/api/applications/{application['id']}/review",
            json={"decision": "approved", "institution_id": INSTITUTION_ID},
        )
        assert result.status_code == 200

    assert [
        (row["role"], row["status"])
        for row in database.rows["institution_memberships"]
    ] == [("teacher", "active"), ("institute_admin", "active")]


def test_new_migration_keeps_student_approval_out_of_provider_memberships():
    migration = (
        Path(__file__).parents[2]
        / "supabase"
        / "migrations"
        / "202610030001_student_approval_and_assignment.sql"
    ).read_text(encoding="utf-8")

    assert "membership_role := case application_row.account_type" in migration
    assert "when 'teacher' then 'teacher'" in migration
    assert "when 'institute' then 'institute_admin'" in migration
    assert "application_row.account_type in ('teacher', 'institute')" in migration
    assert "Student is already assigned to another institution." in migration
    assert "profiles_verified_students_platform_select" in migration
    assert "grant insert on public.institutions, public.classes, public.enrollments to authenticated" in migration
    assert "create policy institutions_admin_insert" in migration
    assert "create policy classes_admin_insert" in migration
    assert "create policy enrollments_admin_insert" in migration
