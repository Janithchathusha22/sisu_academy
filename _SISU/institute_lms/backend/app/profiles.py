from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .database import user_client
from .dependencies import Principal, current_user, require_roles

router=APIRouter(prefix='/api', tags=['profiles'])

class ProfileName(BaseModel):
    full_name: str=Field(min_length=1,max_length=120)

class Review(BaseModel):
    decision: Literal['approved','rejected']
    institution_id: UUID | None=None

class Assignment(BaseModel):
    institution_id: UUID

class InstitutionInput(BaseModel):
    title: str=Field(min_length=1,max_length=120)
    code: str=Field(min_length=2,max_length=40,pattern=r'^[a-zA-Z0-9_-]+$')

@router.post('/institutions', status_code=201)
def create_institution(data: InstitutionInput, user: Principal=Depends(require_roles('super_admin'))):
    return user_client(user.token).table('institutions').insert(data.model_dump()).execute().data[0]

@router.put('/me')
def update_me(data: ProfileName, user: Principal=Depends(current_user)):
    return user_client(user.token).table('profiles').update(data.model_dump()).eq('id',user.id).execute().data[0]

@router.get('/applications')
def applications(user: Principal=Depends(require_roles('super_admin'))):
    return user_client(user.token).table('account_applications').select('*').eq('status','pending').limit(100).execute().data

@router.post('/applications/{application_id}/review')
def review(application_id: UUID, data: Review, user: Principal=Depends(require_roles('super_admin'))):
    if data.decision=='approved' and not data.institution_id:
        raise HTTPException(422,'Select an institution before approval')
    user_client(user.token).rpc('review_application',{'application':str(application_id),'decision':data.decision,
                              'institution':str(data.institution_id) if data.institution_id else None}).execute()
    return {'status':data.decision}

@router.post('/profiles/{profile_id}/institution')
def assign_student(profile_id: UUID, data: Assignment, user: Principal=Depends(require_roles('super_admin'))):
    user_client(user.token).rpc('assign_student',{'student_profile':str(profile_id),'institution':str(data.institution_id)}).execute()
    return {'status':'assigned'}

@router.get('/institutions')
def institutions(user: Principal=Depends(require_roles('super_admin','institute_admin'))):
    return user_client(user.token).table('institutions').select('id,title,code').execute().data

@router.get('/profiles/unassigned')
def unassigned(user: Principal=Depends(require_roles('super_admin'))):
    return user_client(user.token).table('profiles').select('id,full_name,email').eq('role','student').is_('institution_id','null').limit(100).execute().data
