import httpx
import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError
from pydantic import AwareDatetime, BaseModel, Field
from uuid import UUID

from .auth import router as auth_router
from .config import get_settings
from .database import user_client
from .dependencies import Principal, active_user, current_user, require_roles

settings = get_settings()
app = FastAPI(title="Sisu Academy API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url.rstrip("/")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(auth_router)

from .profiles import router as profiles_router
from .workspace import router as workspace_router

app.include_router(profiles_router)
app.include_router(workspace_router)


@app.exception_handler(RuntimeError)
async def configuration_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Server configuration is incomplete. Contact the administrator."})


@app.exception_handler(psycopg.Error)
async def postgres_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database connection unavailable. Contact the administrator."})


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
        "detail": "Permission denied." if forbidden else "Database operation unavailable. Contact the administrator."
    })


@app.exception_handler(httpx.HTTPError)
async def network_error(request, exc):
    return JSONResponse(status_code=503, content={
        "detail": "The server could not reach the authentication or database service."
    })


class CourseInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    institution_id: UUID


class AttendanceInput(BaseModel):
    class_id: UUID
    student_id: UUID
    occurred_at: AwareDatetime
    status: str = Field(pattern="^(Present|Absent|Late|Excused)$")


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    published: bool | None = None


class AttendanceUpdate(BaseModel):
    status: str = Field(pattern="^(Present|Absent|Late|Excused)$")


@app.get("/api/health")
def health():
    configured = bool(settings.supabase_url and settings.supabase_publishable_key and settings.supabase_service_role_key)
    configured = configured and bool(settings.supabase_database_url and len(settings.session_secret) >= 32)
    return {"status": "running", "backend": "FastAPI", "database": "Supabase PostgreSQL", "configured": configured,
            "connectivity_verified": False}


@app.get("/api/me")
def me(user: Principal = Depends(current_user)):
    rows = user_client(user.token).table("profiles").select(
        "id,email,username,full_name,profile_kind,status,language,country,bio,tagline,"
        "curriculum,languages,grades,qualifications,socials,avatar_path,cover_path,created_at,updated_at"
    ).eq("id", user.id).limit(1).execute().data
    if not rows:
        raise HTTPException(403, "Profile not provisioned")
    return {
        **rows[0],
        "role": user.role,
        "application_role": user.role,
        "institution_id": user.institution_id,
        "account_status": user.account_status,
    }


@app.get("/api/courses")
def courses(user: Principal = Depends(active_user)):
    return user_client(user.token).table("courses").select("*").order("created_at", desc=True).execute().data


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
    return user_client(user.token).table("classes").select("*").order("created_at", desc=True).execute().data


@app.get("/api/students")
def students(user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    return user_client(user.token).table("students").select("*").execute().data


@app.get("/api/teachers")
def teachers(user: Principal = Depends(active_user)):
    return user_client(user.token).table("teachers").select("*").execute().data


@app.get("/api/attendance")
def attendance(user: Principal = Depends(active_user)):
    return user_client(user.token).table("attendance").select("*").order("occurred_at", desc=True).limit(200).execute().data


@app.post("/api/attendance", status_code=201)
def record_attendance(data: AttendanceInput, user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    row = {**data.model_dump(mode="json"), "recorded_by": user.id}
    return user_client(user.token).table("attendance").insert(row).execute().data[0]


@app.put("/api/attendance/{attendance_id}")
def update_attendance(attendance_id: UUID, data: AttendanceUpdate,
                      user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    rows = user_client(user.token).table("attendance").update(data.model_dump()).eq("id", str(attendance_id)).execute().data
    if not rows:
        raise HTTPException(404, "Attendance record not found")
    return rows[0]


@app.get("/api/assignments")
def assignments(user: Principal = Depends(active_user)):
    return user_client(user.token).table("assignments").select("*").limit(200).execute().data


@app.get("/api/exams")
def exams(user: Principal = Depends(active_user)):
    return user_client(user.token).table("exams").select("id,class_id,title,opens_at,closes_at").limit(200).execute().data
