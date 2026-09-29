"""Email introductions never grant membership or classroom access by themselves."""
from datetime import timedelta
from html import escape
import frappe
from frappe.utils import now_datetime,get_url,get_datetime
from .registration import limit
from .contact import email_address

def send_notice(email,subject,body):
    if not frappe.db.exists('Email Account',{'enable_outgoing':1}):return False
    frappe.sendmail(recipients=[email],subject=subject,message='<p>'+escape(body)+'</p><p><a href="'+escape(get_url('/campus#dashboard'),quote=True)+'">Open SISU</a></p>',delayed=True)
    return True

def require_mail():
    if not get_url().startswith('https://') or not frappe.db.exists('Email Account',{'enable_outgoing':1}):frappe.throw('Configure an outgoing Email Account and HTTPS site first')

@frappe.whitelist(methods=['POST'])
def invite_teacher(email):
    from .api import identity,require_role
    from .teaching import institute_profile
    inst,member=identity();require_role(member,'Admin');require_mail()
    try:email=email_address(email.strip())
    except ValueError as e:frappe.throw(str(e))
    limit('teacher-invite:'+member.user)
    profile=institute_profile(inst)
    with frappe.cache.lock('il_invite:'+inst.name+':'+email,timeout=10):
        if frappe.db.exists('IL Teacher Invitation',{'institute':inst.name,'invite_email':email,'status':'Pending','expires_at':['>',now_datetime()]}):frappe.throw('An invitation for this email is already pending')
        d=frappe.get_doc({'doctype':'IL Teacher Invitation','institute':inst.name,'profile':profile,'invite_email':email,'invited_by':member.user,'status':'Pending','expires_at':now_datetime()+timedelta(days=7)})
        d.flags.contact_service=True;d.insert(ignore_permissions=True)
        send_notice(email,'You are invited to teach at '+inst.title,inst.title+' invited you to connect on SISU. Sign in with this email using your verified teacher account, then review the invitation on your dashboard within 7 days. Accepting submits a membership request for institute approval.')
    return {'name':d.name,'status':'Pending','email_queued':True}

@frappe.whitelist(methods=['POST'])
def list_invitations():
    from .api import identity,require_role
    inst,m=identity();require_role(m,'Admin','Teacher')
    filters={'institute':inst.name} if m.role=='Admin' else {'invite_email':m.user.lower()}
    rows=frappe.get_all('IL Teacher Invitation',filters=filters,fields=['name','invite_email','profile','status','expires_at'],order_by='creation desc',limit_page_length=50)
    for r in rows:
        r['institute_title']=frappe.db.get_value('IL Public Profile',r.profile,'display_name')
        r['expired']=get_datetime(r.expires_at)<=now_datetime()
    return rows

@frappe.whitelist(methods=['POST'])
def respond(name,decision):
    from .api import identity,require_role
    from .profiles import required,relate
    _,m=identity();require_role(m,'Teacher');p=required()
    if p.kind!='Teacher':frappe.throw('Verified teacher profile required',frappe.PermissionError)
    if decision not in ('Accepted','Declined'):frappe.throw('Choose accept or decline')
    frappe.db.sql('SELECT name FROM `tabIL Teacher Invitation` WHERE name=%s FOR UPDATE',(name,))
    d=frappe.get_doc('IL Teacher Invitation',name)
    if d.invite_email.lower()!=m.user.lower():frappe.throw('This invitation belongs to another account',frappe.PermissionError)
    if d.status!='Pending' or get_datetime(d.expires_at)<=now_datetime():frappe.throw('This invitation is no longer pending')
    if decision=='Accepted':relate(d.profile,'Teacher membership')
    d.status=decision;d.responded_at=now_datetime();d.flags.contact_service=True;d.save(ignore_permissions=True)
    return {'status':decision}

@frappe.whitelist(methods=['POST'])
def request_by_email(email):
    from .profiles import required,relate
    p=required()
    if p.kind!='Teacher':frappe.throw('Only verified teachers can request membership',frappe.PermissionError)
    require_mail()
    try:email=email_address(email.strip())
    except ValueError as e:frappe.throw(str(e))
    limit('institute-request:'+frappe.session.user)
    target=frappe.db.get_value('IL Public Profile',{'user':email,'kind':'Institute','status':'Verified'},'name')
    if target:relate(target,'Teacher membership')
    return {'message':'If this email belongs to a verified institute on this site, your request is now in its membership inbox.'}
