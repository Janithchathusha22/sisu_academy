import frappe
from frappe.model.document import Document

class ILProductEntitlement(Document):
    def validate(self):
        if not self.flags.pricing_service: frappe.throw('Use the authorized service API', frappe.PermissionError)
    def on_trash(self):
        frappe.throw('Financial and assessment records must be retained', frappe.PermissionError)
