"""SOUL server proxy. Authenticated, per-site secrets, no tools or record retrieval."""
import hashlib
import hmac
import json
import time
import requests
import frappe
from frappe.utils import get_url
from .api import identity, require_role
from .soul_contract import clean_request, valid_model, instructions, output_text

SAFE_REPLY = 'I can help you find your way around the LMS. For something worrying or personal, please talk with a trusted adult or your teacher. If someone is in immediate danger, contact local emergency services.'

def settings_doc():
    return frappe.get_single('IL SOUL Settings')

def student_ready(member):
    # Unknown age/consent defaults to local guided help. Deployment review is not
    # represented as an ordinary portal toggle or inferred from a course name.
    return member.role != 'Student' or bool(
        frappe.conf.get('il_soul_student_ai_reviewed') and frappe.conf.get('il_soul_zdr_verified')
        and member.get('soul_ai_enabled'))

@frappe.whitelist(methods=['POST'])
def status():
    from .wallet import admin_actor
    member=frappe._dict(role='PlatformAdmin') if admin_actor() else identity()[1]
    doc = settings_doc()
    configured = bool(doc.get_password('api_key', raise_exception=False))
    return {'configured': configured, 'enabled': bool(doc.enabled),
            'available': bool(doc.enabled and configured and student_ready(member)),
            'model': doc.model if member.role == 'PlatformAdmin' else None,
            'student_reviewed': bool(frappe.conf.get('il_soul_student_ai_reviewed') and frappe.conf.get('il_soul_zdr_verified')) if member.role == 'PlatformAdmin' else None}

@frappe.whitelist(methods=['POST'])
def configure(api_key=None, model='gpt-4.1-mini', enabled=False, remove_key=False):
    from .wallet import owner
    owner()
    if not get_url().startswith('https://'):
        frappe.throw('Use your HTTPS institute site to save an API key.')
    try:
        model = valid_model(model)
    except ValueError as exc:
        frappe.throw(str(exc))
    if type(enabled) is not bool or type(remove_key) is not bool:
        frappe.throw('Invalid setting')
    if api_key and (not isinstance(api_key, str) or not api_key.startswith('sk-') or not 20 <= len(api_key) <= 512 or any(c.isspace() for c in api_key)):
        frappe.throw('Enter a valid OpenAI secret key.')
    doc = settings_doc()
    doc.model = model
    doc.enabled = int(enabled and not remove_key)
    if remove_key:
        from frappe.utils.password import remove_encrypted_password
        remove_encrypted_password('IL SOUL Settings', 'IL SOUL Settings', 'api_key')
        doc.api_key = ''
    elif api_key:
        doc.api_key = api_key
    if doc.enabled and not api_key and not doc.get_password('api_key', raise_exception=False):
        frappe.throw('Save an API key before enabling OpenAI chat.')
    doc.save(ignore_permissions=True)
    return {'saved': True}

def provider(path, key, body):
    try:
        r = requests.post('https://api.openai.com/v1/' + path,
            headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'},
            json=body, timeout=(5, 20), allow_redirects=False)
        if not r.ok:
            raise ValueError('Provider request failed')
        result = r.json()
        if not isinstance(result, dict):
            raise ValueError('Invalid provider response')
        return result
    except (requests.RequestException, ValueError):
        frappe.throw('SOUL is temporarily unavailable. Your administrator can check the OpenAI key, model access and usage limits.')

def moderated(key, text):
    result = provider('moderations', key, {'model': 'omni-moderation-latest', 'input': text})
    rows = result.get('results', [])
    if not rows or not isinstance(rows[0].get('flagged'), bool):
        frappe.throw('SOUL safety checks are temporarily unavailable. Please try later.')
    return rows[0]['flagged']

def reserve(user, site):
    # Atomic counters across workers; a failed request still consumes a slot.
    now = int(time.time())
    checks = [(f'il_soul:minute:{user}:{now//60}', 6, 120),
              (f'il_soul:day:{user}:{now//86400}', 50, 172800),
              (f'il_soul:site:{site}:{now//86400}', 500, 172800)]
    with frappe.cache.lock('il_soul:budget:'+site, timeout=5):
        for key, limit, _ in checks:
            if (frappe.cache.get_value(key) or 0) >= limit:
                frappe.throw('SOUL has reached its message limit. Guided help is still available; please try again later.')
        for key, _, ttl in checks:
            frappe.cache.set_value(key, (frappe.cache.get_value(key) or 0)+1, expires_in_sec=ttl)

@frappe.whitelist(methods=['POST'])
def chat(message, page='dashboard', language='en', history=None, consent=False):
    inst, member = identity()
    doc = settings_doc()
    if not doc.enabled or not student_ready(member):
        frappe.throw('OpenAI chat is not enabled for this account. You can still use SOUL guided help.', frappe.PermissionError)
    if consent is not True:
        frappe.throw('Review the OpenAI chat notice before sending a message.')
    try:
        history = json.loads(history) if isinstance(history, str) else history or []
        message, history, page, language = clean_request(message, history, page, language)
    except (ValueError, TypeError):
        frappe.throw('Use a short message and start a new conversation if this chat is full.')
    key = doc.get_password('api_key', raise_exception=False)
    if not key:
        frappe.throw('Your administrator has not connected OpenAI yet.')
    safety_id = hmac.new(str(frappe.conf.encryption_key).encode(),
        (inst.name+':'+frappe.session.user).encode(), hashlib.sha256).hexdigest()
    reserve(safety_id, inst.name)
    # No automatic retries: avoid double billing on an uncertain network result.
    if moderated(key, '\n'.join(x['content'] for x in history)+'\n'+message):
        return {'reply': SAFE_REPLY, 'mode': 'safety'}
    response = provider('responses', key, {'model': valid_model(doc.model or 'gpt-4.1-mini'),
        'instructions': instructions(member.role, page, language),
        'input': history+[{'role':'user','content':message}], 'store': False,
        'max_output_tokens': 600, 'safety_identifier': safety_id})
    try:
        reply = output_text(response)
    except ValueError as exc:
        frappe.throw(str(exc))
    return {'reply': SAFE_REPLY if moderated(key, reply) else reply, 'mode':'openai'}

@frappe.whitelist(methods=['POST'])
def test_connection():
    from .wallet import owner
    from .api import institute
    owner()
    inst=institute()
    doc = settings_doc()
    key = doc.get_password('api_key', raise_exception=False)
    if not key:
        frappe.throw('Save an API key first.')
    reserve('admin-test:'+inst.name, inst.name)
    result = provider('responses', key, {'model':valid_model(doc.model or 'gpt-4.1-mini'),
        'input':'Reply with the single word Connected.', 'store':False, 'max_output_tokens':32})
    if result.get('status') != 'completed':
        frappe.throw('The model did not finish the connection check.')
    moderated(key, 'Connection check.')
    return {'connected':True}
