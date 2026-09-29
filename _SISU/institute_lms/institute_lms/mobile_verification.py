"""Phone ownership verification. Provider hook must be configured server-side."""
import hashlib,hmac,re,secrets,time
import frappe
from frappe.utils import now_datetime,get_url
from .wallet import signed_in
from .profiles import write
from .registration import limit

@frappe.whitelist(methods=['POST'])
def request_code(phone):
    signed_in()
    senders=frappe.get_hooks('il_send_verification_sms')
    if not senders or not get_url().startswith('https://') or not frappe.conf.get('encryption_key'):frappe.throw('Secure SMS verification has not been configured')
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}',str(phone)):frappe.throw('Use an international phone number, for example +947…')
    limit('sms-user:'+frappe.session.user);limit('sms-phone:'+phone);limit('sms-ip:'+str(frappe.local.request_ip))
    code=f'{secrets.randbelow(1000000):06d}';key='il_mobile:'+frappe.session.user
    digest=hmac.new(str(frappe.conf.encryption_key).encode(),(phone+':'+code).encode(),hashlib.sha256).hexdigest()
    # The trusted hook must throw on provider failure; it must not log codes.
    frappe.get_attr(senders[0])(phone=phone,message='Your Sisu verification code is '+code+'. It expires in 10 minutes.')
    frappe.cache.set_value(key,{'phone':phone,'digest':digest,'created':time.time(),'attempts':0},expires_in_sec=600)
    return {'sent':True}

@frappe.whitelist(methods=['POST'])
def verify(code):
    signed_in();key='il_mobile:'+frappe.session.user
    if not re.fullmatch(r'[0-9]{6}',str(code)):frappe.throw('Six-digit code required')
    with frappe.cache.lock(key,timeout=10):
        d=frappe.cache.get_value(key)
        if not d or time.time()-d['created']>=600 or d['attempts']>=5:frappe.throw('Code expired')
        d['attempts']+=1;frappe.cache.set_value(key,d,expires_in_sec=max(1,600-int(time.time()-d['created'])))
        digest=hmac.new(str(frappe.conf.encryption_key).encode(),(d['phone']+':'+code).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(d['digest'],digest):frappe.throw('Code did not match')
        name=frappe.db.get_value('IL Verified Phone',{'user':frappe.session.user},'name')
        doc=frappe.get_doc('IL Verified Phone',name) if name else frappe.get_doc({'doctype':'IL Verified Phone','user':frappe.session.user})
        doc.phone=d['phone'];doc.verified_at=now_datetime();write(doc);frappe.cache.delete_value(key)
    return {'verified':True}

@frappe.whitelist(methods=['POST'])
def claim_trial():
    """Hosted-card adapter validates customer ownership, setup status and reuse."""
    signed_in()
    from .profiles import required
    required()
    hooks=frappe.get_hooks('il_verified_card_for_user')
    if not hooks:frappe.throw('Hosted card setup is not connected')
    with frappe.cache.lock('il_trial:'+frappe.session.user,timeout=20):
        if frappe.db.exists('IL Trial Claim',{'user':frappe.session.user}):frappe.throw('Trial already claimed')
        card=frappe.get_attr(hooks[0])(frappe.session.user)
        if not card or not card.get('verified') or card.get('user')!=frappe.session.user:frappe.throw('A verified card for this account is required')
        from datetime import timedelta
        end=now_datetime()+timedelta(days=3)
        doc=frappe.get_doc({'doctype':'IL Trial Claim','user':frappe.session.user,'verified_card_reference':card['reference'],'expires_at':end,'status':'Active'});write(doc)
    return {'expires_at':end,'status':'Active'}

def has_trial(user):
    row=frappe.db.get_value('IL Trial Claim',{'user':user},['expires_at','status'],as_dict=True)
    return bool(row and row.status=='Active' and row.expires_at>now_datetime())
