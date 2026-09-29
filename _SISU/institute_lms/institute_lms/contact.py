"""Member-owned contact verification and email preferences. No login-email changes."""
import hashlib
import hmac
import secrets
import time
import re
import frappe
from frappe.utils import get_url
from .api import identity


def email_address(value):
    if not isinstance(value, str) or len(value)>254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value):
        raise ValueError('Enter a valid email address')
    return value.strip().lower()


def code_digest(member, email, code, secret):
    return hmac.new(str(secret).encode(), f'{member}:{email}:{code}'.encode(), hashlib.sha256).hexdigest()


def own_member():
    inst, member = identity()
    if not member.name:
        frappe.throw('Use a named institute member account', frappe.PermissionError)
    return inst, member


@frappe.whitelist(methods=['POST'])
def status():
    _, member = own_member()
    connection = frappe.db.get_value('IL Calendar Connection', {'member':member.name}, ['status','google_email','last_synced'], as_dict=True)
    return {'email':member.get('contact_email') or '', 'verified':bool(member.get('contact_email_verified')),
            'email_opt_in':bool(member.get('email_opt_in')), 'calendar':connection or {'status':'Disconnected'}}


@frappe.whitelist(methods=['POST'])
def request_verification(email):
    inst, member = own_member()
    if not get_url().startswith('https://'): frappe.throw('Use your HTTPS institute site to verify an email')
    try: email=email_address(email)
    except ValueError as exc: frappe.throw(str(exc))
    if not frappe.db.exists('Email Account', {'enable_outgoing':1}): frappe.throw('Your institute must configure outgoing email first')
    now=int(time.time()); key='il_contact:'+member.name
    with frappe.cache.lock(key,timeout=10):
        pending=frappe.cache.get_value(key)
        if pending and now-pending['created']<60: frappe.throw('Wait one minute before requesting another code')
        bucket=f'il_contact_limit:{member.name}:{now//3600}'
        if (frappe.cache.get_value(bucket) or 0)>=5: frappe.throw('Too many codes requested. Please try later')
        frappe.cache.set_value(bucket,(frappe.cache.get_value(bucket) or 0)+1,expires_in_sec=7200)
        code=f'{secrets.randbelow(1000000):06d}'
        frappe.cache.set_value(key,{'email':email,'digest':code_digest(member.name,email,code,frappe.conf.encryption_key),'created':now,'attempts':0},expires_in_sec=600)
        frappe.sendmail(recipients=[email],subject='Verify your Sisu schedule email',message=f'<p>Your verification code is <strong>{code}</strong>.</p><p>It expires in 10 minutes. If you did not request this, ignore this email.</p>',delayed=True)
    return {'sent':True,'expires_in_seconds':600}


@frappe.whitelist(methods=['POST'])
def verify(code):
    _, member=own_member(); key='il_contact:'+member.name
    if not isinstance(code,str) or not re.fullmatch(r'\d{6}',code): frappe.throw('Enter the six-digit code')
    with frappe.cache.lock(key,timeout=10):
        pending=frappe.cache.get_value(key)
        if not pending or time.time()-pending['created']>=600 or pending['attempts']>=5: frappe.throw('Code expired. Request a new one')
        pending['attempts']+=1
        frappe.cache.set_value(key,pending,expires_in_sec=max(1,600-int(time.time()-pending['created'])))
        digest=code_digest(member.name,pending['email'],code,frappe.conf.encryption_key)
        if not hmac.compare_digest(digest,pending['digest']): frappe.throw('Code did not match')
        # A changed contact invalidates previous calendar consent. It never renames the login account.
        if member.get('contact_email')!=pending['email']:
            from .calendar_sync import disconnect_member
            disconnect_member(member.name)
        frappe.db.set_value('IL Member',member.name,{'contact_email':pending['email'],'contact_email_verified':1,'email_opt_in':0})
        frappe.cache.delete_value(key)
    return {'verified':True}


@frappe.whitelist(methods=['POST'])
def preferences(email_opt_in):
    _,member=own_member()
    if type(email_opt_in) is not bool: frappe.throw('Invalid preference')
    if email_opt_in and not member.get('contact_email_verified'): frappe.throw('Verify your email first')
    frappe.db.set_value('IL Member',member.name,'email_opt_in',int(email_opt_in))
    return {'saved':True}
