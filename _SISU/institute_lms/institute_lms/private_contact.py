"""Self-service personal details; never part of public profiles/search."""
import json
import frappe
from frappe.utils import now_datetime,getdate
from .wallet import signed_in
from .private_contact_rules import normalize,age_on,FIELDS,guardian_updates_without_otp

def own():
    signed_in()
    name=frappe.db.get_value('IL Private Contact',{'user':frappe.session.user},'name')
    return frappe.get_doc('IL Private Contact',name) if name else None

@frappe.whitelist(methods=['POST'])
def get_details():
    d=own()
    data={k:d.get(k) for k in FIELDS} if d else {'notification_language':'en'}
    data['age']=age_on(str(d.date_of_birth),getdate()) if d and d.date_of_birth else None
    return {'data':data,'verified_phone':frappe.db.get_value('IL Verified Phone',{'user':frappe.session.user},'phone') or '',
            'login_email':frappe.session.user}

@frappe.whitelist(methods=['POST'])
def save_details(data):
    signed_in()
    from .onboarding import account_kind
    if isinstance(data,str):data=json.loads(data)
    kind=account_kind()
    try:values=normalize(data,kind,getdate())
    except ValueError as e:frappe.throw(str(e))
    if values['whatsapp_opt_in'] and not guardian_updates_without_otp(values,kind,getdate()) and not frappe.db.exists('IL Verified Phone',{'user':frappe.session.user,'phone':values['whatsapp_phone']}):frappe.throw('Verify this WhatsApp number before enabling updates')
    d=own() or frappe.get_doc({'doctype':'IL Private Contact','user':frappe.session.user})
    if bool(d.get('whatsapp_opt_in'))!=bool(values['whatsapp_opt_in']) or d.get('whatsapp_phone')!=values['whatsapp_phone']:d.consent_at=now_datetime()
    d.update(values);d.flags.contact_service=True;d.save(ignore_permissions=True)
    for name in frappe.get_all('IL Member',filters={'user':frappe.session.user,'active':1},pluck='name'):
        frappe.db.set_value('IL Member',name,{'phone':values['whatsapp_phone'],'whatsapp_opt_in':values['whatsapp_opt_in'],'language':values['notification_language']})
    return {'saved':True,'age':age_on(values['date_of_birth'],getdate())}

@frappe.whitelist(methods=['POST'])
def request_whatsapp_code(phone):
    import hashlib,hmac,re,secrets,time,requests
    from frappe.utils import get_url
    from .registration import limit
    signed_in()
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}',str(phone)):frappe.throw('Use an international phone number')
    template=frappe.conf.get('il_whatsapp_auth_template') or {}
    token=frappe.conf.get('il_whatsapp_token');phone_id=frappe.conf.get('il_whatsapp_phone_id');version=frappe.conf.get('il_whatsapp_graph_version')
    if not get_url().startswith('https://') or not all((token,phone_id,version,template.get('name'),template.get('language'),frappe.conf.get('encryption_key'))):frappe.throw('Your administrator must configure WhatsApp authentication first')
    limit('wa-user:'+frappe.session.user);limit('wa-phone:'+phone);limit('wa-ip:'+str(frappe.local.request_ip))
    key='il_mobile:'+frappe.session.user
    with frappe.cache.lock(key,timeout=30):
        old=frappe.cache.get_value(key)
        if old and time.time()-old['created']<60:frappe.throw('Wait one minute before requesting another code')
        code=f'{secrets.randbelow(1000000):06d}'
        digest=hmac.new(str(frappe.conf.encryption_key).encode(),(phone+':'+code).encode(),hashlib.sha256).hexdigest()
        try:
            response=requests.post(f'https://graph.facebook.com/{version}/{phone_id}/messages',headers={'Authorization':'Bearer '+token},timeout=(5,15),json={'messaging_product':'whatsapp','to':phone.lstrip('+'),'type':'template','template':{'name':template['name'],'language':{'code':template['language']},'components':[{'type':'body','parameters':[{'type':'text','text':code}]},{'type':'button','sub_type':'url','index':'0','parameters':[{'type':'text','text':code}]}]}})
            if not response.ok:frappe.throw('WhatsApp rejected the verification request. Ask your administrator to check the authentication template.')
        except requests.RequestException:frappe.throw('Could not confirm WhatsApp delivery. Try again later.')
        frappe.cache.set_value(key,{'phone':phone,'digest':digest,'created':time.time(),'attempts':0},expires_in_sec=600)
    return {'sent':True}
