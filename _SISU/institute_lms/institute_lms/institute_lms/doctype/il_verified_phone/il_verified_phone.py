from frappe.model.document import Document
import frappe

class ILVerifiedPhone(Document):
    def validate(self):
        if not self.flags.community_service: frappe.throw("Use the profile API", frappe.PermissionError)
