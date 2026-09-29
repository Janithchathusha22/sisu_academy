"""Thirty-day promotional retention; never deletes invoices or learning records."""
from datetime import timedelta
import frappe
from frappe.utils import now_datetime


def purge_expired_promotions():
    cutoff = now_datetime() - timedelta(days=30)
    # Creation is the immutable publication timestamp. Editing cannot extend TTL.
    # Bounded batches prevent a large backfill from monopolising the scheduler.
    for doctype in ("IL News",):
        names = frappe.get_all(doctype, filters={"creation": ["<=", cutoff]}, pluck="name", limit_page_length=500, order_by="creation asc")
        for name in names:
            frappe.delete_doc(doctype, name, ignore_permissions=True)
    # Shared File records are not removed: other posts/profiles may still use them.
