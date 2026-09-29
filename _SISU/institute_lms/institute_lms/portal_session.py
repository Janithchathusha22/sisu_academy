"""Session routing is resolved on the server. A selected login tile grants no role."""
import frappe
from .wallet import owner, admin_actor

@frappe.whitelist(allow_guest=True, methods=['GET'])
def current():
    if frappe.session.user=='Guest': return {'authenticated':False}
    if not frappe.db.get_value('User',frappe.session.user,'enabled'): frappe.throw('Account disabled',frappe.PermissionError)
    csrf=frappe.sessions.get_csrf_token()
    if admin_actor():
        owner()
        return {'authenticated':True,'role':'Super Admin','user':frappe.session.user,'csrf_token':csrf}
    from .api import institute
    inst=institute()
    member=frappe.db.get_value('IL Member',{'institute':inst.name,'user':frappe.session.user,'active':1},['name','role','full_name','user'],as_dict=True)
    if member and member.role=="Student":
        from .portal_policy import require_google_student
        require_google_student()
    onboarding_kind=None
    if not member:
        from .onboarding import account_kind
        onboarding_kind=account_kind()
    # Framework System Managers retain technical site administration, not automatic platform ownership.
    return {'authenticated':True,'role':member.role if member else 'Onboarding','onboarding_kind':onboarding_kind,'member':member,'user':frappe.session.user,'csrf_token':csrf}

@frappe.whitelist()
def overview():
    owner()
    return {'students':frappe.db.count('IL Member',{'role':'Student','active':1}),
        'teachers':frappe.db.count('IL Public Profile',{'kind':'Teacher','status':'Verified'}),
        'institutes':frappe.db.count('IL Public Profile',{'kind':'Institute','status':'Verified'}),
        'pending_profiles':frappe.db.count('IL Public Profile',{'status':'Pending'}),
        'pending_payouts':frappe.db.count('IL Payout Request',{'status':'Pending'})}
