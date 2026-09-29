"""Registration is an approval request, never a client-selected privilege grant."""
import re

ROLES = {'Institute', 'Individual Teacher', 'Student', 'Super Admin'}

def registration_details(data, owner_email):
    if not isinstance(data, dict): raise ValueError('Invalid registration')
    role = data.get('kind')
    email = str(data.get('email', '')).strip().lower()
    if role not in ROLES: raise ValueError('Choose an account type')
    if len(email)>254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', email): raise ValueError('Enter a valid email')
    if role == 'Super Admin' and (not owner_email or email != owner_email.strip().lower()):
        raise PermissionError('This address is not eligible for owner access')
    result = {'kind': role, 'email': email}
    for key in ('full_name','organization','organization_type','country','timezone','language','subject','invite','website','job','phone','backup_name','backup_email','username','qualifications','tagline','privacy_policy_url','privacy_policy_version','consented_at'):
        value = str(data.get(key, '')).strip()
        if len(value)>254 or any(c in value for c in '\x00\r\n'): raise ValueError('Invalid registration field')
        result[key] = value
    if role != 'Super Admin' and not result['full_name']: raise ValueError('Enter your full name')
    if role == 'Institute':
        if not all(result[k] for k in ('organization','country','job','phone','backup_name','backup_email')): raise ValueError('Complete the institute and recovery contact details')
        if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',result['backup_email']): raise ValueError('Invalid recovery email')
        if result['backup_email'].lower()==email: raise ValueError('Use a separate recovery contact')
    return result
