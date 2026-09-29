from frappe.model.document import Document
import frappe

class ILTeacherInvitation(Document):
    def validate(self):
        if not self.flags.contact_service: frappe.throw("Use the contact service", frappe.PermissionError)
