"""Bounded email verification for pending registrations; no automatic role grant."""
import hashlib
import hmac
import json
import secrets
import time
import frappe
from frappe.utils import get_url
from .registration_contract import registration_details

def ready():
    if not frappe.conf.get('il_registration_enabled') or not get_url().startswith('https://'):
        frappe.throw('Registration is not enabled on this site')
    if not frappe.conf.get('encryption_key') or not frappe.db.exists('Email Account', {'enable_outgoing':1}):
        frappe.throw('Email verification is not configured')

def digest(challenge, code):
    return hmac.new(str(frappe.conf.encryption_key).encode(),(challenge+':'+code).encode(),hashlib.sha256).hexdigest()

def limit(identifier):
    now=int(time.time()); key='il_signup_limit:'+hashlib.sha256(identifier.encode()).hexdigest()+':'+str(now//3600)
    with frappe.cache.lock(key, timeout=10):
        count=frappe.cache.get_value(key) or 0
        if count>=5: frappe.throw('Too many verification requests. Please try later')
        frappe.cache.set_value(key,count+1,expires_in_sec=7200)

@frappe.whitelist(allow_guest=True, methods=['POST'])
def request_code(data):
    ready()
    try:
        if isinstance(data,str):
            if len(data)>5000: raise ValueError('Registration is too large')
            data=json.loads(data)
        if data.get('kind')=='Student':frappe.throw('Students register with Google')
        if not isinstance(data,dict):raise ValueError('Invalid registration')
        if data.get('kind')!='Super Admin':
            from .portal_policy import public
            policy=public()
            if not policy['provider_applications_enabled'] or data.get('privacy_policy_version')!=policy['privacy_policy_version'] or data.get('privacy_accepted') is not True:frappe.throw('Read and accept the published privacy policy before applying')
            from frappe.utils import now_datetime
            data.update(privacy_policy_url=policy['privacy_policy_url'],consented_at=str(now_datetime()))
        details=registration_details(data,frappe.conf.get('il_owner_email'))
        if details['kind']!='Super Admin':
            import re
            if not re.fullmatch(r'[a-z][a-z0-9_]{2,29}',details['username']):frappe.throw('Choose a username of 3–30 lowercase letters, digits or underscores')
            if not re.fullmatch(r'\+[1-9][0-9]{7,14}',details['phone']):frappe.throw('Use a phone number with country code')
            if frappe.db.exists('IL Public Profile',{'username':details['username']}):frappe.throw('This username is already in use')
    except PermissionError as exc: frappe.throw(str(exc),frappe.PermissionError)
    except (ValueError,TypeError) as exc: frappe.throw(str(exc))
    limit('ip:'+str(frappe.local.request_ip));limit('email:'+details['email'])
    challenge=secrets.token_urlsafe(32);code=f'{secrets.randbelow(1000000):06d}'
    frappe.cache.set_value('il_signup:'+challenge,{'details':details,'digest':digest(challenge,code),'created':int(time.time()),'attempts':0},expires_in_sec=600)
    frappe.sendmail(recipients=[details['email']],subject='Your Sisu registration code',message=f'<p>Your code is <strong>{code}</strong>.</p><p>It expires in ten minutes. If you did not request it, ignore this email.</p>',delayed=True)
    return {'challenge':challenge,'expires_in_seconds':600}

@frappe.whitelist(allow_guest=True, methods=['POST'])
def verify_code(challenge, code):
    ready()
    if not isinstance(challenge,str) or len(challenge)>80 or not isinstance(code,str) or len(code)!=6 or not code.isascii() or not code.isdigit(): frappe.throw('Invalid verification request')
    key='il_signup:'+challenge
    with frappe.cache.lock(key,timeout=10):
        pending=frappe.cache.get_value(key)
        if not pending or time.time()-pending['created']>=600 or pending['attempts']>=5: frappe.throw('Code expired. Request another')
        pending['attempts']+=1
        frappe.cache.set_value(key,pending,expires_in_sec=max(1,600-int(time.time()-pending['created'])))
        if not hmac.compare_digest(pending['digest'],digest(challenge,code)): frappe.throw('Code did not match')
        # Recheck the allowlist in case the operator changed it after issuance.
        details=registration_details(pending['details'],frappe.conf.get('il_owner_email'))
        if details['kind']!='Super Admin':
            from .portal_policy import public
            policy=public()
            if not policy['provider_applications_enabled'] or details['privacy_policy_version']!=policy['privacy_policy_version'] or details['privacy_policy_url']!=policy['privacy_policy_url']:
                frappe.throw('The signup policy changed. Please review it and start a new application.')
        doc=frappe.get_doc({'doctype':'IL Registration Request','email':details['email'],'account_type':details['kind'],'status':'Pending review','details':json.dumps(details),'email_verified':1}).insert(ignore_permissions=True)
        email=frappe.conf.get('il_owner_email')
        if email and frappe.db.exists('User',email):
            frappe.get_doc({'doctype':'Notification Log','subject':'Provider application ready for review','for_user':email,'type':'Alert','document_type':'IL Registration Request','document_name':doc.name}).insert(ignore_permissions=True)
        frappe.cache.delete_value(key)
    return {'verified':True,'status':'Pending review','reference':doc.name}

def require_owner():
    """For future owner services: configuration and authenticated identity both required."""
    allowed=str(frappe.conf.get('il_owner_email') or '').strip().lower()
    if not allowed or frappe.session.user=='Guest' or frappe.session.user.lower()!=allowed:
        frappe.throw('Owner access required',frappe.PermissionError)
    if not frappe.db.get_value('User',frappe.session.user,'enabled'):
        frappe.throw('Owner access required',frappe.PermissionError)
    # Enrollment approval is not authentication. Normal Frappe login/2FA still applies.
    if not frappe.conf.get('il_owner_provisioned'):
        frappe.throw('Owner setup must be completed by the site operator',frappe.PermissionError)

@frappe.whitelist()
def applications(page=0):
    require_owner()
    return frappe.get_all('IL Registration Request',filters={'status':'Pending review'},fields=['name','email','account_type','details','creation','email_verified'],limit_start=max(0,min(int(page),10000))*30,limit_page_length=30,order_by='creation asc')

@frappe.whitelist(methods=['POST'])
def review_application(name,decision,reason):
    require_owner()
    if decision not in ('Approved','Rejected') or not str(reason).strip():frappe.throw('Decision and review reason required')
    frappe.db.sql('SELECT name FROM `tabIL Registration Request` WHERE name=%s FOR UPDATE',(name,))
    d=frappe.get_doc('IL Registration Request',name)
    if d.status!='Pending review' or not d.email_verified or d.account_type not in ('Institute','Individual Teacher'):frappe.throw('No provider application pending')
    if decision=='Approved':
        details=json.loads(d.details)
        if not frappe.db.exists('User',d.email):
            user=frappe.get_doc({'doctype':'User','email':d.email,'first_name':details['full_name'],'enabled':1,'user_type':'Website User','send_welcome_email':0}).insert(ignore_permissions=True)
            user.reset_password(send_email=True)
    d.status=decision;d.reviewed_by=frappe.session.user;d.review_reason=str(reason)[:1000];d.save(ignore_permissions=True)
    return {'status':decision}
