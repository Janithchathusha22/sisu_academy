"""Central directory API; relationships do not grant access to paid class materials."""
import hashlib
import json
import re
import frappe
from frappe.model.naming import make_autoname
from .wallet import signed_in,owner
from .domain import safe_url

def write(doc):
    doc.flags.community_service=True
    return doc.save(ignore_permissions=True)

def mine():
    signed_in()
    name=frappe.db.get_value('IL Public Profile',{'user':frappe.session.user},'name')
    return frappe.get_doc('IL Public Profile',name) if name else None

def required():
    p=mine()
    if not p or p.status!='Verified':frappe.throw('Complete your profile and verification first',frappe.PermissionError)
    if p.kind=='Student':
        from .portal_policy import require_google_student
        require_google_student()
    return p

def owner_notice(subject,reference):
    email=frappe.conf.get('il_owner_email')
    if email and frappe.db.exists('User',email):
        frappe.get_doc({'doctype':'Notification Log','subject':subject,'for_user':email,'type':'Alert',
                       'document_type':'IL Public Profile','document_name':reference}).insert(ignore_permissions=True)

@frappe.whitelist()
def me():
    p=mine()
    return {'profile':p.as_dict() if p else None,'phone_verified':bool(frappe.db.exists('IL Verified Phone',{'user':frappe.session.user}))}

@frappe.whitelist(methods=['POST'])
def save_profile(data):
    signed_in()
    if not frappe.db.exists('IL Verified Phone',{'user':frappe.session.user}):frappe.throw('Verify your mobile number first')
    if isinstance(data,str):data=json.loads(data)
    username=str(data.get('username','')).strip().lower()
    if not re.fullmatch(r'[a-z][a-z0-9_]{2,29}',username):frappe.throw('Username must be 3–30 lowercase letters, digits or underscores')
    if username in ('admin','administrator','sisu','support','api','owner'):frappe.throw('Reserved username')
    kind=data.get('kind')
    if kind not in ('Student','Teacher','Institute'):frappe.throw('Invalid profile type')
    p=mine()
    from .onboarding import account_kind
    if kind!=account_kind():frappe.throw('Use the account type approved for this identity')
    if kind=='Student':
        from .portal_policy import require_google_student
        require_google_student()
    elif not p and not frappe.db.exists('IL Registration Request',{'email':frappe.session.user,'account_type':'Institute' if kind=='Institute' else 'Individual Teacher','status':'Approved'}):
        frappe.throw('Your provider application must be approved first')
    p=mine()
    identity_changed=not p or p.display_name!=str(data.get('display_name','')).strip() or p.country!=str(data.get('country','')).strip() or bool(p.is_school)!=bool(data.get('is_school'))
    if p and (p.username!=username or p.kind!=kind):frappe.throw('Username and account type are permanent. Contact support for a reviewed change.')
    if not p:
        p=frappe.get_doc({'doctype':'IL Public Profile','user':frappe.session.user,'username':username,'kind':kind})
    for key,limit in [('display_name',120),('country',80),('bio',1000),('curriculum',150),('languages',150),('grades',150),('tagline',120),('qualifications',240)]:
        p.set(key,str(data.get(key,'')).strip()[:limit])
    if not p.display_name or not p.country:frappe.throw('Name and country required')
    from .profile_rules import provider_socials
    p.socials=json.dumps(provider_socials(kind,data.get('socials') or {}))
    p.is_school=int(kind=='Institute' and data.get('is_school') is True)
    # Identity or profile changes to a verified provider require re-review.
    if kind=='Student':p.status='Verified'
    elif identity_changed:p.status='Pending';p.reviewed_by=None
    write(p)
    if kind=='Student':
        from .onboarding import activate
        activate(p)
    if kind!='Student' and p.status=='Pending':owner_notice('Provider profile awaits verification: @'+username,p.name)
    return {'name':p.name,'username':username,'status':p.status,'code':p.code}

@frappe.whitelist()
def pending(page=0):
    owner()
    return frappe.get_all('IL Public Profile',filters={'status':'Pending','kind':['in',['Teacher','Institute']]},fields=['name','username','display_name','kind','country','creation'],start=max(0,min(int(page),10000))*50,limit_page_length=50)

@frappe.whitelist(methods=['POST'])
def review(profile,decision,reason,workspace=None):
    owner()
    if decision not in ('Verified','Rejected') or not str(reason).strip():frappe.throw('Decision and reason required')
    frappe.db.sql('SELECT name FROM `tabIL Public Profile` WHERE name=%s FOR UPDATE',(profile,))
    p=frappe.get_doc('IL Public Profile',profile)
    if p.kind=='Student' or p.status!='Pending':frappe.throw('No provider request pending')
    if p.user==frappe.session.user:frappe.throw('Self verification is not allowed',frappe.PermissionError)
    if decision=='Verified' and not p.code:
        words=re.findall(r'[A-Za-z]+',p.display_name)
        prefix=''.join(w[0] for w in words[:2]).upper().ljust(2,'X') if words else 'ED'
        p.code=make_autoname(prefix+'.#######')
    if decision=='Verified':
        from .onboarding import activate
        activate(p,workspace)
        if p.kind=='Institute':p.workspace=workspace
    p.status=decision;p.review_reason=str(reason)[:1000];p.reviewed_by=frappe.session.user;write(p)
    return {'code':p.code,'status':p.status}

@frappe.whitelist()
def search(query='',page=0):
    required();term=str(query).strip().lstrip('@')[:80]
    return frappe.get_all('IL Public Profile',filters={'status':'Verified','kind':['in',['Institute','Teacher']]},
       or_filters=[['username','like',f'%{term}%'],['display_name','like',f'%{term}%']],
       fields=['name','username','display_name','kind','country','code','bio','curriculum','languages','grades','socials','is_school','profile_image','cover_image','tagline','qualifications'],order_by='display_name asc',start=max(0,min(int(page),10000))*24,limit_page_length=24)

@frappe.whitelist(methods=['POST'])
def upload_image(kind):
    """Owned raster uploads only. Public profile images are deliberately public."""
    import io
    import secrets
    from PIL import Image, ImageOps, UnidentifiedImageError
    from frappe.utils.file_manager import save_file
    p=mine()
    if not p:frappe.throw('Save your profile first')
    if kind not in ('profile_image','cover_image'):frappe.throw('Invalid image placement')
    from .registration import limit
    limit('profile-image:'+frappe.session.user)
    item=frappe.request.files.get('file')
    if not item:frappe.throw('Choose an image')
    raw=item.stream.read(5*1024*1024+1)
    if len(raw)>5*1024*1024:frappe.throw('Images must be no larger than 5 MB')
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in ('JPEG','PNG','WEBP') or source.width*source.height>20000000:raise ValueError()
            source.load()
            size=(1600,600) if kind=='cover_image' else (400,400)
            result=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),size)
            out=io.BytesIO();result.save(out,format='WEBP',quality=85)
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError):frappe.throw('Choose a valid JPEG, PNG or WebP image under 20 megapixels')
    file=save_file('profile-'+secrets.token_hex(12)+'.webp',out.getvalue(),'IL Public Profile',p.name,is_private=0)
    p.set(kind,file.file_url);write(p)
    return {'url':file.file_url,'kind':kind}

@frappe.whitelist(methods=['POST'])
def relate(profile,kind):
    self=required();p=frappe.get_doc('IL Public Profile',profile)
    if p.status!='Verified' or p.kind=='Student' or p.user==frappe.session.user:frappe.throw('Provider unavailable')
    if kind=='Teacher membership' and (self.kind!='Teacher' or p.kind!='Institute'):frappe.throw('Teacher-to-institute request required')
    if kind=='Student join' and self.kind!='Student':frappe.throw('Student account required')
    if kind not in ('Follow','Student join','Teacher membership'):frappe.throw('Invalid relationship')
    key=hashlib.sha256(f'{frappe.session.user}:{profile}:{kind}'.encode()).hexdigest()
    name=frappe.db.get_value('IL Profile Relationship',{'relationship_key':key},'name')
    if name:
        doc=frappe.get_doc('IL Profile Relationship',name)
        if doc.status in ('Active','Pending'):return {'name':name,'status':doc.status}
    else:doc=frappe.get_doc({'doctype':'IL Profile Relationship','relationship_key':key,'profile':profile,'user':frappe.session.user,'kind':kind})
    doc.status='Active' if kind=='Follow' else 'Pending';write(doc)
    if kind=='Teacher membership':
        from .invitations import send_notice
        send_notice(p.user,'Teacher membership request',self.display_name+' (@'+self.username+') requested to join '+p.display_name+'. Open your institute dashboard to review the request.')
    return {'name':doc.name,'status':doc.status}

@frappe.whitelist(methods=['POST'])
def change_relationship(relationship,status,reason=''):
    r=frappe.get_doc('IL Profile Relationship',relationship)
    if r.kind=='Teacher membership':
        from .teaching import membership
        return membership(relationship,status)
    signed_in();frappe.db.sql('SELECT name FROM `tabIL Profile Relationship` WHERE name=%s FOR UPDATE',(relationship,))
    r=frappe.get_doc('IL Profile Relationship',relationship);p=frappe.get_doc('IL Public Profile',r.profile)
    if status=='Left':
        if r.user!=frappe.session.user:frappe.throw('Not your membership',frappe.PermissionError)
    elif status in ('Active','Rejected','Removed'):
        if p.user!=frappe.session.user or r.kind=='Follow':frappe.throw('Provider owner required',frappe.PermissionError)
        if status in ('Active','Rejected') and r.status!='Pending':frappe.throw('No pending request')
        if status=='Removed' and r.status!='Active':frappe.throw('No active membership')
    else:frappe.throw('Invalid status')
    r.status=status;r.reason=str(reason)[:1000];r.reviewed_by=frappe.session.user;write(r)
    return {'status':status}

@frappe.whitelist()
def relationships(profile):
    signed_in();p=frappe.get_doc('IL Public Profile',profile)
    filters={'profile':profile}
    if p.user!=frappe.session.user:filters['user']=frappe.session.user
    return {'followers':frappe.db.count('IL Profile Relationship',{'profile':profile,'kind':'Follow','status':'Active'}),
            'owns_profile':p.user==frappe.session.user,'relationships':frappe.get_all('IL Profile Relationship',filters=filters,fields=['name','profile','user','kind','status'],limit_page_length=100)}

@frappe.whitelist(methods=['POST'])
def publish_update(headline,body,url=''):
    from frappe.utils import now_datetime
    from datetime import timedelta
    p=required()
    if p.kind not in ('Teacher','Institute'):frappe.throw('Provider profile required',frappe.PermissionError)
    if not headline.strip() or len(headline)>80 or not body.strip() or len(body)>240:frappe.throw('Use a headline up to 80 characters and description up to 240')
    if frappe.db.count('IL Provider Update',{'profile':p.name,'creation':['>',now_datetime()-timedelta(days=1)]})>=20:frappe.throw('Daily update limit reached')
    d=frappe.get_doc({'doctype':'IL Provider Update','profile':p.name,'headline':headline,'body':body,
                     'url':safe_url(url) if url else '', 'expires_at':now_datetime()+timedelta(days=30)})
    write(d)
    return {'name':d.name}

@frappe.whitelist()
def followed_updates(page=0):
    from frappe.utils import now_datetime
    signed_in()
    # Join on verified providers and the current user's follows, then paginate in
    # SQL so one popular provider cannot expose someone else's private records.
    return frappe.db.sql('''SELECT u.name,u.headline,u.body,u.url,u.expires_at,p.display_name,p.username
        FROM `tabIL Provider Update` u JOIN `tabIL Public Profile` p ON p.name=u.profile
        WHERE u.expires_at>%s AND p.status='Verified' AND EXISTS
        (SELECT 1 FROM `tabIL Profile Relationship` r WHERE r.profile=p.name AND r.user=%s
         AND r.kind='Follow' AND r.status='Active') ORDER BY u.creation DESC LIMIT 25 OFFSET %s''',
        (now_datetime(),frappe.session.user,max(0,min(int(page),10000))*25),as_dict=True)

def purge_updates():
    from frappe.utils import now_datetime
    frappe.flags.il_provider_update_purge=True
    try:
        for name in frappe.get_all('IL Provider Update',filters={'expires_at':['<=',now_datetime()]},pluck='name',limit_page_length=500):
            frappe.delete_doc('IL Provider Update',name,ignore_permissions=True)
    finally:
        frappe.flags.il_provider_update_purge=False
