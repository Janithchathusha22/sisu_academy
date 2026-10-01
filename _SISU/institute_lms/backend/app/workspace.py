"""Connected workspace routes. Every query uses the user's JWT and database RLS."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, AwareDatetime, model_validator
from .database import user_client
from .dependencies import Principal, active_user, require_roles

router = APIRouter(prefix='/api', tags=['workspace'])

class ClassInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    subject: str = Field(default='', max_length=120)
    institution_id: UUID
    course_id: UUID | None = None
    teacher_id: UUID | None = None

class EnrollmentInput(BaseModel):
    institution_id: UUID
    class_id: UUID
    student_id: UUID

class ScheduleInput(BaseModel):
    class_id: UUID
    title: str = Field(min_length=1, max_length=120)
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    @model_validator(mode='after')
    def time_order(self):
        if self.ends_at <= self.starts_at:
            raise ValueError('End time must be after start time')
        return self

@router.post('/classes', status_code=201)
def create_class(data: ClassInput, user: Principal=Depends(require_roles('super_admin','institute_admin'))):
    if user.role != 'super_admin' and str(data.institution_id) != user.institution_id:
        raise HTTPException(403, 'Wrong institution')
    return user_client(user.token).table('classes').insert(data.model_dump(mode='json')).execute().data[0]

@router.post('/enrollments', status_code=201)
def enroll(data: EnrollmentInput, user: Principal=Depends(require_roles('super_admin','institute_admin'))):
    if user.role != 'super_admin' and str(data.institution_id) != user.institution_id:
        raise HTTPException(403, 'Wrong institution')
    return user_client(user.token).table('enrollments').insert(data.model_dump(mode='json')).execute().data[0]

@router.post('/schedule', status_code=201)
def schedule(data: ScheduleInput, user: Principal=Depends(require_roles('super_admin','institute_admin'))):
    return user_client(user.token).table('class_sessions').insert(data.model_dump(mode='json')).execute().data[0]

# Explicit allowlist; do not expose arbitrary tables or return exam questions.
READ_TABLES = {'schedule': ('class_sessions','starts_at'), 'enrollments': ('enrollments','created_at'),
               'materials': ('materials','created_at'), 'results': ('exam_results','created_at'),
               'payments': ('payments','created_at'), 'notifications': ('notifications','created_at')}

def read_table(table, order):
    def endpoint(user: Principal=Depends(active_user)):
        return user_client(user.token).table(table).select('*').order(order, desc=True).limit(200).execute().data
    return endpoint

for path, (table, order) in READ_TABLES.items():
    router.add_api_route('/'+path, read_table(table, order), methods=['GET'])
