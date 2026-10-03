from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app import workspace
from app.dependencies.auth import Membership, Principal


INSTITUTION_ID = "30000000-0000-0000-0000-000000000003"
TEACHER_ID = "10000000-0000-0000-0000-000000000001"
MEMBERSHIP_ID = "20000000-0000-0000-0000-000000000002"
CLASS_ID = "40000000-0000-0000-0000-000000000004"


class Query:
    def __init__(self, client, table):
        self.client = client
        self.name = table
        self.filters = []
        self.pending = None

    def select(self, *args): return self
    def eq(self, column, value):
        self.filters.append((column, value))
        return self
    def limit(self, *args): return self
    def insert(self, row):
        self.pending = row
        return self
    def execute(self):
        from types import SimpleNamespace
        if self.pending is not None:
            saved = {"id": "50000000-0000-0000-0000-000000000005", **self.pending}
            self.client.rows.setdefault(self.name, []).append(saved)
            return SimpleNamespace(data=[saved])
        rows = self.client.rows.get(self.name, [])
        return SimpleNamespace(data=[
            row for row in rows
            if all(str(row.get(column)) == str(value) for column, value in self.filters)
        ])


class Client:
    def __init__(self, teacher_membership_id):
        self.rows = {"classes": [{
            "id": CLASS_ID,
            "institution_id": INSTITUTION_ID,
            "owner_user_id": None,
            "teacher_membership_id": teacher_membership_id,
        }]}

    def table(self, name):
        return Query(self, name)


def teacher_principal():
    membership = Membership(MEMBERSHIP_ID, INSTITUTION_ID, "teacher", "active")
    return Principal(
        id=TEACHER_ID,
        email="teacher@example.test",
        token="valid-token",
        profile={
            "application_role": "teacher",
            "account_status": "active",
            "institution_id": INSTITUTION_ID,
            "membership_id": MEMBERSHIP_ID,
        },
        memberships=(membership,),
        platform_roles=frozenset(),
    )


def schedule_input():
    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    return workspace.ScheduleInput(
        class_id=CLASS_ID,
        title="Revision session",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
    )


def test_assigned_teacher_can_schedule_their_class(monkeypatch):
    client = Client(MEMBERSHIP_ID)
    monkeypatch.setattr(workspace, "user_client", lambda token: client)

    result = workspace.schedule(schedule_input(), teacher_principal())

    assert result["class_id"] == CLASS_ID
    assert result["institution_id"] == INSTITUTION_ID
    assert result["mode"] == "online"


def test_teacher_cannot_schedule_an_unassigned_class(monkeypatch):
    client = Client("60000000-0000-0000-0000-000000000006")
    monkeypatch.setattr(workspace, "user_client", lambda token: client)

    with pytest.raises(HTTPException) as error:
        workspace.schedule(schedule_input(), teacher_principal())

    assert error.value.status_code == 403
    assert error.value.detail == "Teaching assignment required"
