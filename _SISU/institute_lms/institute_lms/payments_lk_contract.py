"""Pure validation helpers for Payments.lk's documented v1 contract.

Reference: https://payments.lk/developers/api (reviewed 2026-09-23).
These checks do not replace deployment and merchant sandbox acceptance tests.
"""
import hashlib
import hmac
import re
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse


def amount_cents(amount):
    try:
        value = Decimal(str(amount)) * 100
        if not value.is_finite() or value != value.to_integral_value() or not 1000 <= value <= 100000000:
            raise ValueError("Payment must be between LKR 10 and LKR 1,000,000 with at most two decimal places")
        return int(value)
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid payment amount") from None


def verify_signature(raw, header, secret, now=None, tolerance=300):
    if not isinstance(raw, bytes) or not isinstance(secret, str) or not secret:
        return False
    timestamps, signatures = [], []
    for part in str(header or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "t" and re.fullmatch(r"\d{1,12}", value):
            timestamps.append(value)
        if key == "v1" and re.fullmatch(r"[0-9a-f]{64}", value):
            signatures.append(value)
    if len(timestamps) != 1:
        return False
    timestamp = int(timestamps[0])
    if abs((time.time() if now is None else now) - timestamp) > tolerance:
        return False
    expected = hmac.new(secret.encode(), str(timestamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, signature) for signature in signatures)


def hosted_url(value):
    try:
        u = urlparse(value)
        return isinstance(value, str) and u.scheme == "https" and u.hostname == "payments.lk" and not u.username and not u.password and u.port in (None, 443) and re.fullmatch(r"/(?:si/|ta/)?checkout/chk_[a-zA-Z0-9]+", u.path) is not None
    except (ValueError, TypeError, AttributeError):
        return False


def valid_payment(payment, invoice, mode):
    if not isinstance(payment, dict):
        return False
    try:
        return (payment.get("object") == "payment" and payment.get("status") == "succeeded"
                and payment.get("mode") == mode and payment.get("currency") == "LKR"
                and type(payment.get("amountCents")) is int
                and payment["amountCents"] == amount_cents(invoice["amount"])
                and payment.get("reference") == invoice["name"]
                and bool(invoice.get("gateway_checkout_id"))
                and payment.get("checkoutId") == invoice["gateway_checkout_id"]
                and re.fullmatch(r"pay_[a-zA-Z0-9]{24}", str(payment.get("id", ""))) is not None)
    except (ValueError, KeyError):
        return False
