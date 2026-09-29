"""Pure domain rules, shared by API and independently testable."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import md5
import hmac
import re
import regex
from urllib.parse import urlparse, parse_qs


def text_length(value):
    return len(regex.findall(r"\X", value or ""))


def limited(value, maximum, label):
    value = (value or "").strip()
    if text_length(value) > maximum:
        raise ValueError(f"{label} must be {maximum} characters or fewer")
    return value


def institute_code(value):
    value = (value or "").strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,11}", value):
        raise ValueError("Institute code must be 2–12 letters/numbers, starting with a letter")
    return value


def money(value):
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"))
        if not result.is_finite() or result < 0:
            raise ValueError("Amount must be a finite positive value or zero")
        return result
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc


def billing_total(active_students, base_fee):
    return money(base_fee) + max(0, int(active_students) - 500) * Decimal("50.00")


def access_decision(enrollment, invoices, today=None):
    today = today or date.today()
    if not enrollment or not enrollment.get("active"):
        return False, "Not enrolled"
    override = enrollment.get("access_override", "Automatic")
    if override == "Closed":
        return False, "Access closed by your institute"
    if override == "Open":
        return True, "Opened by your institute"
    if money(enrollment.get("fee", 0)) == 0:
        return True, "Free classroom"
    grace = enrollment.get("grace_until")
    if grace and today <= date.fromisoformat(str(grace)[:10]):
        return True, "Grace period"
    if not invoices:
        return False, "Payment plan pending"
    settled = [i for i in invoices if i.get("status") == "Paid"]
    unpaid_due = [i for i in invoices if i.get("status") != "Paid"
                  and date.fromisoformat(str(i["due_date"])[:10]) <= today]
    if unpaid_due:
        return False, "Payment due"
    if not settled:
        return False, "First payment required"
    return True, "Payment up to date"


def safe_url(value, optional=True):
    if not value and optional:
        return ""
    parsed = urlparse(value or "")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a valid HTTPS URL")
    return value


def youtube_id(value):
    if re.fullmatch(r"[\w-]{11}", value or ""):
        return value
    parsed = urlparse(value or "")
    if parsed.scheme != "https":
        raise ValueError("Use a YouTube HTTPS URL or 11-character video ID")
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        result = parsed.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com", "www.youtube-nocookie.com"):
        result = parse_qs(parsed.query).get("v", [""])[0]
        if not result and parsed.path.startswith(("/embed/", "/live/", "/shorts/")):
            result = parsed.path.split("/")[2]
    else:
        result = ""
    if not re.fullmatch(r"[\w-]{11}", result):
        raise ValueError("Invalid YouTube video")
    return result


def checksum(*values):
    # MD5 is required by the PayHere protocol; never used for passwords.
    return md5("".join(str(v) for v in values).encode()).hexdigest().upper()


def checkout_hash(merchant, invoice, amount, secret):
    return checksum(merchant, invoice, f"{money(amount):.2f}", "LKR", checksum(secret))


def verify_payment(payload, merchant, secret, amount):
    required = ("merchant_id", "order_id", "payhere_amount", "payhere_currency", "status_code", "md5sig", "payment_id")
    if any(not payload.get(k) for k in required):
        return False
    expected = checksum(payload["merchant_id"], payload["order_id"], payload["payhere_amount"],
                        payload["payhere_currency"], payload["status_code"], checksum(secret))
    try:
        return (hmac.compare_digest(expected, payload["md5sig"].upper())
                and payload["merchant_id"] == merchant and payload["payhere_currency"] == "LKR"
                and money(payload["payhere_amount"]) == money(amount))
    except ValueError:
        return False
