"""Explicit public onboarding configuration; never exposes provider credentials."""
import frappe
from frappe.utils import cint
from .domain import safe_url

@frappe.whitelist(allow_guest=True)
def public():
    d=frappe.get_single('IL Portal Settings')
    return {'privacy_policy_url':d.privacy_policy_url or '', 'privacy_policy_version':d.privacy_policy_version or '',
        'provider_applications_enabled':bool(d.provider_applications_enabled and d.privacy_policy_url and d.privacy_policy_version),
        'google_available':bool(frappe.db.exists('Social Login Key',{'name':'google','enable_social_login':1}))}

@frappe.whitelist(methods=['POST'])
def save(privacy_policy_url='',privacy_policy_version='',provider_applications_enabled=0):
    from .wallet import owner,audit
    owner()
    url=safe_url(privacy_policy_url) if privacy_policy_url else ''
    enabled=cint(provider_applications_enabled)
    if enabled not in (0,1):frappe.throw('Invalid application setting')
    if enabled and (not url or not str(privacy_policy_version).strip()):frappe.throw('Publish a policy URL and version before enabling applications')
    d=frappe.get_single('IL Portal Settings');d.privacy_policy_url=url;d.privacy_policy_version=str(privacy_policy_version)[:80]
    d.provider_applications_enabled=enabled;d.save(ignore_permissions=True)
    audit('Update onboarding policy',d.name,'Privacy policy and application settings updated')
    return public()

@frappe.whitelist(allow_guest=True,methods=['POST'])
def google_start():
    from frappe.utils.oauth import get_oauth2_authorize_url
    if not public()['google_available']:frappe.throw('Google sign-in is not configured yet')
    return {'url':get_oauth2_authorize_url('google','/campus')}

def stamp_session(login_manager=None):
    """Only the trusted Google callback can stamp a newly-created browser session."""
    path=getattr(getattr(frappe.local,'request',None),'path','')
    callback='frappe.integrations.oauth2_logins.login_via_google'
    frappe.session.data['il_google_session']=int(path=='/api/method/'+callback and frappe.session.user!='Guest')
    frappe.local.session_obj.update(force=True)

def require_google_student():
    if not getattr(frappe.session,'data',{}).get('il_google_session'):
        frappe.throw('Students must sign in with Google',frappe.AuthenticationError)

def validate_login(login_manager):
    user=login_manager.user
    student=frappe.db.exists('IL Public Profile',{'user':user,'kind':'Student'}) or frappe.db.exists('IL Member',{'user':user,'role':'Student'})
    path=getattr(getattr(frappe.local,'request',None),'path','')
    if student and path!='/api/method/frappe.integrations.oauth2_logins.login_via_google':
        frappe.throw('Students must sign in with Google',frappe.AuthenticationError)
