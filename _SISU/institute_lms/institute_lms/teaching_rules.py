"""Ownership, delegated teaching rights and safe meeting URLs (no network requests)."""
from datetime import date
from urllib.parse import urlparse
import re
from .domain import safe_url

def capabilities(room,member,affiliated=True):
    personal=room.get('owner_type')=='Teacher'
    owner=member.get('role')=='Teacher' and personal and room.get('owner_user')==member.get('user')
    institute_admin=member.get('role')=='Admin' and not personal
    assigned=member.get('role')=='Teacher' and room.get('teacher')==member.get('name') and room.get('teacher_assignment_active')!=0 and (personal or affiliated)
    manage=owner or institute_admin or (assigned and room.get('teacher_access')=='Full control')
    return {'teach':bool(owner or institute_admin or assigned),'edit':bool(manage),'delete':bool(manage),
            'assign':bool(institute_admin),'fees':bool(manage),'owner':bool(owner or institute_admin)}

def meeting_link(provider,url):
    if provider not in ('YouTube','Zoom','Google Meet'):raise ValueError('Choose YouTube, Zoom or Google Meet')
    if not url:return ''
    safe_url(url,False);p=urlparse(url);host=(p.hostname or '').lower()
    if p.port not in (None,443):raise ValueError('Use the standard HTTPS meeting link')
    allowed={'YouTube':host in ('youtube.com','www.youtube.com','youtu.be','m.youtube.com'),
        'Zoom':host in ('zoom.us','zoom.com') or host.endswith('.zoom.us') or host.endswith('.zoom.com'),
        'Google Meet':host=='meet.google.com'}[provider]
    if not allowed:raise ValueError('The meeting URL must match the selected provider')
    if len(url)>2048:raise ValueError('Meeting URL is too long')
    return url

def billing_month(value):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',str(value or '')):raise ValueError('Use a billing month in YYYY-MM format')
    date.fromisoformat(value+'-01')
    return value

def module_plan(rows):
    if not isinstance(rows,list) or not 1<=len(rows)<=60:raise ValueError('Add between 1 and 60 modules')
    names=set();total=0
    for row in rows:
        if not row.get('classroom') or row['classroom'] in names:raise ValueError('Each module needs a different classroom')
        names.add(row['classroom']);weeks=int(row.get('duration_weeks',2))
        if not 1<=weeks<=52:raise ValueError('Module duration must be 1–52 weeks')
        total+=weeks
    return total
