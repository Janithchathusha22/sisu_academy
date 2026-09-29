from frappe.model.document import Document
import frappe

class ILProfileRelationship(Document):
    def validate(self):
        if not self.flags.community_service: frappe.throw("Use the profile API", frappe.PermissionError)
