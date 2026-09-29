"""Private profile validation, independent of public directory records."""
import re
from datetime import date

FIELDS=('date_of_birth','gender','gender_description','contact_phone','city','address','guardian_name','guardian_relationship','guardian_phone','guardian_email','guardian_permission','whatsapp_phone','whatsapp_opt_in','notification_language')

def age_on(value,today=None):
    if not value:return None
    today=today or date.today()
    try:born=date.fromisoformat(str(value))
    except ValueError:raise ValueError('Enter a valid birthday')
    age=today.year-born.year-((today.month,today.day)<(born.month,born.day))
    if born>today or age>120:raise ValueError('Enter a realistic birthday, not a future date')
    return age

def normalize(data,kind,today=None):
    result={k:str(data.get(k) or '').strip() for k in FIELDS}
    for key in ('guardian_permission','whatsapp_opt_in'):
        if data.get(key) not in (None,False,True,0,1):raise ValueError('Invalid consent preference')
        result[key]=int(bool(data.get(key)))
    age=age_on(result['date_of_birth'],today)
    if kind=='Student' and age is None:raise ValueError('Add your birthday so we can show the right guardian options')
    if result['gender'] not in ('','Female','Male','Non-binary','Self-described','Prefer not to say'):raise ValueError('Choose a gender option')
    if result['gender']!='Self-described':result['gender_description']=''
    for key in ('contact_phone','guardian_phone','whatsapp_phone'):
        if result[key] and not re.fullmatch(r'\+[1-9][0-9]{7,14}',result[key]):raise ValueError('Use phone numbers with country code, e.g. +94771234567')
    if result['guardian_email'] and not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',result['guardian_email']):raise ValueError('Enter a valid guardian email')
    for key,value in result.items():
        if isinstance(value,str) and len(value)>(500 if key=='address' else 254):raise ValueError('Contact information is too long')
    if kind=='Student' and age<16:
        if not all(result[k] for k in ('guardian_name','guardian_relationship','guardian_phone')):raise ValueError('Students under 16 need a guardian name, relationship and phone')
        if result['whatsapp_opt_in'] and (not result['guardian_permission'] or result['whatsapp_phone']!=result['guardian_phone']):raise ValueError('Under-16 WhatsApp updates require the guardian number and their permission')
    if result['whatsapp_opt_in'] and not result['whatsapp_phone']:raise ValueError('Add a WhatsApp number first')
    if result['notification_language'] not in ('en','si','ta'):raise ValueError('Choose a supported notification language')
    result['date_of_birth']=result['date_of_birth'] or None
    return result

def guardian_updates_without_otp(data,kind,today=None):
    """Only an under-16 student's permitted guardian contact skips phone OTP."""
    if kind!='Student':return False
    try:
        values=normalize(data,kind,today)
        return (age_on(values['date_of_birth'],today)<16 and bool(values['whatsapp_opt_in'])
                and bool(values['guardian_permission']) and bool(values['guardian_phone'])
                and values['whatsapp_phone']==values['guardian_phone'])
    except (ValueError,TypeError):return False
