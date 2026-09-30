"""Defence-in-depth tenant checks in addition to Supabase RLS."""

from typing import Any

from fastapi import HTTPException, status

from ..dependencies.auth import Principal
from ..dependencies.authorization import institution_membership
from .repository import Repository


DIRECT_INSTITUTION_TABLES = {
    "institutions",
    "institution_memberships",
    "courses",
    "classes",
    "class_sessions",
    "enrollments",
    "attendance",
    "invoices",
    "payments",
    "notifications",
    "news",
}


def require_record(repository: Repository, table: str, record_id: str) -> dict[str, Any]:
    row = repository.get(table, str(record_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{table.rstrip('s').replace('_', ' ')} not found")
    return row


def class_for_record(repository: Repository, table: str, row: dict[str, Any]) -> dict[str, Any] | None:
    if table == "classes":
        return row
    if table in {"class_sessions", "assignments", "exams"}:
        return require_record(repository, "classes", str(row["class_id"]))
    if table == "attendance":
        session = require_record(repository, "class_sessions", str(row["class_session_id"]))
        return require_record(repository, "classes", str(session["class_id"]))
    if table == "assignment_submissions":
        assignment = require_record(repository, "assignments", str(row["assignment_id"]))
        return require_record(repository, "classes", str(assignment["class_id"]))
    if table == "exam_results":
        exam = require_record(repository, "exams", str(row["exam_id"]))
        return require_record(repository, "classes", str(exam["class_id"]))
    if table in {"enrollments", "invoices"} and row.get("class_id"):
        return require_record(repository, "classes", str(row["class_id"]))
    return None


def course_for_record(repository: Repository, table: str, row: dict[str, Any]) -> dict[str, Any] | None:
    if table == "courses":
        return row
    if table == "course_modules":
        return require_record(repository, "courses", str(row["course_id"]))
    if table == "lessons":
        module = require_record(repository, "course_modules", str(row["module_id"]))
        return require_record(repository, "courses", str(module["course_id"]))
    return None


def institution_id_for(repository: Repository, table: str, row: dict[str, Any]) -> str:
    if table == "institutions":
        return str(row["id"])
    if row.get("institution_id"):
        return str(row["institution_id"])
    course = course_for_record(repository, table, row)
    if course:
        return str(course["institution_id"])
    classroom = class_for_record(repository, table, row)
    if classroom:
        return str(classroom["institution_id"])
    if table == "payments":
        invoice = require_record(repository, "invoices", str(row["invoice_id"]))
        return str(invoice["institution_id"])
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Record has no institution scope")


def ensure_read(principal: Principal, institution_id: str) -> None:
    if not principal.is_super_admin:
        institution_membership(principal, institution_id)


def _owns_teaching_record(
    repository: Repository,
    principal: Principal,
    table: str,
    row: dict[str, Any],
    institution_id: str,
) -> bool:
    membership = principal.membership_for(institution_id)
    if membership is None or membership.role != "teacher":
        return False
    course = course_for_record(repository, table, row)
    if course:
        return str(course.get("created_by")) == principal.id
    classroom = class_for_record(repository, table, row)
    if classroom:
        return (
            str(classroom.get("teacher_membership_id")) == membership.id
            or str(classroom.get("owner_user_id")) == principal.id
        )
    return False


def ensure_manage(
    repository: Repository,
    principal: Principal,
    table: str,
    row: dict[str, Any],
    *,
    teachers: bool = False,
) -> str:
    institution_id = institution_id_for(repository, table, row)
    if principal.is_super_admin:
        return institution_id
    membership = institution_membership(principal, institution_id)
    if membership.role == "institute_admin":
        return institution_id
    if teachers and _owns_teaching_record(repository, principal, table, row, institution_id):
        return institution_id
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient institution permissions")


def own_student_membership(principal: Principal, institution_id: str) -> str:
    membership = institution_membership(principal, institution_id)
    if membership.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student membership required")
    return membership.id
