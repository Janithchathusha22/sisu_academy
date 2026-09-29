"""Owner-only contracts; immutable checkout quotes and explicit expiring entitlements.

Assignments are not payments. Only a verified settlement integration or an audited
owner grant can enable a premium product. No public catalogue prices exist.
"""
import json
from datetime import timedelta
import frappe
from frappe.utils import now_datetime, get_datetime
from .wallet import owner, signed_in, audit
from .pricing_rules import PRODUCTS, CURRENCIES, calculate

def save(doc):
    doc.flags.pricing_service = True
    return doc.save(ignore_permissions=True)

def current(user, product):
    names = frappe.get_all('IL Price Assignment', filters={'customer':user,'product':product,'active':1}, pluck='name', limit_page_length=2)
    if len(names) != 1: frappe.throw('Your price has not been assigned. Contact your administrator.')
    return frappe.get_doc('IL Price Assignment', names[0])

def usage(contract):
    if not contract.institute: return 1
    return frappe.db.count('IL Member', {'institute':contract.institute,'role':'Student','active':1})

def amount(contract):
    return calculate(contract.base_minor,contract.included_units,contract.unit_minor,usage(contract),contract.discount_bps,contract.tax_bps)

@frappe.whitelist(methods=['POST'])
def assign(data):
    owner()
    if isinstance(data,str): data=json.loads(data)
    customer=str(data.get('customer','')).strip()
    if not frappe.db.exists('User',{'name':customer,'enabled':1}) or customer=='Guest': frappe.throw('Select an enabled customer')
    kind=data.get('customer_kind'); product=data.get('product'); currency=data.get('currency')
    if kind not in ('Institute','Teacher','Student') or product not in PRODUCTS or currency not in CURRENCIES: frappe.throw('Invalid contract details')
    if data.get('period') not in ('Monthly','Yearly','Per payment'): frappe.throw('Choose a billing period')
    reason=str(data.get('reason','')).strip()
    if not reason or len(reason)>1000: frappe.throw('An audit reason is required (maximum 1,000 characters)')
    institute=data.get('institute') or None
    if institute and (kind!='Institute' or not frappe.db.exists('IL Institute',institute)): frappe.throw('Select a valid institute')
    if kind=='Institute' and not institute: frappe.throw('Institute pricing requires its workspace')
    values={k:data.get(k,0) for k in ('base_minor','included_units','unit_minor','discount_bps','tax_bps')}
    try: calculate(**values,units=0)
    except ValueError as e: frappe.throw(str(e))
    # Serialize all revisions for this customer, even when no contract exists yet.
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE',(customer,))
    previous=frappe.get_all('IL Price Assignment',filters={'customer':customer,'product':product,'active':1},pluck='name')
    for name in previous:
        old=frappe.get_doc('IL Price Assignment',name);old.active=0;save(old)
    doc=save(frappe.get_doc({'doctype':'IL Price Assignment','customer':customer,'customer_kind':kind,'product':product,
        'currency':currency,'period':data['period'],'institute':institute,'active':1,'reason':reason,'assigned_by':frappe.session.user,**values}))
    audit('Assign price',doc.name,reason)
    return {'name':doc.name}

@frappe.whitelist()
def assignments(page=0):
    owner()
    return frappe.get_all('IL Price Assignment',filters={'active':1},fields=['*'],order_by='creation desc',start=max(0,min(int(page),10000))*50,limit_page_length=50)

@frappe.whitelist(methods=['POST'])
def quote(product):
    signed_in()
    from .registration import limit
    limit('checkout-quote:'+frappe.session.user)
    if product not in PRODUCTS: frappe.throw('Unknown product')
    contract=current(frappe.session.user,product)
    # The browser supplies neither an amount nor an account identifier.
    result=amount(contract)
    doc=save(frappe.get_doc({'doctype':'IL Checkout Quote','customer':frappe.session.user,'assignment':contract.name,
        'currency':contract.currency,'product':product,'period':contract.period,'total_minor':result['total_minor'],
        'breakdown':json.dumps(result),'expires_at':now_datetime()+timedelta(minutes=15),'status':'Open'}))
    return {'name':doc.name,'product':doc.product,'currency':doc.currency,'period':doc.period,'expires_at':doc.expires_at,'breakdown':result,
        'payment_available':False}

@frappe.whitelist(methods=['POST'])
def classroom_price(classroom,amount_minor,reason):
    owner()
    from .pricing_rules import integer
    from decimal import Decimal
    if not str(reason).strip():frappe.throw('An audit reason is required')
    try:value=integer(amount_minor,'Class fee')
    except ValueError as e:frappe.throw(str(e))
    room=frappe.get_doc('IL Classroom',classroom)
    room.fee=Decimal(value)/100;room.save(ignore_permissions=True)
    audit('Assign classroom fee',room.name,f'LKR minor units {value}: {reason}')
    return {'saved':True,'currency':'LKR'}

def validate_quote(name,user):
    """Integration entry point: call inside a verified payment transaction, not from the browser."""
    q=frappe.get_doc('IL Checkout Quote',name)
    if q.customer!=user or q.status!='Open' or get_datetime(q.expires_at)<=now_datetime(): frappe.throw('Checkout quote expired or unavailable')
    return q

def has_entitlement(user,product):
    return bool(frappe.db.exists('IL Product Entitlement',{'customer':user,'product':product,'revoked':0,'expires_at':['>',now_datetime()]}))

@frappe.whitelist()
def entitlements():
    signed_in()
    return {p:has_entitlement(frappe.session.user,p) for p in PRODUCTS}

@frappe.whitelist(methods=['POST'])
def grant(customer,product,expires_at,reason):
    owner()
    if product not in PRODUCTS or not frappe.db.exists('User',{'name':customer,'enabled':1}): frappe.throw('Invalid customer or product')
    expiry=get_datetime(expires_at)
    if not now_datetime()<expiry<=now_datetime()+timedelta(days=366): frappe.throw('Choose an expiry within one year')
    if not str(reason).strip() or len(str(reason))>1000: frappe.throw('An audit reason is required')
    doc=save(frappe.get_doc({'doctype':'IL Product Entitlement','customer':customer,'product':product,'expires_at':expiry,
        'reason':str(reason),'granted_by':frappe.session.user,'revoked':0}))
    audit('Grant product',doc.name,reason)
    return {'name':doc.name}

@frappe.whitelist(methods=['POST'])
def revoke(name,reason):
    owner()
    if not str(reason).strip(): frappe.throw('An audit reason is required')
    doc=frappe.get_doc('IL Product Entitlement',name);doc.revoked=1;save(doc);audit('Revoke product',doc.name,reason)
    return {'revoked':True}
