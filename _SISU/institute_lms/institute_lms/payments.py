import frappe
from frappe.utils import now_datetime, get_url
from .api import identity, scoped, payload
from .domain import checkout_hash, verify_payment, money


@frappe.whitelist(methods=["POST"])
def checkout(invoice: str, customer: dict | str):
    provider = frappe.conf.get("il_payment_provider", "payments_lk")
    if provider == "payments_lk":
        from .payments_lk import checkout as hosted_checkout
        return hosted_checkout(invoice)
    if provider != "payhere":
        frappe.throw("Unknown payment provider")
    inst, member = identity()
    doc = scoped("IL Invoice", invoice, inst)
    if doc.student != member.name:
        frappe.throw("Only the invoiced student can initiate payment", frappe.PermissionError)
    if doc.status == "Paid":
        frappe.throw("This invoice is already paid")
    merchant = frappe.conf.get("il_payhere_merchant_id")
    secret = frappe.conf.get("il_payhere_secret")
    if not merchant or not secret:
        frappe.throw("Payments have not been configured by your institute")
    customer = payload(customer)
    for key in ("first_name", "last_name", "phone", "address", "city"):
        if not customer.get(key) or len(str(customer[key])) > 200:
            frappe.throw(f"A valid {key.replace('_', ' ')} is required")
    fields = {k: customer[k] for k in ("first_name", "last_name", "phone", "address", "city")}
    fields.update({"merchant_id": merchant, "order_id": doc.name, "amount": f"{money(doc.amount):.2f}",
        "currency": "LKR", "items": f"Class installment {doc.installment}", "country": "Sri Lanka",
        "email": frappe.session.user, "return_url": get_url("/campus?payment=returned"),
        "cancel_url": get_url("/campus?payment=cancelled"),
        "notify_url": get_url("/api/method/institute_lms.payments.notify"),
        "hash": checkout_hash(merchant, doc.name, doc.amount, secret)})
    action = "https://sandbox.payhere.lk/pay/checkout" if frappe.conf.get("il_payhere_sandbox", True) else "https://www.payhere.lk/pay/checkout"
    return {"action": action, "fields": fields}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def notify(**kwargs):
    if frappe.conf.get("il_payment_provider", "payments_lk") != "payhere":
        frappe.throw("This payment provider is not enabled", frappe.PermissionError)
    data = dict(frappe.form_dict)
    merchant, secret = frappe.conf.get("il_payhere_merchant_id"), frappe.conf.get("il_payhere_secret")
    if not merchant or not secret:
        frappe.throw("Payments unavailable", frappe.PermissionError)
    name = data.get("order_id")
    # Serializes simultaneous/replayed callbacks for the same invoice.
    rows = frappe.db.sql("SELECT name FROM `tabIL Invoice` WHERE name=%s FOR UPDATE", (name,))
    if not rows:
        frappe.throw("Invalid payment notification", frappe.PermissionError)
    doc = frappe.get_doc("IL Invoice", name)
    if not verify_payment(data, str(merchant), secret, doc.amount):
        frappe.throw("Invalid payment notification", frappe.PermissionError)
    if doc.status == "Paid":
        return {"accepted": True}  # Settled invoices are never downgraded by late failure callbacks.
    if str(data["status_code"]) != "2":
        doc.db_set("gateway_status", str(data["status_code"]), update_modified=False)
        return {"accepted": True}
    if frappe.db.exists("IL Invoice", {"payment_id": data["payment_id"], "name": ["!=", doc.name]}):
        frappe.throw("Payment reference already used", frappe.PermissionError)
    doc.update({"status": "Paid", "paid_at": now_datetime(), "payment_id": data["payment_id"],
                "receipt_number": f"RC-{doc.name}", "gateway_status": "2"})
    doc.save(ignore_permissions=True)
    from .wallet import record_earning
    record_earning(doc)
    from .notifications import queue
    queue(doc.institute, doc.student, f"payment:{doc.name}",
          f"Payment received: LKR {money(doc.amount):.2f}. Receipt {doc.receipt_number}.")
    return {"accepted": True}
