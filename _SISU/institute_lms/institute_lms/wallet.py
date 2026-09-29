"""Server-owned wallet ledger. Transfers are executed outside this API by finance.

Mutations use database row locks, unique idempotency keys and the enclosing Frappe
POST transaction. Never commit between reserving funds and writing the request.
"""
import csv
import hashlib
import io
import json
import re
import frappe
from frappe.utils import now_datetime
from .registration import require_owner
from .wallet_rules import minor, reserve, transition, payout_details, csv_cell

def signed_in():
    if frappe.session.user=='Guest': frappe.throw('Sign in required',frappe.PermissionError)

def owner():
    signed_in();require_owner()

def admin_actor():
    return bool(frappe.conf.get('il_owner_provisioned') and frappe.session.user!='Guest' and frappe.session.user.lower()==str(frappe.conf.get('il_owner_email','')).lower())

def saved(doc):
    doc.flags.wallet_service=True
    return doc.save(ignore_permissions=True)

def insert(doctype,**data):
    doc=frappe.get_doc({'doctype':doctype,**data});doc.flags.wallet_service=True
    return doc.insert(ignore_permissions=True)

def audit(action,reference,details=''):
    insert('IL Payout Audit',action=action,reference=reference,actor=frappe.session.user,details=str(details)[:1000])

def locked_wallet(name):
    if not frappe.db.sql('SELECT name FROM `tabIL Wallet` WHERE name=%s FOR UPDATE',(name,)):
        frappe.throw('Wallet unavailable',frappe.PermissionError)
    return frappe.get_doc('IL Wallet',name)

def authorized(name,lock=False):
    signed_in()
    w=locked_wallet(name) if lock else frappe.get_doc('IL Wallet',name)
    if w.owner_user!=frappe.session.user and not admin_actor(): frappe.throw('Wallet unavailable',frappe.PermissionError)
    if not w.enabled: frappe.throw('Wallet is paused')
    return w

def minimum(currency):
    if currency=='USD':return 2000
    if currency!='LKR':frappe.throw('Unsupported wallet currency')
    return usd_lkr_minor(20)

def usd_lkr_minor(dollars):
    from decimal import Decimal, ROUND_CEILING
    from frappe.utils import get_datetime
    from datetime import timedelta
    from decimal import InvalidOperation
    try:
        rate=Decimal(str(frappe.conf.get('il_usd_lkr_rate') or 0))
    except InvalidOperation:
        frappe.throw('Finance must configure a valid USD/LKR reference rate')
    updated=frappe.conf.get('il_usd_lkr_rate_updated_at')
    if not rate.is_finite() or rate<=0 or rate>100000 or not updated or not now_datetime()-timedelta(days=7)<=get_datetime(updated)<=now_datetime():
        frappe.throw('Finance must publish a USD/LKR reference rate dated within the last seven days')
    return int((Decimal(dollars)*rate*100).to_integral_value(rounding=ROUND_CEILING))

def post(w,event,kind,available_delta,held_delta,**links):
    if frappe.db.exists('IL Wallet Transaction',{'event_key':event}): return
    a=int(w.available_minor or 0)+available_delta;h=int(w.held_minor or 0)+held_delta
    if h<0 or abs(a)>2000000000 or h>2000000000: frappe.throw('Wallet limit exceeded; reconcile before continuing')
    insert('IL Wallet Transaction',wallet=w.name,event_key=event,kind=kind,
           available_delta=available_delta,held_delta=held_delta,available_after=a,held_after=h,
           actor=frappe.session.user,**links)
    w.available_minor=a;w.held_minor=h;saved(w)

@frappe.whitelist(methods=['POST'])
def provision_wallet(user,beneficiary,country,currency,institute=None):
    owner()
    if beneficiary not in ('Teacher','Institute') or currency not in ('LKR','USD') or not country:
        frappe.throw('Invalid wallet identity')
    if not frappe.db.get_value('User',user,'enabled'): frappe.throw('Enabled account required')
    if beneficiary=='Institute' and not frappe.db.exists('IL Institute',institute): frappe.throw('Institute required')
    if beneficiary=='Teacher' and institute: frappe.throw('Independent teacher wallet cannot own institute revenue')
    if (country=='Sri Lanka')!=(currency=='LKR'): frappe.throw('Sri Lanka wallets use LKR; international wallets use USD')
    identity=hashlib.sha256(f'{user}|{beneficiary}|{institute or ""}|{currency}'.encode()).hexdigest()
    existing=frappe.db.get_value('IL Wallet',{'identity_key':identity},'name')
    if existing:return {'name':existing}
    w=insert('IL Wallet',identity_key=identity,owner_user=user,beneficiary=beneficiary,institute=institute,
             country=country,currency=currency,available_minor=0,held_minor=0,enabled=1)
    audit('Wallet provisioned',w.name)
    return {'name':w.name}

@frappe.whitelist()
def dashboard(wallet=None,page=0):
    signed_in()
    choices=frappe.get_all('IL Wallet',filters={'owner_user':frappe.session.user},fields=['name','beneficiary','currency','institute'],limit_page_length=100)
    if not wallet:
        if not choices:return {'wallets':[],'wallet':None,'ledger':[],'methods':[],'requests':[]}
        wallet=choices[0].name
    w=authorized(wallet)
    fields=['name','kind','masked_label','country','status','creation','review_reason']
    return {'wallets':choices,'wallet':{k:w.get(k) for k in ('name','beneficiary','currency','available_minor','held_minor','country')},
            'minimum_minor':minimum(w.currency),
            'ledger':frappe.get_all('IL Wallet Transaction',filters={'wallet':w.name},fields=['name','creation','kind','available_delta','held_delta','available_after','reference','reason'],order_by='creation desc',start=max(0,min(int(page),10000))*25,limit_page_length=25),
            'methods':frappe.get_all('IL Payout Method',filters={'wallet':w.name},fields=fields,order_by='creation desc',limit_page_length=50),
            'requests':frappe.get_all('IL Payout Request',filters={'wallet':w.name},fields=['name','creation','method','amount_minor','currency','status','transaction_reference','reason'],order_by='creation desc',limit_page_length=50)}

@frappe.whitelist(methods=['POST'])
def submit_method(wallet,data):
    w=authorized(wallet,True)
    if w.owner_user!=frappe.session.user: frappe.throw('Only the beneficiary can submit payout details',frappe.PermissionError)
    if isinstance(data,str):data=json.loads(data)
    d=payout_details(data)
    if d['country']!=w.country: frappe.throw('Country must match the verified wallet')
    if frappe.db.count('IL Payout Method',{'wallet':w.name,'status':'Pending'})>=3: frappe.throw('Please wait for finance to review your pending methods')
    last=d.get('account') or d.get('email') or d.get('payoneer_id') or d.get('iban')
    method=insert('IL Payout Method',wallet=w.name,kind=d['kind'],country=d['country'],
                  masked_label=d['kind']+' · ••••'+last[-4:],secret_details=json.dumps(d,ensure_ascii=False),status='Pending',submitted_by=frappe.session.user)
    audit('Payout method submitted',method.name)
    return {'name':method.name,'status':'Pending'}

@frappe.whitelist(methods=['POST'])
def review_method(method,decision,reason):
    owner()
    if decision not in ('Approved','Rejected') or not str(reason).strip():frappe.throw('Decision and reason required')
    m=frappe.get_doc('IL Payout Method',method);locked_wallet(m.wallet);m.reload()
    if m.submitted_by==frappe.session.user:frappe.throw('Another authorized finance reviewer must approve their own details',frappe.PermissionError)
    if m.status!='Pending':frappe.throw('Method already reviewed')
    if decision=='Approved':
        for name in frappe.get_all('IL Payout Method',filters={'wallet':m.wallet,'status':'Approved'},pluck='name'):
            old=frappe.get_doc('IL Payout Method',name);old.status='Superseded';saved(old)
    m.update({'status':decision,'reviewed_by':frappe.session.user,'reviewed_at':now_datetime(),'review_reason':str(reason)[:1000]});saved(m)
    audit('Payout method '+decision,method,reason)
    return {'status':decision}

@frappe.whitelist(methods=['POST'])
def request_payout(wallet,method,amount,request_key):
    w=authorized(wallet,True)
    if w.owner_user!=frappe.session.user:frappe.throw('Only the beneficiary can request a payout',frappe.PermissionError)
    if not re.fullmatch(r'[A-Za-z0-9-]{16,80}',str(request_key)):frappe.throw('Valid idempotency key required')
    key=hashlib.sha256((wallet+':'+request_key).encode()).hexdigest();cents=minor(amount)
    prior=frappe.db.get_value('IL Payout Request',{'request_key':key},['name','amount_minor','method','status'],as_dict=True)
    if prior:
        if prior.amount_minor!=cents or prior.method!=method:frappe.throw('Idempotency key was used for another request')
        return prior
    m=frappe.get_doc('IL Payout Method',method)
    if m.wallet!=w.name or m.status!='Approved':frappe.throw('An approved payout method is required')
    reserve(int(w.available_minor),int(w.held_minor),cents,minimum(w.currency))
    req=insert('IL Payout Request',wallet=w.name,method=m.name,request_key=key,amount_minor=cents,currency=w.currency,
               region='Local' if w.country=='Sri Lanka' else 'International',status='Pending')
    post(w,'reserve:'+req.name,'Reserve',-cents,cents,payout=req.name)
    audit('Payout requested',req.name)
    return {'name':req.name,'status':'Pending'}

@frappe.whitelist(methods=['POST'])
def update_payout(request,status,reference='',reason='',receipt=None):
    owner()
    req=frappe.get_doc('IL Payout Request',request);w=locked_wallet(req.wallet);req.reload()
    if w.owner_user==frappe.session.user:frappe.throw('Self-settlement is not permitted',frappe.PermissionError)
    if req.status==status:
        if (req.transaction_reference or '')!=reference or (req.reason or '')!=reason or (req.receipt or '')!=(receipt or ''):frappe.throw('Already processed with different details')
        return {'status':status}
    da,dh=transition(req.status,status,int(req.amount_minor),reference,reason)
    if receipt:
        f=frappe.get_doc('File',receipt)
        if not f.is_private or f.attached_to_doctype!='IL Payout Request' or f.attached_to_name!=req.name:
            frappe.throw('Receipt must be a private attachment to this payout',frappe.PermissionError)
    if status=='Completed' and frappe.db.exists('IL Payout Request',{'transaction_reference':reference,'status':'Completed','name':['!=',req.name]}):frappe.throw('Transfer reference already used')
    if status=='Completed' and w.available_minor<0:frappe.throw('Reconcile refunded earnings before completing this payout')
    if len(reference)>140:frappe.throw('Transfer reference is too long')
    req.update({'status':status,'transaction_reference':str(reference),'settlement_key':hashlib.sha256(reference.encode()).hexdigest() if status=='Completed' else None,'reason':str(reason)[:1000],
                'receipt':receipt,'processed_by':frappe.session.user,'completed_at':now_datetime() if status=='Completed' else None});saved(req)
    if da or dh:post(w,status.lower()+':'+req.name,'Release' if status=='Rejected' else 'Payout',da,dh,payout=req.name,reference=reference,reason=reason)
    audit('Payout '+status,req.name,reason)
    return {'status':status}

@frappe.whitelist()
def admin_queue(region='Local',page=0):
    owner()
    if region not in ('Local','International'):frappe.throw('Invalid region')
    return {'requests':frappe.get_all('IL Payout Request',filters={'region':region,'status':['in',['Pending','Processing']]},fields=['name','wallet','method','amount_minor','currency','status','creation'],order_by='creation asc',start=max(0,min(int(page),10000))*50,limit_page_length=50),
            'methods':frappe.get_all('IL Payout Method',filters={'status':'Pending','country':['=' if region=='Local' else '!=','Sri Lanka']},fields=['name','wallet','kind','masked_label','country','creation'],limit_page_length=50)}

@frappe.whitelist(methods=['POST'])
def reveal_method(method):
    owner();m=frappe.get_doc('IL Payout Method',method)
    audit('Sensitive method viewed',m.name)
    return json.loads(m.get_password('secret_details'))

@frappe.whitelist(methods=['POST'])
def export_local(requests):
    owner()
    names=json.loads(requests) if isinstance(requests,str) else requests
    if not isinstance(names,list) or not 1<=len(names)<=200 or len(set(names))!=len(names):frappe.throw('Select 1–200 unique payouts')
    rows=[]
    for name in names:
        p=frappe.get_doc('IL Payout Request',name)
        if p.region!='Local' or p.currency!='LKR' or p.status!='Processing':frappe.throw('Only Processing local payouts can be exported')
        m=frappe.get_doc('IL Payout Method',p.method)
        if m.wallet!=p.wallet or m.status not in ('Approved','Superseded'):frappe.throw('Invalid frozen payout method')
        d=json.loads(m.get_password('secret_details'))
        if d['kind']!='Local Bank':frappe.throw('Bank payout required')
        rows.append([p.name,d['bank'],d['branch'],d['holder'],"'"+d['account'],f'{p.amount_minor/100:.2f}','LKR'])
    stream=io.StringIO();writer=csv.writer(stream)
    writer.writerow(['Payout reference','Bank name','Branch','Account holder','Account number (text)','Amount','Currency'])
    for row in rows:writer.writerow([csv_cell(v) for v in row])
    audit('Local payouts exported',','.join(names)[:140],f'{len(rows)} records; generic CSV, not bank-certified')
    frappe.local.response.filename='sisu-local-payouts.csv';frappe.local.response.filecontent='\ufeff'+stream.getvalue();frappe.local.response.type='download'

def record_earning(invoice):
    """Internal settlement hook; caller already validated the gateway and locked invoice.

    A beneficiary split must have been frozen before checkout. Never infer earnings
    for legacy invoices or credit both institute and teacher for the same payment.
    """
    if not invoice.get('payout_wallet'):return
    w=locked_wallet(invoice.payout_wallet)
    if invoice.status!='Paid' or invoice.get('currency')!=w.currency:frappe.throw('Settlement currency mismatch')
    earned=int(invoice.get('beneficiary_minor') or 0);platform=int(invoice.get('platform_minor') or 0)
    if earned<0 or platform<0 or earned+platform!=minor(invoice.amount):frappe.throw('Invoice split does not reconcile')
    if w.beneficiary=='Institute' and w.institute!=invoice.institute:frappe.throw('Wrong institute beneficiary')
    if earned:post(w,'earning:'+invoice.name,'Earning',earned,0,invoice=invoice.name,reference=invoice.payment_id)

def reverse_earning(invoice,amount,event_reference):
    """Internal verified-refund integration only. Negative balance blocks new payouts."""
    w=locked_wallet(invoice.payout_wallet);value=minor(amount)
    earning=frappe.db.get_value('IL Wallet Transaction',{'event_key':'earning:'+invoice.name},'available_delta')
    if not earning or value<=0:frappe.throw('Original earning required')
    key='reversal:'+hashlib.sha256((invoice.name+':'+event_reference).encode()).hexdigest()
    if frappe.db.exists('IL Wallet Transaction',{'event_key':key}):return
    reversed_total=frappe.db.sql("SELECT COALESCE(SUM(-available_delta),0) FROM `tabIL Wallet Transaction` WHERE invoice=%s AND kind='Reversal'",(invoice.name,))[0][0]
    if value+reversed_total>earning:frappe.throw('Refund exceeds credited earning')
    post(w,key,'Reversal',-value,0,invoice=invoice.name,reference=event_reference)
