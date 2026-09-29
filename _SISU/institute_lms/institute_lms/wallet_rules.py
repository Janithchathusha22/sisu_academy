"""Money is integer minor units. No floating-point arithmetic or implicit FX."""
from decimal import Decimal, InvalidOperation
import re

def minor(value):
    try:
        d=Decimal(str(value))
        if not d.is_finite() or d<0 or d>Decimal('9999999.99') or d.as_tuple().exponent < -2:
            raise ValueError('Use a non-negative amount with at most two decimal places')
        return int(d*100)
    except (InvalidOperation, TypeError):
        raise ValueError('Invalid amount')

def reserve(available, held, amount, minimum):
    if any(type(v) is not int for v in (available,held,amount,minimum)):
        raise ValueError('Amounts must use integer minor units')
    if minimum<=0 or amount<=0 or amount<minimum or amount>available or held<0:
        raise ValueError('Minimum payout not met or insufficient available funds')
    return available-amount,held+amount

def transition(old,new,amount,reference='',reason=''):
    if new not in {'Pending':{'Processing','Rejected'},'Processing':{'Completed','Rejected'}}.get(old,set()):
        raise ValueError('Invalid payout status transition')
    if new=='Completed' and not reference.strip(): raise ValueError('A transfer reference is required')
    if new=='Rejected' and not reason.strip(): raise ValueError('A rejection reason is required')
    return (amount,-amount) if new=='Rejected' else (0,-amount) if new=='Completed' else (0,0)

def payout_details(data):
    if not isinstance(data,dict): raise ValueError('Payout details required')
    kind=data.get('kind'); country=str(data.get('country','')).strip()
    allowed={
      'Local Bank':('bank','branch','holder','account'),
      'Wise':('email',), 'Payoneer':('payoneer_id',),
      'SWIFT / IBAN':('bank','holder','swift','iban')}
    if kind not in allowed or not country: raise ValueError('Select a method and country')
    if (kind=='Local Bank') != (country=='Sri Lanka'): raise ValueError('Choose a method suitable for the payout country')
    clean={'kind':kind,'country':country[:80]}
    for key in allowed[kind]:
        value=str(data.get(key,'')).strip()
        if not value or len(value)>140 or any(ord(c)<32 for c in value): raise ValueError('Invalid '+key)
        clean[key]=value
    if kind=='Wise' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',clean['email']): raise ValueError('Invalid Wise email')
    if kind=='SWIFT / IBAN':
        clean['swift']=clean['swift'].upper();clean['iban']=clean['iban'].replace(' ','').upper()
        if not re.fullmatch(r'[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?',clean['swift']): raise ValueError('Invalid SWIFT/BIC')
        if not re.fullmatch(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}',clean['iban']): raise ValueError('Invalid IBAN')
        rearranged=clean['iban'][4:]+clean['iban'][:4]
        if int(''.join(str(ord(c)-55) if c.isalpha() else c for c in rearranged))%97!=1: raise ValueError('IBAN checksum failed')
    return clean

def class_quote(class_minor, platform_minor=100, school=False):
    if any(type(v)is not int or v<0 for v in (class_minor,platform_minor)): raise ValueError('Invalid fee')
    return {'class_minor':0 if school else class_minor,'platform_minor':0 if school else platform_minor,
            'total_minor':0 if school else class_minor+platform_minor}

def csv_cell(value):
    text=str(value or '').replace('\r',' ').replace('\n',' ')
    return "'"+text if text.lstrip().startswith(('=','+','-','@')) or text[:1]=='\t' else text
