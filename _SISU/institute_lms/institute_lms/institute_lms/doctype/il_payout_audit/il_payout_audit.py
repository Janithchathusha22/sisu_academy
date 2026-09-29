from frappe.model.document import Document
import frappe

class ILPayoutAudit(Document):
    def validate(self):
        if not self.flags.wallet_service: frappe.throw("Use the authorized wallet API", frappe.PermissionError)
        if not self.is_new(): frappe.throw("Ledger entries are immutable")
    def on_trash(self):
        frappe.throw("Financial records cannot be deleted")
