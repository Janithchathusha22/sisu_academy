import frappe
from frappe.model.document import Document
class ILProviderUpdate(Document):
    def validate(self):
        if not self.flags.community_service: frappe.throw('Use the profile update API', frappe.PermissionError)
    def on_trash(self):
        if not frappe.flags.get('il_provider_update_purge'): frappe.throw('Use scheduled expiry', frappe.PermissionError)
