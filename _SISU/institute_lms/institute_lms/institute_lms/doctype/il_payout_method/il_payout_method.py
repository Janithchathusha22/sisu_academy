from frappe.model.document import Document
import frappe

class ILPayoutMethod(Document):
    def validate(self):
        if not self.flags.wallet_service: frappe.throw("Use the authorized wallet API", frappe.PermissionError)
    def on_trash(self):
        frappe.throw("Financial records cannot be deleted")
