from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import get_settings
from .database import user_client
from .dependencies import Principal, current_user, require_roles

settings = get_settings()
app = FastAPI(title="Sisu Academy API")
origins = ["http://127.0.0.1:5178", "http://localhost:5178", settings.frontend_url]
app.add_middleware(CORSMiddleware, allow_origins=list(set(origins)), allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])


class CourseInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    institution_id: str


class AttendanceInput(BaseModel):
    class_id: str
    student_id: str
    occurred_at: str
    status: str = Field(pattern="^(Present|Absent|Late|Excused)$")


@app.get("/api/health")
def health():
    return {"status": "healthy", "backend": "FastAPI", "database": "Supabase PostgreSQL"}


@app.get("/api/me")
def me(user: Principal = Depends(current_user)):
    rows = user_client(user.token).table("profiles").select("*").eq("id", user.id).limit(1).execute().data
    return rows[0]


@app.get("/api/courses")
def courses(user: Principal = Depends(current_user)):
    return user_client(user.token).table("courses").select("*").order("created_at", desc=True).execute().data


@app.get("/api/courses/{course_id}")
def course(course_id: str, user: Principal = Depends(current_user)):
    rows = user_client(user.token).table("courses").select("*").eq("id", course_id).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "Course not found")
    return rows[0]


@app.post("/api/courses", status_code=201)
def create_course(data: CourseInput, user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    if user.role != "super_admin" and user.institution_id != data.institution_id:
        raise HTTPException(403, "Wrong institution")
    return user_client(user.token).table("courses").insert({**data.model_dump(), "created_by": user.id}).execute().data[0]


@app.get("/api/classes")
def classes(user: Principal = Depends(current_user)):
    return user_client(user.token).table("classes").select("*").order("created_at", desc=True).execute().data


@app.get("/api/students")
def students(user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    return user_client(user.token).table("students").select("*").execute().data


@app.get("/api/teachers")
def teachers(user: Principal = Depends(current_user)):
    return user_client(user.token).table("teachers").select("*").execute().data


@app.get("/api/attendance")
def attendance(user: Principal = Depends(current_user)):
    return user_client(user.token).table("attendance").select("*").order("occurred_at", desc=True).limit(200).execute().data


@app.post("/api/attendance", status_code=201)
def record_attendance(data: AttendanceInput, user: Principal = Depends(require_roles("teacher", "institute_admin", "super_admin"))):
    row = {**data.model_dump(), "recorded_by": user.id}
    return user_client(user.token).table("attendance").insert(row).execute().data[0]


@app.get("/api/assignments")
def assignments(user: Principal = Depends(current_user)):
    return user_client(user.token).table("assignments").select("*").limit(200).execute().data


@app.get("/api/exams")
def exams(user: Principal = Depends(current_user)):
    return user_client(user.token).table("exams").select("id,class_id,title,opens_at,closes_at").limit(200).execute().data
