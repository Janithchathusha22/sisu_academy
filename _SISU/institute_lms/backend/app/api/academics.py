from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..dependencies.auth import Principal, get_current_user
from ..dependencies.authorization import institution_membership
from ..schemas.resources import (
    AssignmentCreate,
    AssignmentUpdate,
    AttendanceCreate,
    AttendanceUpdate,
    ExamCreate,
    ExamResultCreate,
    ExamResultUpdate,
    ExamUpdate,
    SubmissionCreate,
    SubmissionUpdate,
)
from ..services.access import ensure_manage, ensure_read, institution_id_for, require_record
from ..services.repository import Repository, alias_record, alias_rows, get_repository, json_values

router = APIRouter(tags=["academic operations"])


def _student_scope(principal: Principal, institution_id: str) -> str | None:
    if principal.is_super_admin:
        return None
    membership = institution_membership(principal, institution_id)
    return membership.id if membership.role == "student" else None


@router.get("/attendance")
def list_attendance(
    class_id: str = Query(...),
    session_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    classroom = require_record(repository, "classes", class_id)
    institution_id = str(classroom["institution_id"])
    ensure_read(principal, institution_id)
    filters: dict[str, object] = {"class_id": class_id}
    if session_id:
        session = require_record(repository, "class_sessions", session_id)
        if str(session["class_id"]) != class_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Session belongs to another class")
        filters["class_session_id"] = session_id
    student_id = _student_scope(principal, institution_id)
    if student_id:
        filters["student_membership_id"] = student_id
    return alias_rows(repository.list("attendance", filters=filters, order="recorded_at", desc=True, limit=500))


@router.post("/attendance", status_code=status.HTTP_201_CREATED)
def create_attendance(
    body: AttendanceCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    session = require_record(repository, "class_sessions", str(body.class_session_id))
    classroom = require_record(repository, "classes", str(session["class_id"]))
    institution_id = ensure_manage(repository, principal, "classes", classroom, teachers=True)
    student = require_record(repository, "institution_memberships", str(body.student_membership_id))
    if str(student["institution_id"]) != institution_id or student.get("role") != "student" or student.get("status") != "active":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Active student membership required")
    enrolled = repository.list(
        "enrollments",
        filters={"class_id": str(classroom["id"]), "student_membership_id": str(student["id"]), "status": "active"},
        limit=1,
    )
    if not enrolled:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Student is not enrolled in this class")
    values = json_values(body)
    values.update(
        institution_id=institution_id,
        class_id=str(classroom["id"]),
        recorded_by=principal.id,
        recorded_at=values.get("recorded_at") or datetime.now(timezone.utc).isoformat(),
    )
    return alias_record(repository.create("attendance", values)) or {}


@router.get("/attendance/{attendance_id}")
def get_attendance(
    attendance_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "attendance", attendance_id)
    institution_id = institution_id_for(repository, "attendance", row)
    student_id = _student_scope(principal, institution_id)
    if student_id and str(row["student_membership_id"]) != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Attendance access denied")
    return alias_record(row) or {}


@router.patch("/attendance/{attendance_id}")
def update_attendance(
    attendance_id: str,
    body: AttendanceUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "attendance", attendance_id)
    ensure_manage(repository, principal, "attendance", row, teachers=True)
    return alias_record(repository.update("attendance", attendance_id, json_values(body))) or {}


@router.delete("/attendance/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "attendance", attendance_id)
    ensure_manage(repository, principal, "attendance", row, teachers=True)
    repository.delete("attendance", attendance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/assignments")
def list_assignments(
    class_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    classroom = require_record(repository, "classes", class_id)
    ensure_read(principal, str(classroom["institution_id"]))
    return alias_rows(repository.list("assignments", filters={"class_id": class_id}, limit=500))


@router.post("/assignments", status_code=status.HTTP_201_CREATED)
def create_assignment(
    body: AssignmentCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    classroom = require_record(repository, "classes", str(body.class_id))
    institution_id = ensure_manage(repository, principal, "classes", classroom, teachers=True)
    values = json_values(body)
    values.update(institution_id=institution_id, created_by=principal.id)
    return alias_record(repository.create("assignments", values)) or {}


@router.get("/assignments/{assignment_id}")
def get_assignment(
    assignment_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "assignments", assignment_id)
    ensure_read(principal, institution_id_for(repository, "assignments", row))
    return alias_record(row) or {}


@router.patch("/assignments/{assignment_id}")
def update_assignment(
    assignment_id: str,
    body: AssignmentUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "assignments", assignment_id)
    ensure_manage(repository, principal, "assignments", row, teachers=True)
    return alias_record(repository.update("assignments", assignment_id, json_values(body))) or {}


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "assignments", assignment_id)
    ensure_manage(repository, principal, "assignments", row, teachers=True)
    repository.delete("assignments", assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/submissions")
def list_submissions(
    assignment_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    assignment = require_record(repository, "assignments", assignment_id)
    institution_id = institution_id_for(repository, "assignments", assignment)
    filters: dict[str, object] = {"assignment_id": assignment_id}
    student_id = _student_scope(principal, institution_id)
    if student_id:
        filters["student_membership_id"] = student_id
    return alias_rows(repository.list("assignment_submissions", filters=filters, limit=500))


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def create_submission(
    body: SubmissionCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    assignment = require_record(repository, "assignments", str(body.assignment_id))
    institution_id = institution_id_for(repository, "assignments", assignment)
    student_id = _student_scope(principal, institution_id)
    if not student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student membership required")
    values = json_values(body)
    values.update(institution_id=institution_id, student_membership_id=student_id, status="submitted", submitted_at=datetime.now(timezone.utc).isoformat())
    return alias_record(repository.create("assignment_submissions", values)) or {}


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "assignment_submissions", submission_id)
    institution_id = institution_id_for(repository, "assignment_submissions", row)
    student_id = _student_scope(principal, institution_id)
    if student_id and str(row["student_membership_id"]) != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Submission access denied")
    return alias_record(row) or {}


@router.patch("/submissions/{submission_id}")
def update_submission(
    submission_id: str,
    body: SubmissionUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "assignment_submissions", submission_id)
    institution_id = institution_id_for(repository, "assignment_submissions", row)
    values = json_values(body)
    membership = principal.membership_for(institution_id)
    if not principal.is_super_admin and membership and membership.role == "student":
        if membership.id != str(row["student_membership_id"]):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Submission access denied")
        forbidden = {"score", "feedback"}.intersection(values)
        if forbidden or values.get("status") == "graded":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Students cannot grade submissions")
    else:
        ensure_manage(repository, principal, "assignment_submissions", row, teachers=True)
    return alias_record(repository.update("assignment_submissions", submission_id, values)) or {}


@router.delete("/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "assignment_submissions", submission_id)
    institution_id = institution_id_for(repository, "assignment_submissions", row)
    membership = principal.membership_for(institution_id)
    if not principal.is_super_admin and membership and membership.role == "student":
        if membership.id != str(row["student_membership_id"]) or row.get("status") != "draft":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a draft submission can be deleted")
    else:
        ensure_manage(repository, principal, "assignment_submissions", row, teachers=True)
    repository.delete("assignment_submissions", submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _public_exam(row: dict, student: bool) -> dict:
    result = alias_record(row) or {}
    if student and isinstance(result.get("questions"), list):
        result["questions"] = [
            {key: value for key, value in question.items() if key not in {"answer", "correct_answer"}}
            for question in result["questions"]
        ]
    return result


@router.get("/exams")
def list_exams(
    class_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    classroom = require_record(repository, "classes", class_id)
    institution_id = str(classroom["institution_id"])
    student = _student_scope(principal, institution_id) is not None
    return [_public_exam(row, student) for row in repository.list("exams", filters={"class_id": class_id}, limit=500)]


@router.post("/exams", status_code=status.HTTP_201_CREATED)
def create_exam(
    body: ExamCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    classroom = require_record(repository, "classes", str(body.class_id))
    institution_id = ensure_manage(repository, principal, "classes", classroom, teachers=True)
    values = json_values(body)
    values.update(institution_id=institution_id, created_by=principal.id)
    return alias_record(repository.create("exams", values)) or {}


@router.get("/exams/{exam_id}")
def get_exam(
    exam_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "exams", exam_id)
    institution_id = institution_id_for(repository, "exams", row)
    student = _student_scope(principal, institution_id) is not None
    return _public_exam(row, student)


@router.patch("/exams/{exam_id}")
def update_exam(
    exam_id: str,
    body: ExamUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "exams", exam_id)
    ensure_manage(repository, principal, "exams", row, teachers=True)
    return alias_record(repository.update("exams", exam_id, json_values(body))) or {}


@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "exams", exam_id)
    ensure_manage(repository, principal, "exams", row, teachers=True)
    repository.delete("exams", exam_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/results")
def list_results(
    exam_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    exam = require_record(repository, "exams", exam_id)
    institution_id = institution_id_for(repository, "exams", exam)
    filters: dict[str, object] = {"exam_id": exam_id}
    student_id = _student_scope(principal, institution_id)
    if student_id:
        filters["student_membership_id"] = student_id
    return alias_rows(repository.list("exam_results", filters=filters, limit=500))


@router.post("/results", status_code=status.HTTP_201_CREATED)
def create_result(
    body: ExamResultCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    exam = require_record(repository, "exams", str(body.exam_id))
    institution_id = ensure_manage(repository, principal, "exams", exam, teachers=True)
    student = require_record(repository, "institution_memberships", str(body.student_membership_id))
    if str(student["institution_id"]) != institution_id or student.get("role") != "student":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Student belongs to another institution")
    values = json_values(body)
    values.update(institution_id=institution_id, graded_by=principal.id)
    return alias_record(repository.create("exam_results", values)) or {}


@router.get("/results/{result_id}")
def get_result(
    result_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "exam_results", result_id)
    institution_id = institution_id_for(repository, "exam_results", row)
    student_id = _student_scope(principal, institution_id)
    if student_id and str(row["student_membership_id"]) != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Result access denied")
    return alias_record(row) or {}


@router.patch("/results/{result_id}")
def update_result(
    result_id: str,
    body: ExamResultUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "exam_results", result_id)
    ensure_manage(repository, principal, "exam_results", row, teachers=True)
    return alias_record(repository.update("exam_results", result_id, json_values(body))) or {}


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(
    result_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "exam_results", result_id)
    ensure_manage(repository, principal, "exam_results", row, teachers=True)
    repository.delete("exam_results", result_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
