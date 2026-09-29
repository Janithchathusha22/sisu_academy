"""Durable notification outbox. No provider tokens or payloads enter client responses."""
from hashlib import sha256
from datetime import timedelta
import requests
import frappe
from frappe.utils import now_datetime


def whatsapp_allowed(member):
    if not member.active or not member.whatsapp_opt_in or not member.phone:return False
    if member.role=='Student':
        from .private_contact_rules import normalize,guardian_updates_without_otp
        name=frappe.db.get_value('IL Private Contact',{'user':member.user},'name')
        if not name:return False
        values=frappe.get_doc('IL Private Contact',name).as_dict()
        values.update(whatsapp_phone=member.phone,whatsapp_opt_in=True)
        try:normalize(values,'Student')
        except ValueError:return False
        if guardian_updates_without_otp(values,'Student'):return True
    return bool(frappe.db.exists('IL Verified Phone',{'user':member.user,'phone':member.phone}))


def queue(institute, recipient, event_key, body):
    member = frappe.get_doc("IL Member", recipient)
    for channel in ('WhatsApp','Email'):
        suffix='' if channel=='WhatsApp' else ':Email'
        key=sha256(f'{event_key}:{recipient}{suffix}'.encode()).hexdigest()
        if frappe.db.exists('IL Notification',{'event_key':key}):continue
        enabled=member.active and (whatsapp_allowed(member) if channel=='WhatsApp' else member.get('contact_email_verified') and member.get('email_opt_in') and member.get('contact_email'))
        frappe.get_doc({'doctype':'IL Notification','institute':institute,'recipient':recipient,'channel':channel,
            'event_key':key,'body':body[:1000],'status':'Queued' if enabled else 'Skipped','attempts':0,'next_attempt':now_datetime()}).insert(ignore_permissions=True)


def classroom_event(room, event_key, body):
    for member in frappe.get_all("IL Enrollment", filters={"classroom": room.name, "active": 1}, pluck="student", limit_page_length=0):
        queue(room.institute, member, event_key, f"{room.title} — {body}")


def dispatch():
    token = frappe.conf.get("il_whatsapp_token")
    phone_id = frappe.conf.get("il_whatsapp_phone_id")
    version = frappe.conf.get("il_whatsapp_graph_version")
    templates = frappe.conf.get("il_whatsapp_templates") or {}
    if not all((token, phone_id, version, templates)):
        return  # Remain queued until configuration exists.
    with frappe.cache.lock("il_whatsapp_dispatch", timeout=300, blocking_timeout=1):
        for name in frappe.get_all("IL Notification", filters={"channel":"WhatsApp", "status": "Queued", "next_attempt": ["<=", now_datetime()]},
                                   pluck="name", limit_page_length=20, order_by="creation asc"):
            doc = frappe.get_doc("IL Notification", name)
            if doc.channel == 'Email':
                continue
            member = frappe.get_doc("IL Member", doc.recipient)
            if not whatsapp_allowed(member):
                doc.db_set("status", "Skipped")
                continue
            template = templates.get(member.language)
            if not template:
                doc.db_set("last_error", "No approved template configured for recipient language")
                continue
            # A worker crash or ambiguous network result must not blindly resend.
            doc.status = "Review"
            doc.attempts += 1
            doc.save(ignore_permissions=True)
            frappe.db.commit()

            try:
                response = requests.post(f"https://graph.facebook.com/{version}/{phone_id}/messages",
                    headers={"Authorization": f"Bearer {token}"}, timeout=(5, 15),
                    json={"messaging_product": "whatsapp", "to": member.phone.lstrip("+"), "type": "template",
                          "template": {"name": template["name"], "language": {"code": template["language"]},
                          "components": [{"type": "body", "parameters": [{"type": "text", "text": doc.body}]}]}})
                if response.ok:
                    doc.status = "Accepted"
                    doc.provider_id = response.json()["messages"][0]["id"]
                    doc.last_error = ""
                elif response.status_code == 429:
                    doc.status = "Queued" if doc.attempts < 5 else "Failed"
                    doc.next_attempt = now_datetime() + timedelta(minutes=2 ** doc.attempts)
                    doc.last_error = "Provider rate limit"
                else:
                    doc.status = "Failed"
                    doc.last_error = f"Provider rejected request (HTTP {response.status_code})"
            except (requests.RequestException, ValueError, KeyError):
                doc.status = "Review"
                doc.last_error = "Delivery outcome uncertain; reconcile in Meta before retrying"
            doc.save(ignore_permissions=True)
            frappe.db.commit()


def dispatch_email():
    """Transfer verified/opted-in messages to Frappe's durable Email Queue."""
    from html import escape
    if not frappe.db.exists('Email Account',{'enable_outgoing':1}):return
    with frappe.cache.lock('il_email_dispatch',timeout=300,blocking_timeout=1):
        for name in frappe.get_all('IL Notification',filters={'channel':'Email','status':'Queued'},pluck='name',limit_page_length=50,order_by='creation asc'):
            frappe.db.sql('SELECT name FROM `tabIL Notification` WHERE name=%s FOR UPDATE',(name,))
            doc=frappe.get_doc('IL Notification',name);member=frappe.get_doc('IL Member',doc.recipient)
            if not member.active or not member.get('contact_email_verified') or not member.get('email_opt_in') or not member.get('contact_email'):
                doc.db_set('status','Skipped');frappe.db.commit();continue
            # Email Queue creation and outbox acceptance share the DB transaction.
            frappe.sendmail(recipients=[member.contact_email],subject='Your Sisu class update',message='<p>'+escape(doc.body).replace('\n','<br>')+'</p><p>Open your institute LMS for the current schedule and class access.</p>',delayed=True,reference_doctype='IL Notification',reference_name=doc.name)
            doc.status='Accepted';doc.attempts+=1;doc.save(ignore_permissions=True);frappe.db.commit()
