"""Scoped membership removal and tracked erasure requests. No silent hard deletes."""
import json
import frappe
from .api import identity, require_role, scoped, classroom_for, payload, set_member_active

@frappe.whitelist(methods=['POST'])
def account_controls():
    inst, member = identity()
    rooms = frappe.get_all('IL Classroom', filters={'institute':inst.name, **({'teacher':member.name} if member.role=='Teacher' else {})}, pluck='name') if member.role in ('Admin','Teacher') else []
    enrollments = frappe.get_all('IL Enrollment', filters={'institute':inst.name,'active':1,'classroom':['in',rooms or ['__none__']]}, fields=['name','student','classroom','active'], limit_page_length=1000)
    for row in enrollments:
        row.full_name = frappe.db.get_value('IL Member',row.student,'full_name')
    requests = frappe.get_all('IL Account Request',filters={'institute':inst.name,**({} if member.role=='Admin' else {'requested_by':frappe.session.user})},fields=['name','kind','status','creation'],limit_page_length=50)
    return {'enrollments':enrollments,'requests':requests,'memberships':[],'providers':[],'owned_profiles':[]}

@frappe.whitelist(methods=['POST'])
def account_action(data):
    inst, member = identity()
    v=payload(data)
    if v.confirmation!='CONFIRM' or not isinstance(v.reason,str) or not v.reason.strip() or len(v.reason)>500:
        frappe.throw('Confirm the action and provide a reason of up to 500 characters.')
    if v.kind=='remove_student':
        require_role(member,'Admin','Teacher')
        enrollment=scoped('IL Enrollment',v.target,inst)
        classroom_for(enrollment.classroom,write=True)
        frappe.get_doc({'doctype':'IL Access Audit','institute':inst.name,'enrollment':enrollment.name,
            'actor':frappe.session.user,'before_state':json.dumps({'active':enrollment.active,'access_override':enrollment.access_override}),
            'after_state':json.dumps({'active':0,'access_override':'Closed'}),'reason':v.reason}).insert(ignore_permissions=True)
        enrollment.active=0
        enrollment.access_override='Closed'
        enrollment.save(ignore_permissions=True)
        return {'removed':True}
    if v.kind=='remove_member':
        require_role(member,'Admin')
        set_member_active(v.target,0)
        return {'removed':True}
    if v.kind not in ('delete_profile','delete_institute'):
        frappe.throw('This action is unavailable on this site.')
    if v.kind=='delete_institute':
        require_role(member,'Admin')
    elif v.target!=member.name:
        frappe.throw('You may request deletion only of your own profile.',frappe.PermissionError)
    existing=frappe.db.get_value('IL Account Request',{'institute':inst.name,'requested_by':frappe.session.user,'kind':v.kind,'status':'Pending'},'name')
    if existing:
        return {'request':existing,'status':'Pending'}
    doc=frappe.get_doc({'doctype':'IL Account Request','institute':inst.name,'requested_by':frappe.session.user,'kind':v.kind,'reason':v.reason,'status':'Pending'}).insert(ignore_permissions=True)
    return {'request':doc.name,'status':'Pending'}
