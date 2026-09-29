"""Opt-in Google Calendar sync to an app-created secondary calendar only."""
import base64
import hashlib
import secrets
from urllib.parse import urlencode, quote
import requests
import frappe
from frappe.utils import get_url, now_datetime
from .api import identity, require_role
from .calendar_contract import event_id, event_payload

SCOPE='https://www.googleapis.com/auth/calendar.app.created'
BASE='https://www.googleapis.com/calendar/v3'


def config():
    client=frappe.conf.get('il_calendar_client_id');secret=frappe.conf.get('il_calendar_client_secret')
    if not client or not secret or not get_url().startswith('https://'):
        frappe.throw('Calendar connection needs Google OAuth configuration and an HTTPS site')
    return client,secret,get_url('/api/method/institute_lms.calendar_sync.callback')


def request(method,url,**kwargs):
    try:
        result=requests.request(method,url,timeout=(5,20),allow_redirects=False,**kwargs)
        return result
    except requests.RequestException:
        raise ValueError('Calendar request could not be confirmed') from None


@frappe.whitelist(methods=['POST'])
def connect():
    inst,member=identity();require_role(member,'Student')
    if not member.get('contact_email_verified'):frappe.throw('Verify your contact email first')
    existing=frappe.db.get_value('IL Calendar Connection',{'member':member.name},'status')
    if existing=='Review':frappe.throw('An earlier calendar creation needs operator reconciliation before reconnecting')
    client,_,redirect=config();state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    frappe.cache.set_value('il_calendar_oauth:'+state,{'user':frappe.session.user,'member':member.name,'institute':inst.name,'email':member.contact_email,'verifier':verifier},expires_in_sec=600)
    return {'url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client,'redirect_uri':redirect,'response_type':'code','scope':'openid email '+SCOPE,'access_type':'offline','prompt':'consent','state':state,'code_challenge':challenge,'code_challenge_method':'S256','login_hint':member.contact_email})}


@frappe.whitelist(methods=['GET'])
def callback(state=None,code=None,error=None):
    if not isinstance(state,str) or len(state)>100:frappe.throw('Invalid calendar session',frappe.PermissionError)
    key='il_calendar_oauth:'+state
    with frappe.cache.lock(key,timeout=5):
        context=frappe.cache.get_value(key);frappe.cache.delete_value(key)
    inst,member=identity();require_role(member,'Student')
    if not context or context['user']!=frappe.session.user or context['member']!=member.name or context['institute']!=inst.name or context['email']!=member.get('contact_email') or not member.get('contact_email_verified'):
        frappe.throw('Calendar session expired. Start the connection again',frappe.PermissionError)
    if error or not code:frappe.throw('Calendar access was not granted')
    client,secret,redirect=config()
    try:
        response=request('POST','https://oauth2.googleapis.com/token',data={'client_id':client,'client_secret':secret,'redirect_uri':redirect,'grant_type':'authorization_code','code':code,'code_verifier':context['verifier']})
        token=response.json()
        if not response.ok or not token.get('refresh_token') or SCOPE not in token.get('scope','').split():raise ValueError('Missing authorization')
        user=request('GET','https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+token['access_token']})
        info=user.json()
        if not user.ok or info.get('email_verified') is not True or str(info.get('email','')).lower()!=context['email']:raise ValueError('Email mismatch')
    except (ValueError,KeyError,TypeError):
        frappe.throw('Connect the Google account matching your verified email and grant the requested access')
    name=frappe.db.get_value('IL Calendar Connection',{'member':member.name},'name')
    with frappe.cache.lock('il_calendar_member:'+member.name,timeout=35):
        doc=frappe.get_doc('IL Calendar Connection',name) if name else frappe.new_doc('IL Calendar Connection')
        if doc.status=='Review':frappe.throw('The previous calendar creation needs operator review')
        if doc.google_email and doc.google_email!=context['email']:doc.calendar_id=None
        doc.update({'institute':inst.name,'member':member.name,'google_email':context['email'],'refresh_token':token['refresh_token'],'status':'Review'})
        doc.save(ignore_permissions=True);frappe.db.commit()
        # Creation is not blindly retried after timeout; operators reconcile the Review record.
        if not doc.calendar_id:
            try:
                response=request('POST',BASE+'/calendars',headers={'Authorization':'Bearer '+token['access_token']},json={'summary':f'Sisu · {inst.title}'[:120],'description':'Class schedules created by Sisu. Disconnecting stops future updates.','timeZone':timezone()})
                if not response.ok:raise ValueError('Calendar creation failed')
                doc.calendar_id=response.json()['id']
            except (ValueError,KeyError):frappe.throw('Calendar creation needs review. Contact your institute before reconnecting')
        doc.status='Connected';doc.save(ignore_permissions=True)
        queue_member(member.name)
        # OAuth callback is GET: Frappe's POST auto-commit does not apply.
        frappe.db.commit()
    frappe.local.response.update({'type':'redirect','location':'/campus?calendar=connected#settings'})


def timezone():return frappe.db.get_single_value('System Settings','time_zone') or 'Asia/Colombo'


def disconnect_member(member):
    name=frappe.db.get_value('IL Calendar Connection',{'member':member},'name')
    if name:
        from frappe.utils.password import remove_encrypted_password
        remove_encrypted_password('IL Calendar Connection',name,'refresh_token')
        frappe.db.set_value('IL Calendar Connection',name,'status','Disconnected')
        # Existing Google calendar entries remain the student's own copy.


@frappe.whitelist(methods=['POST'])
def disconnect():
    _,member=identity();require_role(member,'Student');disconnect_member(member.name)
    return {'disconnected':True,'existing_events_retained':True}


def queue_job(member,session,institute):
    connection=frappe.db.get_value('IL Calendar Connection',{'member':member,'status':'Connected'},'name')
    if not connection:return
    name=event_id(institute,member,session)
    with frappe.cache.lock('il_calendar_job:'+name,timeout=10):
        if frappe.db.exists('IL Calendar Job',name):
            frappe.db.set_value('IL Calendar Job',name,{'status':'Pending','attempts':0,'next_attempt':now_datetime()})
        else:
            frappe.get_doc({'doctype':'IL Calendar Job','name':name,'event_key':name,'institute':institute,'member':member,'session':session,'connection':connection,'status':'Pending','next_attempt':now_datetime()}).insert(ignore_permissions=True)


def queue_member(member):
    m=frappe.get_doc('IL Member',member)
    rooms=frappe.get_all('IL Enrollment',filters={'student':member,'active':1},pluck='classroom',limit_page_length=0)
    sessions=frappe.get_all('IL Session',filters={'classroom':['in',rooms or ['__none__']],'ends_at':['>=',now_datetime()]},pluck='name',limit_page_length=0)
    # Include existing jobs so removed enrollments are deleted from the calendar.
    sessions+=frappe.get_all('IL Calendar Job',filters={'member':member},pluck='session',limit_page_length=0)
    for session in set(sessions):queue_job(member,session,m.institute)


def session_changed(doc,method=None):
    for member in frappe.get_all('IL Enrollment',filters={'classroom':doc.classroom,'active':1},pluck='student',limit_page_length=0):queue_job(member,doc.name,doc.institute)


def enrollment_changed(doc,method=None):queue_member(doc.student)


def dispatch():
    if not frappe.conf.get('il_calendar_client_id'):return
    with frappe.cache.lock('il_calendar_dispatch',timeout=900,blocking_timeout=1):
        jobs=frappe.get_all('IL Calendar Job',filters={'status':'Pending','next_attempt':['<=',now_datetime()]},pluck='name',limit_page_length=20,order_by='modified asc')
        for name in jobs:
            frappe.db.sql('SELECT name FROM `tabIL Calendar Job` WHERE name=%s FOR UPDATE',(name,))
            job=frappe.get_doc('IL Calendar Job',name);connection=frappe.get_doc('IL Calendar Connection',job.connection);member=frappe.get_doc('IL Member',job.member)
            if connection.status!='Connected' or not member.active or not member.contact_email_verified or member.contact_email!=connection.google_email:
                job.db_set('status','Skipped');frappe.db.commit();continue
            try:
                client,secret,_=config()
                response=request('POST','https://oauth2.googleapis.com/token',data={'client_id':client,'client_secret':secret,'refresh_token':connection.get_password('refresh_token'),'grant_type':'refresh_token'})
                if not response.ok:raise ValueError('Reconnect Google Calendar')
                headers={'Authorization':'Bearer '+response.json()['access_token']}
                session=frappe.get_doc('IL Session',job.session);room=frappe.get_doc('IL Classroom',session.classroom)
                active=bool(room.active and frappe.db.exists('IL Enrollment',{'student':member.name,'classroom':room.name,'active':1}))
                base=BASE+'/calendars/'+quote(connection.calendar_id,safe='')+'/events';url=base+'/'+job.name
                if session.status=='Cancelled' or not active:
                    result=request('DELETE',url,headers=headers,params={'sendUpdates':'none'})
                    if result.status_code not in (200,204,404,410):raise ValueError('Calendar removal failed')
                else:
                    body=event_payload(session.as_dict(),room.title,timezone(),get_url('/campus#schedule'));body['id']=job.name
                    result=request('POST',base,headers=headers,params={'sendUpdates':'none'},json=body)
                    if result.status_code==409:
                        body.pop('id');result=request('PATCH',url,headers=headers,params={'sendUpdates':'none'},json=body)
                    if not result.ok:raise ValueError('Calendar update failed')
                job.status='Synced';job.last_error='';connection.last_synced=now_datetime();connection.save(ignore_permissions=True)
            except (ValueError,KeyError,requests.RequestException):
                from datetime import timedelta
                job.attempts=(job.attempts or 0)+1;job.status='Review' if job.attempts>=5 else 'Pending';job.next_attempt=now_datetime()+timedelta(minutes=2**job.attempts);job.last_error='Calendar update failed. Check connection, access and provider status.'
            job.save(ignore_permissions=True);frappe.db.commit()
