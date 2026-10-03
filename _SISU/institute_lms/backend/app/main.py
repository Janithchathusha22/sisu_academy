import httpx
import psycopg
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field
from uuid import UUID
from urllib.parse import urlparse

from .config import get_settings
from .database import user_client
from .dependencies import Principal, active_user, require_roles

settings = get_settings()
app = FastAPI(title="Sisu Academy API")
app.state.settings = settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
from .admin import router as admin_router
from .profiles import router as profiles_router
from .workspace import router as workspace_router
from .api import academics, commerce, content, identity, institutions, learning

app.include_router(admin_router)
app.include_router(profiles_router)
app.include_router(workspace_router)
# The resource routers use paths such as /me, /courses and /classes that also
# exist in the connected v1 API. Expose their scoped read operations under v2.
# Mutations need separate approval-flow and RLS review before activation.
resource_reads = APIRouter(prefix="/api/v2", tags=["resource reads"])
for resource_router in (
    identity.router, institutions.router,
    learning.router, academics.router, commerce.router, content.router,
):
    for route in resource_router.routes:
        if isinstance(route, APIRoute) and route.methods == {"GET"}:
            resource_reads.add_api_route(
                route.path, route.endpoint, methods=["GET"],
                response_model=route.response_model, tags=route.tags,
            )
app.include_router(resource_reads)


@app.exception_handler(RuntimeError)
async def configuration_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": {"code": "server_configuration", "message": "Server configuration is incomplete. Contact the administrator."}})


@app.exception_handler(psycopg.Error)
async def postgres_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": {"code": "database_unavailable", "message": "The database is temporarily unavailable."}})


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={
        "detail": "Check the form fields and try again.",
        "errors": [{"field": ".".join(map(str, error["loc"])), "message": error["msg"]} for error in exc.errors()],
    })


@app.exception_handler(APIError)
async def database_error(request, exc):
    forbidden = exc.code == "42501"
    return JSONResponse(status_code=403 if forbidden else 503, content={
        "detail": {
            "code": "permission_denied" if forbidden else "database_unavailable",
            "message": "You do not have permission to complete this request." if forbidden else "The database operation is temporarily unavailable.",
        }
    })


@app.exception_handler(httpx.HTTPError)
async def network_error(request, exc):
    return JSONResponse(status_code=503, content={
        "detail": {"code": "upstream_unavailable", "message": "The server could not reach a required service."}
    })


class CourseInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    institution_id: UUID


class AttendanceInput(BaseModel):
    class_session_id: UUID
    student_id: UUID
    status: str = Field(pattern="^(present|absent|excused)$")
    note: str = Field(default="", max_length=500)


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    published: bool | None = None


class ClassUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    published: bool | None = None
    active: bool | None = None


class AttendanceUpdate(BaseModel):
    status: str = Field(pattern="^(present|absent|excused)$")
    note: str | None = Field(default=None, max_length=500)


@app.get("/api/health")
def health():
    try:
        settings.require_auth()
        configured = True
    except RuntimeError:
        configured = False
    return {"status": "running", "backend": "FastAPI", "database": "Supabase PostgreSQL", "configured": configured,
            "supabase_host": urlparse(settings.supabase_url).hostname,
            "supabase_project_ref": settings.supabase_project_ref,
            "token_issuer": settings.supabase_issuer,
            "jwks_url": settings.supabase_jwks_url,
            "connectivity_verified": False}


@app.get("/api/me")
def me(user: Principal = Depends(active_user)):
    return user.profile


@app.get("/api/courses")
def courses(user: Principal = Depends(active_user)):
    client = user_client(user.token)
    query = client.table("courses").select("*")
    if not user.is_super_admin and user.institution_id:
        query = query.eq("institution_id", user.institution_id)
    rows = query.order("created_at", desc=True).execute().data or []
    if user.role not in {"student", "teacher"}:
        return rows
    linked_course_ids = {
        str(row["course_id"]) for row in _workspace_classes(client, user) if row.get("course_id")
    }
    if user.role == "student":
        return [row for row in rows if str(row["id"]) in linked_course_ids]
    return [row for row in rows if row.get("created_by") == user.id or str(row["id"]) in linked_course_ids]


@app.get("/api/courses/{course_id}")
def course(course_id: UUID, user: Principal = Depends(active_user)):
    rows = user_client(user.token).table("courses").select("*").eq("id", str(course_id)).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "Course not found")
    return rows[0]


@app.put("/api/courses/{course_id}")
def update_course(course_id: UUID, data: CourseUpdate,
                  user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    changes = data.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "No changes supplied")
    rows = user_client(user.token).table("courses").update(changes).eq("id", str(course_id)).execute().data
    if not rows:
        raise HTTPException(404, "Course not found")
    return rows[0]


@app.post("/api/courses", status_code=201)
def create_course(data: CourseInput, user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    if user.role != "super_admin" and user.institution_id != str(data.institution_id):
        raise HTTPException(403, "Wrong institution")
    return user_client(user.token).table("courses").insert({
        **data.model_dump(mode="json"), "created_by": user.id
    }).execute().data[0]


@app.get("/api/classes")
def classes(user: Principal = Depends(active_user)):
    return _workspace_classes(user_client(user.token), user)


@app.put("/api/classes/{class_id}")
def update_class(
    class_id: UUID,
    data: ClassUpdate,
    user: Principal = Depends(require_roles("institute_admin", "super_admin")),
):
    changes = data.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "No changes supplied")
    rows = user_client(user.token).table("classes").update(changes).eq("id", str(class_id)).execute().data
    if not rows:
        raise HTTPException(404, "Class not found")
    return rows[0]


def _workspace_classes(client, user: Principal) -> list[dict]:
    """Narrow the public catalogue to classes belonging in this workspace."""
    query = client.table("classes").select("*")
    if not user.is_super_admin and user.institution_id:
        query = query.eq("institution_id", user.institution_id)
    rows = query.order("created_at", desc=True).execute().data or []
    if user.role == "student":
        membership_id = user.profile.get("membership_id")
        if not membership_id:
            return []
        enrollments = (
            client.table("enrollments")
            .select("class_id")
            .eq("student_membership_id", membership_id)
            .eq("status", "active")
            .execute().data or []
        )
        enrolled = {str(row["class_id"]) for row in enrollments}
        return [row for row in rows if str(row["id"]) in enrolled]
    if user.role == "teacher":
        memberships = {item.id for item in user.memberships if item.role == "teacher"}
        return [
            row for row in rows
            if row.get("owner_user_id") == user.id or str(row.get("teacher_membership_id") or "") in memberships
        ]
    return rows


@app.get("/api/students")
def students(user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    return user_client(user.token).table("students").select("*").execute().data


@app.get("/api/teachers")
def teachers(user: Principal = Depends(active_user)):
    return user_client(user.token).table("teachers").select("*").execute().data


@app.get("/api/attendance")
def attendance(user: Principal = Depends(active_user)):
    return user_client(user.token).table("attendance").select("*").order("recorded_at", desc=True).limit(200).execute().data


@app.post("/api/attendance", status_code=201)
def record_attendance(data: AttendanceInput, user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    client = user_client(user.token)
    sessions = client.table("class_sessions").select("id,institution_id,class_id,mode").eq(
        "id", str(data.class_session_id)
    ).limit(1).execute().data
    if not sessions:
        raise HTTPException(404, "Class session not found")
    session = sessions[0]
    row = {
        "institution_id": session["institution_id"],
        "class_id": session["class_id"],
        "class_session_id": str(data.class_session_id),
        "student_membership_id": str(data.student_id),
        "channel": session["mode"],
        "status": data.status,
        "note": data.note or None,
        "recorded_by": user.id,
    }
    return client.table("attendance").insert(row).execute().data[0]


@app.put("/api/attendance/{attendance_id}")
def update_attendance(attendance_id: UUID, data: AttendanceUpdate,
                      user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    rows = user_client(user.token).table("attendance").update(data.model_dump(exclude_none=True)).eq("id", str(attendance_id)).execute().data
    if not rows:
        raise HTTPException(404, "Attendance record not found")
    return rows[0]


@app.get("/api/assignments")
def assignments(user: Principal = Depends(active_user)):
    return user_client(user.token).table("assignments").select("*").limit(200).execute().data


@app.get("/api/exams")
def exams(user: Principal = Depends(active_user)):
    return user_client(user.token).table("exams").select("id,class_id,title,opens_at,closes_at").limit(200).execute().data
