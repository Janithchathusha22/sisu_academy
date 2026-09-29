"""Server-only account activation after verified identity, never selected login tiles."""
import frappe
from frappe.model.naming import make_autoname

def account_kind():
    profile=frappe.db.get_value('IL Public Profile',{'user':frappe.session.user},'kind')
    if profile:return profile
    kinds=frappe.get_all('IL Registration Request',filters={'email':frappe.session.user,'status':'Approved'},pluck='account_type')
    kinds=set(kinds)&{'Institute','Individual Teacher'}
    if len(kinds)>1:frappe.throw('Conflicting applications need owner review')
    if kinds:return 'Institute' if 'Institute' in kinds else 'Teacher'
    from .portal_policy import require_google_student
    require_google_student()
    return 'Student'

def activate(profile,workspace=None):
    from .api import institute
    inst=institute()
    if profile.kind=='Institute' and workspace!=inst.name:
        frappe.throw('Assign this site’s institute record before granting workspace administration')
    phone=frappe.db.get_value('IL Verified Phone',{'user':profile.user},'phone')
    if not phone:frappe.throw('Mobile verification is required')
    role={'Student':'Student','Teacher':'Teacher','Institute':'Admin'}[profile.kind]
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE',(profile.user,))
    existing=frappe.db.get_value('IL Member',{'institute':inst.name,'user':profile.user},['name','role','active'],as_dict=True)
    if existing:
        if existing.role!=role or not existing.active:frappe.throw('Existing membership requires an administrator review')
        return existing.name
    if role=='Admin' and frappe.db.exists('IL Public Profile',{'kind':'Institute','workspace':inst.name,'name':['!=',profile.name]}):
        frappe.throw('This site already belongs to an institute profile. Provision a separate site for another institute.')
    user=frappe.get_doc('User',profile.user)
    user.append_roles('Institute '+role)
    native_role={'Student':'LMS Student','Teacher':'Course Creator','Admin':'Moderator'}[role]
    if frappe.db.exists('Role',native_role):user.append_roles(native_role)
    user.save(ignore_permissions=True)
    prefix,width={'Student':('ST',5),'Teacher':('TC',4),'Admin':('AD',4)}[role]
    name=make_autoname(f"{prefix}-{inst.code}-.{'#'*width}")
    frappe.get_doc({'doctype':'IL Member','institute':inst.name,'user':profile.user,'role':role,'full_name':profile.display_name,
        'phone':phone,'active':1,'language':'en','whatsapp_opt_in':0,'email_opt_in':0}).insert(ignore_permissions=True,set_name=name)
    return name
