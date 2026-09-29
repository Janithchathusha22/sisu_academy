"""Public profile metadata only. Lessons and payments keep their own access checks."""
import frappe
from frappe.utils import today,cint
from .api import identity,scoped,require_role,paginate

FIELDS=['name','username','display_name','kind','code','tagline','qualifications','bio','country','socials','profile_image','cover_image','curriculum','grades','languages']

def provider(name):
    p=frappe.get_doc('IL Public Profile',name)
    if p.status!='Verified' or p.kind not in ('Teacher','Institute'):frappe.throw('Provider unavailable',frappe.PermissionError)
    return p

def profile_row(p):return {key:p.get(key) for key in FIELDS}

def class_filters(p,inst):
    filters={'institute':inst.name,'active':1,'published':1}
    if p.kind=='Institute':filters['public_provider']=p.name
    else:
        members=frappe.get_all('IL Member',filters={'institute':inst.name,'user':p.user,'role':'Teacher','active':1},pluck='name')
        filters['teacher']=['in',members or ['__none__']]
    return filters

@frappe.whitelist()
def detail(profile,page=0):
    inst,member=identity();p=provider(profile)
    classes=frappe.get_all('IL Classroom',filters=class_filters(p,inst),fields=['name','title','subject','grade','teaching_medium','cover_image','teacher','fee_mode','schedule_label','public_provider','billing_type','programme','owner_type'],order_by='title asc',limit_start=paginate(page),limit_page_length=24)
    teachers=[]
    if p.kind=='Institute':
        users=frappe.get_all('IL Profile Relationship',filters={'profile':p.name,'kind':'Teacher membership','status':'Active'},pluck='user',limit_page_length=0)
        teachers=frappe.get_all('IL Public Profile',filters={'user':['in',users or ['__none__']],'kind':'Teacher','status':'Verified'},fields=FIELDS,order_by='display_name asc',limit_start=paginate(page),limit_page_length=24)
    return {'profile':profile_row(p),'classes':classes,'teachers':teachers}

@frappe.whitelist()
def publishing_options():
    inst,member=identity();require_role(member,'Teacher','Admin')
    own=frappe.get_all('IL Public Profile',filters={'user':frappe.session.user,'status':'Verified','kind':['in',['Teacher','Institute']]},fields=['name','display_name','kind','workspace'])
    links=frappe.get_all('IL Profile Relationship',filters={'user':frappe.session.user,'kind':'Teacher membership','status':'Active'},pluck='profile')
    others=frappe.get_all('IL Public Profile',filters={'name':['in',links or ['__none__']],'kind':'Institute','status':'Verified','workspace':inst.name},fields=['name','display_name','kind','workspace'])
    choices=[p for p in own if p['kind']=='Teacher' or p['workspace']==inst.name]+others
    if member.role=='Admin':
        teachers=frappe.get_all('IL Member',filters={'institute':inst.name,'role':'Teacher','active':1},pluck='user')
        choices+=frappe.get_all('IL Public Profile',filters={'user':['in',teachers or ['__none__']],'kind':'Teacher','status':'Verified'},fields=['name','display_name','kind','workspace'])
    return list({p['name']:p for p in choices}.values())

def validate_publication(room,member,data):
    mode=data.get('fee_mode',room.get('fee_mode') or 'Paid')
    if mode not in ('Free','Paid'):frappe.throw('Choose Free or Paid')
    room.fee_mode=mode
    room.schedule_label=str(data.get('schedule_label',''))[:140]
    room.published=cint(data.get('published'))
    if room.published not in (0,1):frappe.throw('Invalid publication setting')
    name=data.get('public_provider') or None
    if room.published and not name:frappe.throw('Choose a verified provider before publishing')
    if name:
        allowed={p['name'] for p in publishing_options()}
        if name not in allowed:frappe.throw('Approved provider membership required',frappe.PermissionError)
    room.public_provider=name

@frappe.whitelist(methods=['POST'])
def join_class(classroom):
    inst,member=identity();require_role(member,'Student')
    room=scoped('IL Classroom',classroom,inst)
    if not room.active or not room.published:frappe.throw('Classroom unavailable')
    provider(room.public_provider)
    if room.get('programme'):frappe.throw('Join the complete programme from Programmes; modules are included in one payment')
    # A member lock plus unique enrollment constraint makes repeated clicks safe.
    frappe.db.sql('SELECT name FROM `tabIL Member` WHERE name=%s FOR UPDATE',(member.name,))
    existing=frappe.db.get_value('IL Enrollment',{'classroom':room.name,'student':member.name},['name','active'],as_dict=True)
    if existing:
        if not existing.active:frappe.throw('Ask the provider to review your inactive enrollment')
        return {'enrollment':existing.name,'existing':True}
    from .api import create_enrollment
    fee=0 if room.fee_mode=='Free' else room.fee
    name=create_enrollment(inst,room,member,[{'amount':fee,'due_date':today()}] if fee else [])
    return {'enrollment':name,'existing':False}
