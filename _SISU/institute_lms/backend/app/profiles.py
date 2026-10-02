from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError
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
    return user_client(user.token).table('profiles').update(data.model_dump()).eq('id',user.id).select('id,full_name').execute().data[0]

@router.get('/applications')
def applications(user: Principal=Depends(require_roles('super_admin'))):
    return user_client(user.token).table('account_applications').select('*').eq('status','pending').limit(100).execute().data

@router.post('/applications/{application_id}/review')
def review(application_id: UUID, data: Review, user: Principal=Depends(require_roles('super_admin'))):
    client = user_client(user.token)
    rows = (
        client.table('account_applications')
        .select('id,account_type,status')
        .eq('id', str(application_id))
        .limit(1)
        .execute()
        .data
    )
    if not rows or rows[0]['status'] != 'pending':
        raise HTTPException(409, 'This application is no longer pending.')
    application_type = rows[0]['account_type']
    if data.decision == 'approved' and application_type != 'student' and not data.institution_id:
        raise HTTPException(422,'Select an institution before approval')
    institution_id = (
        str(data.institution_id)
        if data.decision == 'approved' and application_type != 'student' and data.institution_id
        else None
    )
    try:
        client.rpc('review_application', {
            'application': str(application_id),
            'decision': data.decision,
            'institution': institution_id,
        }).execute()
    except APIError as exc:
        if exc.code == 'P0001' and 'application not pending' in str(exc.message).lower():
            raise HTTPException(409, 'This application is no longer pending.') from exc
        raise
    return {'status':data.decision}

@router.post('/profiles/{profile_id}/institution')
def assign_student(profile_id: UUID, data: Assignment, user: Principal=Depends(require_roles('super_admin'))):
    client = user_client(user.token)
    student = (
        client.table('profiles')
        .select('id')
        .eq('id', str(profile_id))
        .eq('profile_kind', 'student')
        .eq('status', 'verified')
        .limit(1)
        .execute()
        .data
    )
    if not student:
        raise HTTPException(422, 'A verified student is required.')
    institution = (
        client.table('institutions')
        .select('id')
        .eq('id', str(data.institution_id))
        .limit(1)
        .execute()
        .data
    )
    if not institution:
        raise HTTPException(422, 'The selected institution does not exist.')
    memberships = (
        client.table('institution_memberships')
        .select('institution_id')
        .eq('user_id', str(profile_id))
        .eq('role', 'student')
        .in_('status', ['pending', 'active'])
        .execute()
        .data
    )
    if any(row['institution_id'] != str(data.institution_id) for row in memberships):
        raise HTTPException(409, 'Student is already assigned to another institution.')
    try:
        client.rpc('assign_student', {
            'student_profile': str(profile_id),
            'institution': str(data.institution_id),
        }).execute()
    except APIError as exc:
        if exc.code == 'P0001' and 'already assigned' in str(exc.message).lower():
            raise HTTPException(409, 'Student is already assigned to another institution.') from exc
        raise
    return {'status':'assigned'}

@router.get('/institutions')
def institutions(user: Principal=Depends(require_roles('super_admin','institute_admin'))):
    return user_client(user.token).table('institutions').select('id,title,code').execute().data

@router.get('/profiles/unassigned')
def unassigned(user: Principal=Depends(require_roles('super_admin'))):
    client = user_client(user.token)
    page_size = 100
    profiles = []
    offset = 0
    while True:
        page = (
            client.table('profiles')
            .select('id,full_name,email')
            .eq('profile_kind', 'student')
            .eq('status', 'verified')
            .range(offset, offset + page_size - 1)
            .execute()
            .data or []
        )
        profiles.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    assigned_ids = set()
    for offset in range(0, len(profiles), page_size):
        profile_ids = [profile['id'] for profile in profiles[offset:offset + page_size]]
        assigned = (
            client.table('institution_memberships')
            .select('user_id')
            .in_('user_id', profile_ids)
            .eq('role', 'student')
            .in_('status', ['pending', 'active'])
            .execute()
            .data or []
        )
        assigned_ids.update(row['user_id'] for row in assigned)
    return [profile for profile in profiles if profile['id'] not in assigned_ids]
