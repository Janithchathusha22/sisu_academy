import frappe
from frappe.utils import today
from .api import identity, require_role


def daily():
    frappe.db.sql("UPDATE `tabIL Invoice` SET status='Overdue' WHERE status='Unpaid' AND due_date < %s", (today(),))
    # Legacy 500-seat / LKR 50 tariffs are retired. Retain existing financial
    # records; recurring collection needs the owner-assigned quote integration.



@frappe.whitelist()
def summary():
    inst, member = identity()
    require_role(member, "Admin")
    count = frappe.db.count("IL Member", {"institute": inst.name, "role": "Student", "active": 1})
    return {"active_students": count, "pricing": "Owner assigned; shown at checkout",
        "history": frappe.get_all("IL Institute Bill", filters={"institute": inst.name}, fields=["*"], limit_page_length=24, order_by="period desc")}
