"""Provider-owned classrooms, programme bundles and reviewed teaching assignments."""
import json
import hashlib
from datetime import timedelta
import frappe
from frappe.utils import today,getdate,cint
from .teaching_rules import capabilities,module_plan,billing_month
from .domain import money,limited

def rights(room,member):
    affiliated=True
    if member.role=='Teacher' and room.get('owner_type')!='Teacher' and room.get('public_provider'):
        affiliated=bool(frappe.db.exists('IL Profile Relationship',{'profile':room.public_provider,'user':member.user,'kind':'Teacher membership','status':'Active'}))
    return capabilities(room,member,affiliated)

def require(room,member,action):
    if not rights(room,member).get(action):frappe.throw('Your classroom permission does not allow this action',frappe.PermissionError)

def institute_profile(inst):
    name=frappe.db.get_value('IL Public Profile',{'workspace':inst.name,'kind':'Institute','status':'Verified'},'name')
    if not name:frappe.throw('Verify the institute profile first')
    return name

def approved_teacher(inst,teacher,profile):
    from .api import scoped
    m=scoped('IL Member',teacher,inst)
    if m.role!='Teacher' or not m.active or not frappe.db.exists('IL Profile Relationship',{'profile':profile,'user':m.user,'kind':'Teacher membership','status':'Active'}):
        frappe.throw('Select a teacher with an approved institute membership')
    return m

@frappe.whitelist()
def overview():
    from .api import identity,room_filters
    inst,m=identity()
    rooms=frappe.get_all('IL Classroom',filters=room_filters(inst,m),fields=['name','title','subject','teacher','fee','billing_type','owner_type','teacher_access','public_provider','cover_image'])
    names=[r.name for r in rooms] or ['__none__']
    enrollments=frappe.get_all('IL Enrollment',filters={'classroom':['in',names],'active':1},fields=['student'])
    # Aggregate only this workspace's classroom invoices; amounts remain separated by currency.
    totals=frappe.db.sql('SELECT currency,status,SUM(beneficiary_minor)/100 amount FROM `tabIL Invoice` WHERE classroom IN %(rooms)s GROUP BY currency,status',{'rooms':tuple(names)},as_dict=True)
    links=[]
    if m.role=='Admin':
        provider=institute_profile(inst)
        links=frappe.get_all('IL Profile Relationship',filters={'profile':provider,'kind':'Teacher membership','status':['in',['Pending','Active']]},fields=['name','user','status','creation'])
    elif m.role=='Teacher':
        links=frappe.get_all('IL Profile Relationship',filters={'user':m.user,'kind':'Teacher membership','status':['in',['Pending','Active']]},fields=['name','profile','status','creation'])
    for link in links:
        p=frappe.db.get_value('IL Public Profile',{'user':link.user} if m.role=='Admin' else link.profile,['name','display_name','qualifications','profile_image','cover_image','username'],as_dict=True)
        link['person']=p
    return {'students':len({e.student for e in enrollments}),'teachers':len({l.user for l in links if l.status=='Active'}) if m.role=='Admin' else 1,
        'classrooms':rooms,'totals':totals,'memberships':links,'programmes':programmes()}

@frappe.whitelist(methods=['POST'])
def membership(name,status):
    from .api import identity
    from .profiles import write
    inst,m=identity()
    frappe.db.sql('SELECT name FROM `tabIL Profile Relationship` WHERE name=%s FOR UPDATE',(name,))
    r=frappe.get_doc('IL Profile Relationship',name)
    if r.kind!='Teacher membership':frappe.throw('Teacher membership required')
    if status=='Left':
        if r.user!=m.user or r.status not in ('Pending','Active'):frappe.throw('Not your active membership',frappe.PermissionError)
    elif status in ('Active','Rejected','Removed'):
        if m.role!='Admin' or r.profile!=institute_profile(inst):frappe.throw('Institute administrator required',frappe.PermissionError)
        if (status in ('Active','Rejected') and r.status!='Pending') or (status=='Removed' and r.status!='Active'):frappe.throw('This request has already changed')
        if status=='Active' and not frappe.db.exists('IL Public Profile',{'user':r.user,'kind':'Teacher','status':'Verified'}):frappe.throw('Teacher verification is required')
    else:frappe.throw('Invalid membership decision')
    r.status=status;r.reviewed_by=m.user;write(r)
    if status in ('Left','Removed'):
        teachers=frappe.get_all('IL Member',filters={'user':r.user,'institute':inst.name},pluck='name')
        for room in frappe.get_all('IL Classroom',filters={'public_provider':r.profile,'teacher':['in',teachers or ['__none__']],'owner_type':'Institute'},pluck='name'):
            frappe.db.set_value('IL Classroom',room,'teacher_assignment_active',0)
    return {'status':status}

@frappe.whitelist(methods=['POST'])
def leave_class(classroom):
    from .api import classroom_for
    _,m,room=classroom_for(classroom,write=True)
    if m.role!='Teacher' or room.get('owner_type')=='Teacher' or room.teacher!=m.name:frappe.throw('Only an assigned institute teacher can leave this class')
    room.teacher_assignment_active=0;room.save(ignore_permissions=True)
    room.add_comment('Info','Teacher left the assignment; institute must reassign this classroom.')
    return {'left':True}

@frappe.whitelist()
def programmes():
    from .api import identity,room_filters
    inst,m=identity();filters={'institute':inst.name,'active':1}
    rows=frappe.get_all('IL Programme',filters=filters,pluck='name',limit_page_length=100)
    result=[]
    for name in rows:
        p=frappe.get_doc('IL Programme',name)
        if m.role=='Teacher' and not any(x.teacher==m.name for x in p.modules):continue
        d=p.as_dict()
        for row in d['modules']:row['teacher_name']=frappe.db.get_value('IL Member',row['teacher'],'full_name')
        d['students']=frappe.db.count('IL Programme Enrollment',{'programme':name,'active':1})
        result.append(d)
    return result

@frappe.whitelist(methods=['POST'])
def save_programme(data):
    from .api import identity,require_role,scoped,verified_image
    inst,m=identity();require_role(m,'Admin');data=json.loads(data) if isinstance(data,str) else data
    rows=data.get('modules',[])
    try:module_plan(rows)
    except ValueError as e:frappe.throw(str(e))
    provider=institute_profile(inst)
    p=scoped('IL Programme',data['name'],inst) if data.get('name') else frappe.new_doc('IL Programme')
    if not p.is_new():
        frappe.db.sql('SELECT name FROM `tabIL Programme` WHERE name=%s FOR UPDATE',(p.name,))
        p.reload()
    if not p.is_new() and frappe.db.exists('IL Programme Enrollment',{'programme':p.name}):frappe.throw('Enrolled programmes are locked. Create a new intake to change fees or modules.')
    old=[x.classroom for x in p.get('modules') or []]
    p.institute=inst.name;p.provider=provider;p.title=limited(data.get('title'),120,'Title');p.description=limited(data.get('description'),1500,'Description')
    if not p.title:frappe.throw('Programme title required')
    p.fee=money(data.get('fee'));p.currency='LKR';p.duration_months=cint(data.get('duration_months',6))
    if not 1<=p.duration_months<=60:frappe.throw('Duration must be 1–60 months')
    p.starts_on=getdate(data['starts_on']) if data.get('starts_on') else None;p.ends_on=getdate(data['ends_on']) if data.get('ends_on') else None
    if p.starts_on and p.ends_on and p.ends_on<p.starts_on:frappe.throw('End date must follow start date')
    p.cover_image=verified_image(data.get('cover_image',''),m);p.set('modules',[])
    rooms=[]
    for name in sorted(row['classroom'] for row in rows):
        frappe.db.sql('SELECT name FROM `tabIL Classroom` WHERE name=%s FOR UPDATE',(name,))
    for row in rows:
        room=scoped('IL Classroom',row['classroom'],inst)
        if not room.active or room.get('owner_type')=='Teacher' or (room.get('programme') and room.programme!=p.name):frappe.throw('Choose an active, unbundled institute classroom')
        if frappe.db.exists('IL Enrollment',{'classroom':room.name}):frappe.throw('A classroom with existing enrollments cannot move into a bundle')
        approved_teacher(inst,room.teacher,provider);rooms.append(room)
        p.append('modules',{'classroom':room.name,'title':room.subject or room.title,'teacher':room.teacher,'duration_weeks':int(row.get('duration_weeks',2)),'starts_on':row.get('starts_on') or None})
    p.save(ignore_permissions=True)
    for name in set(old)-{r.name for r in rooms}:frappe.db.set_value('IL Classroom',name,{'programme':None,'billing_type':'One-time'})
    for room in rooms:frappe.db.set_value('IL Classroom',room.name,{'programme':p.name,'billing_type':'Programme module'})
    return p.name

@frappe.whitelist(methods=['POST'])
def enroll_programme(programme):
    from .api import identity,require_role,scoped
    from .class_billing import invoice_split
    inst,m=identity();require_role(m,'Student');p=scoped('IL Programme',programme,inst)
    frappe.db.sql('SELECT name FROM `tabIL Programme` WHERE name=%s FOR UPDATE',(p.name,))
    p.reload()
    frappe.db.sql('SELECT name FROM `tabIL Member` WHERE name=%s FOR UPDATE',(m.name,))
    previous=frappe.db.get_value('IL Programme Enrollment',{'programme':p.name,'student':m.name},'name')
    if previous:return {'enrollment':previous,'existing':True}
    if not p.active or not p.modules:frappe.throw('Programme unavailable')
    rooms=[scoped('IL Classroom',row.classroom,inst) for row in p.modules]
    if any(not r.active or r.programme!=p.name or r.get('owner_type')=='Teacher' for r in rooms):frappe.throw('Programme modules need administrator review')
    if any(frappe.db.exists('IL Enrollment',{'classroom':r.name,'student':m.name}) for r in rooms):frappe.throw('Existing module enrollment needs administrator review')
    quote=invoice_split(inst,money(p.fee),m.user,room=rooms[0])
    purchase=frappe.get_doc({'doctype':'IL Programme Enrollment','programme':p.name,'student':m.name,'active':1}).insert(ignore_permissions=True)
    for i,room in enumerate(rooms):
        e=frappe.get_doc({'doctype':'IL Enrollment','institute':inst.name,'student':m.name,'classroom':room.name,'programme_enrollment':purchase.name,'fee':quote['amount'] if quote else 0,'active':1,'access_override':'Automatic'}).insert(ignore_permissions=True)
        if i==0:
            purchase.billing_enrollment=e.name;purchase.save(ignore_permissions=True)
            if quote and quote['amount']>0:frappe.get_doc({'doctype':'IL Invoice','institute':inst.name,'enrollment':e.name,'classroom':room.name,'student':m.name,**quote,'due_date':today(),'installment':1,'status':'Unpaid'}).insert(ignore_permissions=True)
    return {'enrollment':purchase.name,'existing':False}

@frappe.whitelist(methods=['POST'])
def month_invoice(classroom,month):
    from .api import identity,scoped,require_role
    from .class_billing import invoice_split
    inst,m=identity();require_role(m,'Student');room=scoped('IL Classroom',classroom,inst)
    month=billing_month(month)
    if abs((getdate(month+'-01')-getdate(today())).days)>370:frappe.throw('Choose a month within one year')
    if not room.active or room.get('billing_type')!='Monthly':frappe.throw('Monthly classroom required')
    frappe.db.sql('SELECT name FROM `tabIL Member` WHERE name=%s FOR UPDATE',(m.name,))
    enrollment=frappe.db.get_value('IL Enrollment',{'student':m.name,'classroom':room.name,'active':1},'name')
    if not enrollment:frappe.throw('Join this classroom first')
    key=hashlib.sha256((enrollment+':'+month).encode()).hexdigest()
    existing=frappe.db.get_value('IL Invoice',{'billing_key':key},'name')
    if existing:return {'invoice':existing,'existing':True}
    quote=invoice_split(inst,0 if room.fee_mode=='Free' else money(room.fee),m.user,room=room)
    if not quote:return {'invoice':None,'school_mode':True}
    invoice=frappe.get_doc({'doctype':'IL Invoice','institute':inst.name,'enrollment':enrollment,'classroom':room.name,'student':m.name,**quote,'due_date':month+'-01','billing_month':month,'billing_key':key,'installment':1,'status':'Paid' if quote['amount']==0 else 'Unpaid'}).insert(ignore_permissions=True)
    return {'invoice':invoice.name,'existing':False}
