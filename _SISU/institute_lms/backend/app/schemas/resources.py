from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InstitutionCreate(RequestModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9]{1,11}$")
    title: str = Field(min_length=1, max_length=120)
    language: Literal["en", "si", "ta"] = "en"
    logo_url: str | None = Field(default=None, max_length=500)
    accent: str = Field(default="#7563e6", pattern=r"^#[0-9A-Fa-f]{6}$")


class InstitutionUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    language: Literal["en", "si", "ta"] | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    accent: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    active: bool | None = None


class ProfileCreate(RequestModel):
    user_id: UUID | None = None
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-z][a-z0-9_]{2,29}$")
    full_name: str = Field(min_length=1, max_length=120)
    profile_kind: Literal["student", "teacher", "institute"]
    language: str = Field(default="en", min_length=2, max_length=20)
    country: str = Field(default="", max_length=80)


class ProfileUpdate(RequestModel):
    username: str | None = Field(default=None, min_length=3, max_length=30, pattern=r"^[a-z][a-z0-9_]{2,29}$")
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    language: str | None = Field(default=None, min_length=2, max_length=20)
    country: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=1000)
    tagline: str | None = Field(default=None, max_length=160)
    profile_image_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)


class MembershipCreate(RequestModel):
    institution_id: UUID
    user_id: UUID
    role: Literal["institute_admin", "teacher", "student"]
    member_code: str | None = Field(default=None, max_length=40)


class MembershipUpdate(RequestModel):
    status: Literal["pending", "active", "suspended", "left"] | None = None
    role: Literal["institute_admin", "teacher", "student"] | None = None
    member_code: str | None = Field(default=None, max_length=40)


class CourseCreate(RequestModel):
    institution_id: UUID
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    medium: str | None = Field(default=None, max_length=80)
    published: bool = False
    active: bool = True


class CourseUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    medium: str | None = Field(default=None, max_length=80)
    published: bool | None = None
    active: bool | None = None


class ModuleCreate(RequestModel):
    course_id: UUID
    title: str = Field(min_length=1, max_length=160)
    position: int = Field(default=0, ge=0, le=10000)


class ModuleUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    position: int | None = Field(default=None, ge=0, le=10000)


class LessonCreate(RequestModel):
    module_id: UUID
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    video_url: str | None = Field(default=None, max_length=2048)
    storage_path: str | None = Field(default=None, max_length=1000)
    position: int = Field(default=0, ge=0, le=10000)
    published: bool = False


class LessonUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    video_url: str | None = Field(default=None, max_length=2048)
    storage_path: str | None = Field(default=None, max_length=1000)
    position: int | None = Field(default=None, ge=0, le=10000)
    published: bool | None = None


class ClassCreate(RequestModel):
    institution_id: UUID
    course_id: UUID | None = None
    teacher_membership_id: UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    subject: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=4000)
    fee_minor: int = Field(default=0, ge=0, le=2_000_000_000)
    currency: str = Field(default="LKR", min_length=3, max_length=3)
    fee_mode: Literal["paid", "free"] = "paid"
    billing_type: Literal["one_time", "monthly", "programme_module"] = "one_time"
    published: bool = False
    active: bool = True


class ClassUpdate(RequestModel):
    course_id: UUID | None = None
    teacher_membership_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    subject: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    fee_minor: int | None = Field(default=None, ge=0, le=2_000_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    fee_mode: Literal["paid", "free"] | None = None
    billing_type: Literal["one_time", "monthly", "programme_module"] | None = None
    published: bool | None = None
    active: bool | None = None


class SessionCreate(RequestModel):
    class_id: UUID
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    starts_at: datetime
    ends_at: datetime
    mode: Literal["physical", "online"] = "online"
    status: Literal["scheduled", "live", "completed", "cancelled"] = "scheduled"
    location: str | None = Field(default=None, max_length=240)
    meeting_url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class SessionUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    mode: Literal["physical", "online"] | None = None
    status: Literal["scheduled", "live", "completed", "cancelled"] | None = None
    location: str | None = Field(default=None, max_length=240)
    meeting_url: str | None = Field(default=None, max_length=2048)


class EnrollmentCreate(RequestModel):
    class_id: UUID
    student_membership_id: UUID
    fee_minor: int = Field(default=0, ge=0, le=2_000_000_000)
    currency: str = Field(default="LKR", min_length=3, max_length=3)


class EnrollmentUpdate(RequestModel):
    status: Literal["pending", "active", "completed", "cancelled"] | None = None
    access_override: Literal["automatic", "open", "closed"] | None = None
    grace_until: date | None = None


class AttendanceCreate(RequestModel):
    class_session_id: UUID
    student_membership_id: UUID
    status: Literal["present", "absent", "excused", "late"]
    channel: Literal["physical", "online"] = "physical"
    note: str = Field(default="", max_length=500)
    recorded_at: datetime | None = None


class AttendanceUpdate(RequestModel):
    status: Literal["present", "absent", "excused", "late"] | None = None
    note: str | None = Field(default=None, max_length=500)


class AssignmentCreate(RequestModel):
    class_id: UUID
    title: str = Field(min_length=1, max_length=160)
    instructions: str = Field(default="", max_length=10000)
    due_at: datetime | None = None
    max_score: int = Field(default=100, ge=1, le=10000)
    published: bool = False


class AssignmentUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    instructions: str | None = Field(default=None, max_length=10000)
    due_at: datetime | None = None
    max_score: int | None = Field(default=None, ge=1, le=10000)
    published: bool | None = None


class SubmissionCreate(RequestModel):
    assignment_id: UUID
    body: str = Field(default="", max_length=20000)
    storage_path: str | None = Field(default=None, max_length=1000)


class SubmissionUpdate(RequestModel):
    body: str | None = Field(default=None, max_length=20000)
    storage_path: str | None = Field(default=None, max_length=1000)
    status: Literal["draft", "submitted", "graded"] | None = None
    score: int | None = Field(default=None, ge=0, le=10000)
    feedback: str | None = Field(default=None, max_length=4000)


class ExamCreate(RequestModel):
    class_id: UUID
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    questions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_score: int = Field(default=100, ge=1, le=10000)
    published: bool = False


class ExamUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    questions: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_score: int | None = Field(default=None, ge=1, le=10000)
    published: bool | None = None


class ExamResultCreate(RequestModel):
    exam_id: UUID
    student_membership_id: UUID
    score: int = Field(ge=0, le=10000)
    feedback: str = Field(default="", max_length=4000)


class ExamResultUpdate(RequestModel):
    score: int | None = Field(default=None, ge=0, le=10000)
    feedback: str | None = Field(default=None, max_length=4000)
    published_at: datetime | None = None


class InvoiceCreate(RequestModel):
    enrollment_id: UUID
    amount_minor: int = Field(ge=0, le=2_000_000_000)
    currency: str = Field(default="LKR", min_length=3, max_length=3)
    due_date: date
    installment: int = Field(default=1, ge=1, le=120)


class InvoiceUpdate(RequestModel):
    due_date: date | None = None
    status: Literal["unpaid", "paid", "overdue", "void"] | None = None


class PaymentCreate(RequestModel):
    invoice_id: UUID
    provider: str = Field(default="manual", min_length=1, max_length=40)
    provider_reference: str | None = Field(default=None, max_length=160)


class PaymentUpdate(RequestModel):
    status: Literal["pending", "succeeded", "failed", "refunded"] | None = None
    provider_reference: str | None = Field(default=None, max_length=160)
    paid_at: datetime | None = None


class NotificationCreate(RequestModel):
    institution_id: UUID
    recipient_user_id: UUID
    title: str = Field(default="", max_length=160)
    body: str = Field(min_length=1, max_length=4000)
    channel: Literal["in_app", "email", "whatsapp"] = "in_app"


class NotificationUpdate(RequestModel):
    read_at: datetime | None = None


class NewsCreate(RequestModel):
    institution_id: UUID
    headline: str = Field(min_length=1, max_length=160)
    body: str = Field(default="", max_length=4000)
    cta_label: str | None = Field(default=None, max_length=40)
    cta_url: str | None = Field(default=None, max_length=2048)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    published: bool = False


class NewsUpdate(RequestModel):
    headline: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=4000)
    cta_label: str | None = Field(default=None, max_length=40)
    cta_url: str | None = Field(default=None, max_length=2048)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    published: bool | None = None
