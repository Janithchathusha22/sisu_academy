"""Provider-only social contact information."""
from .domain import safe_url

def provider_socials(kind,value):
    if kind not in ('Teacher','Institute'):return {}
    if not isinstance(value,dict):raise ValueError('Invalid social links')
    result={}
    for key in ('facebook','instagram','twitter','youtube','linkedin','tiktok'):
        if value.get(key):
            url=str(value[key]).strip()
            if len(url)>500:raise ValueError('Social links must be 500 characters or fewer')
            result[key]=safe_url(url)
    return result
