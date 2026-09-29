import frappe
from .domain import institute_code


def validate_institute(doc, method=None):
    doc.code = institute_code(doc.code)
    if frappe.db.exists("IL Institute", {"name": ["!=", doc.name]}):
        frappe.throw("Provision a separate Frappe site for each institute to isolate all LMS data.")
    if not doc.is_new() and doc.has_value_changed("code"):
        frappe.throw("Institute codes cannot change after creation.")
