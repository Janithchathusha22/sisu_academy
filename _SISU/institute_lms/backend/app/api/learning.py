from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..dependencies.auth import Principal, get_current_user
from ..dependencies.authorization import institution_membership, require_institution_role, resolve_institution
from ..schemas.resources import (
    ClassCreate,
    ClassUpdate,
    CourseCreate,
    CourseUpdate,
    EnrollmentCreate,
    EnrollmentUpdate,
    LessonCreate,
    LessonUpdate,
    ModuleCreate,
    ModuleUpdate,
    SessionCreate,
    SessionUpdate,
)
from ..services.access import ensure_manage, ensure_read, institution_id_for, require_record
from ..services.repository import Repository, alias_record, alias_rows, get_repository, json_values

router = APIRouter(tags=["learning"])


@router.get("/courses")
def list_courses(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    return alias_rows(repository.list("courses", filters={"institution_id": selected}, limit=500))


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def create_course(
    body: CourseCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    institution_id = str(body.institution_id)
    require_institution_role(principal, institution_id, "institute_admin", "teacher")
    values = json_values(body)
    values["created_by"] = principal.id
    return alias_record(repository.create("courses", values)) or {}


@router.get("/courses/{course_id}")
def get_course(
    course_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "courses", course_id)
    ensure_read(principal, str(row["institution_id"]))
    return alias_record(row) or {}


@router.patch("/courses/{course_id}")
def update_course(
    course_id: str,
    body: CourseUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "courses", course_id)
    ensure_manage(repository, principal, "courses", row, teachers=True)
    return alias_record(repository.update("courses", course_id, json_values(body))) or {}


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "courses", course_id)
    ensure_manage(repository, principal, "courses", row, teachers=True)
    repository.delete("courses", course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/modules")
def list_modules(
    course_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    course = require_record(repository, "courses", course_id)
    ensure_read(principal, str(course["institution_id"]))
    return alias_rows(repository.list("course_modules", filters={"course_id": course_id}, order="position", desc=False, limit=500))


@router.post("/modules", status_code=status.HTTP_201_CREATED)
def create_module(
    body: ModuleCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    course = require_record(repository, "courses", str(body.course_id))
    ensure_manage(repository, principal, "courses", course, teachers=True)
    return alias_record(repository.create("course_modules", json_values(body))) or {}


@router.get("/modules/{module_id}")
def get_module(
    module_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "course_modules", module_id)
    ensure_read(principal, institution_id_for(repository, "course_modules", row))
    return alias_record(row) or {}


@router.patch("/modules/{module_id}")
def update_module(
    module_id: str,
    body: ModuleUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "course_modules", module_id)
    ensure_manage(repository, principal, "course_modules", row, teachers=True)
    return alias_record(repository.update("course_modules", module_id, json_values(body))) or {}


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "course_modules", module_id)
    ensure_manage(repository, principal, "course_modules", row, teachers=True)
    repository.delete("course_modules", module_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/lessons")
def list_lessons(
    module_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    module = require_record(repository, "course_modules", module_id)
    ensure_read(principal, institution_id_for(repository, "course_modules", module))
    return alias_rows(repository.list("lessons", filters={"module_id": module_id}, order="position", desc=False, limit=500))


@router.post("/lessons", status_code=status.HTTP_201_CREATED)
def create_lesson(
    body: LessonCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    module = require_record(repository, "course_modules", str(body.module_id))
    ensure_manage(repository, principal, "course_modules", module, teachers=True)
    return alias_record(repository.create("lessons", json_values(body))) or {}


@router.get("/lessons/{lesson_id}")
def get_lesson(
    lesson_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "lessons", lesson_id)
    ensure_read(principal, institution_id_for(repository, "lessons", row))
    return alias_record(row) or {}


@router.patch("/lessons/{lesson_id}")
def update_lesson(
    lesson_id: str,
    body: LessonUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "lessons", lesson_id)
    ensure_manage(repository, principal, "lessons", row, teachers=True)
    return alias_record(repository.update("lessons", lesson_id, json_values(body))) or {}


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "lessons", lesson_id)
    ensure_manage(repository, principal, "lessons", row, teachers=True)
    repository.delete("lessons", lesson_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes")
def list_classes(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    return alias_rows(repository.list("classes", filters={"institution_id": selected}, limit=500))


@router.post("/classes", status_code=status.HTTP_201_CREATED)
def create_class(
    body: ClassCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    institution_id = str(body.institution_id)
    membership = require_institution_role(principal, institution_id, "institute_admin", "teacher")
    values = json_values(body)
    if membership and membership.role == "teacher":
        requested_teacher = str(body.teacher_membership_id) if body.teacher_membership_id else membership.id
        if requested_teacher != membership.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Teachers can assign only themselves")
        values.update(teacher_membership_id=membership.id, owner_type="teacher", owner_user_id=principal.id)
    else:
        values.setdefault("owner_type", "institution")
    return alias_record(repository.create("classes", values)) or {}


@router.get("/classes/{class_id}")
def get_class(
    class_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "classes", class_id)
    ensure_read(principal, str(row["institution_id"]))
    return alias_record(row) or {}


@router.patch("/classes/{class_id}")
def update_class(
    class_id: str,
    body: ClassUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "classes", class_id)
    ensure_manage(repository, principal, "classes", row, teachers=True)
    values = json_values(body)
    membership = principal.membership_for(str(row["institution_id"]))
    if membership and membership.role == "teacher" and values.get("teacher_membership_id") not in (None, membership.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Teachers cannot reassign a class")
    return alias_record(repository.update("classes", class_id, values)) or {}


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_class(
    class_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "classes", class_id)
    ensure_manage(repository, principal, "classes", row, teachers=True)
    repository.update("classes", class_id, {"active": False})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions")
def list_sessions(
    class_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    classroom = require_record(repository, "classes", class_id)
    ensure_read(principal, str(classroom["institution_id"]))
    return alias_rows(repository.list("class_sessions", filters={"class_id": class_id}, order="starts_at", desc=True, limit=500))


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    classroom = require_record(repository, "classes", str(body.class_id))
    institution_id = ensure_manage(repository, principal, "classes", classroom, teachers=True)
    values = json_values(body)
    values["institution_id"] = institution_id
    return alias_record(repository.create("class_sessions", values)) or {}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "class_sessions", session_id)
    ensure_read(principal, institution_id_for(repository, "class_sessions", row))
    return alias_record(row) or {}


@router.patch("/sessions/{session_id}")
def update_session(
    session_id: str,
    body: SessionUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "class_sessions", session_id)
    ensure_manage(repository, principal, "class_sessions", row, teachers=True)
    values = json_values(body)
    starts_at = values.get("starts_at", row.get("starts_at"))
    ends_at = values.get("ends_at", row.get("ends_at"))
    if starts_at and ends_at and str(ends_at) <= str(starts_at):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ends_at must be after starts_at")
    return alias_record(repository.update("class_sessions", session_id, values)) or {}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "class_sessions", session_id)
    ensure_manage(repository, principal, "class_sessions", row, teachers=True)
    repository.delete("class_sessions", session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/enrollments")
def list_enrollments(
    class_id: str = Query(...),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    classroom = require_record(repository, "classes", class_id)
    institution_id = str(classroom["institution_id"])
    membership = institution_membership(principal, institution_id) if not principal.is_super_admin else None
    filters: dict[str, object] = {"class_id": class_id}
    if membership and membership.role == "student":
        filters["student_membership_id"] = membership.id
    return alias_rows(repository.list("enrollments", filters=filters, limit=500))


@router.post("/enrollments", status_code=status.HTTP_201_CREATED)
def create_enrollment(
    body: EnrollmentCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    classroom = require_record(repository, "classes", str(body.class_id))
    institution_id = str(classroom["institution_id"])
    student = require_record(repository, "institution_memberships", str(body.student_membership_id))
    if str(student["institution_id"]) != institution_id or student.get("role") != "student" or student.get("status") != "active":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Active student membership required")
    if not principal.is_super_admin:
        actor = institution_membership(principal, institution_id)
        if actor.role == "student" and actor.id != str(body.student_membership_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Students can enroll only themselves")
        if actor.role == "teacher":
            ensure_manage(repository, principal, "classes", classroom, teachers=True)
    values = json_values(body)
    values.update(institution_id=institution_id, status="active", access_override="automatic")
    return alias_record(repository.create("enrollments", values)) or {}


@router.get("/enrollments/{enrollment_id}")
def get_enrollment(
    enrollment_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "enrollments", enrollment_id)
    membership = principal.membership_for(str(row["institution_id"]))
    if not principal.is_super_admin and (membership is None or (membership.role == "student" and membership.id != str(row["student_membership_id"]))):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Enrollment access denied")
    return alias_record(row) or {}


@router.patch("/enrollments/{enrollment_id}")
def update_enrollment(
    enrollment_id: str,
    body: EnrollmentUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "enrollments", enrollment_id)
    ensure_manage(repository, principal, "enrollments", row, teachers=True)
    return alias_record(repository.update("enrollments", enrollment_id, json_values(body))) or {}


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_enrollment(
    enrollment_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "enrollments", enrollment_id)
    ensure_manage(repository, principal, "enrollments", row, teachers=True)
    repository.update("enrollments", enrollment_id, {"status": "cancelled", "access_override": "closed"})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
