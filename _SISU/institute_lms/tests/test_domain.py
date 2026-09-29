import unittest
from datetime import date
from decimal import Decimal
from institute_lms.domain import (access_decision, billing_total, checksum, checkout_hash,
                                  verify_payment, institute_code, limited, text_length, youtube_id, money, safe_url)


class AccessRules(unittest.TestCase):
    def setUp(self):
        self.enrollment = dict(active=1, fee=6000, access_override="Automatic")
        self.today = date(2026, 9, 23)

    def check(self, invoices, **changes):
        return access_decision(dict(self.enrollment, **changes), invoices, self.today)[0]

    def test_no_enrollment(self):
        self.assertFalse(access_decision(None, [dict(status="Paid", due_date="2026-01-01")])[0])

    def test_unpaid_future_first_installment_is_locked(self):
        self.assertFalse(self.check([dict(status="Unpaid", due_date="2026-12-01")]))

    def test_first_paid_second_future(self):
        self.assertTrue(self.check([dict(status="Paid", due_date="2026-09-01"), dict(status="Unpaid", due_date="2026-10-01")]))

    def test_late_installment_blocks_without_cron(self):
        self.assertFalse(self.check([dict(status="Paid", due_date="2026-09-01"), dict(status="Unpaid", due_date="2026-09-23")]))

    def test_grace_boundary_and_expiry(self):
        self.assertTrue(self.check([], grace_until="2026-09-23"))
        self.assertFalse(self.check([], grace_until="2026-09-22"))

    def test_override_precedence(self):
        self.assertFalse(self.check([], access_override="Closed", grace_until="2026-12-01"))
        self.assertTrue(self.check([], access_override="Open"))
        self.assertFalse(self.check([], active=0, access_override="Open"))

    def test_free_classroom(self):
        self.assertTrue(self.check([], fee=0))


class PaymentRules(unittest.TestCase):
    def payload(self):
        p = dict(merchant_id="123",order_id="INV-1",payhere_amount="3000.00",payhere_currency="LKR",status_code="2",payment_id="P-1")
        p["md5sig"] = checksum("123","INV-1","3000.00","LKR","2",checksum("secret"))
        return p

    def test_valid(self):
        self.assertTrue(verify_payment(self.payload(), "123", "secret", Decimal("3000")))

    def test_tampered_amount(self):
        p = self.payload(); p["payhere_amount"] = "1.00"
        self.assertFalse(verify_payment(p, "123", "secret", 3000))

    def test_valid_signature_wrong_invoice_amount(self):
        self.assertFalse(verify_payment(self.payload(), "123", "secret", 6000))

    def test_wrong_merchant_currency_secret(self):
        self.assertFalse(verify_payment(self.payload(), "999", "secret", 3000))
        self.assertFalse(verify_payment(self.payload(), "123", "wrong", 3000))
        p=self.payload();p["payhere_currency"]="USD"
        self.assertFalse(verify_payment(p, "123", "secret", 3000))

    def test_missing_signature(self):
        p=self.payload();del p["md5sig"]
        self.assertFalse(verify_payment(p,"123","secret",3000))

    def test_checkout_amount_format(self):
        self.assertEqual(checkout_hash("123","INV-1",3000,"secret"),checksum("123","INV-1","3000.00","LKR",checksum("secret")))

    def test_bad_money(self):
        for value in ("NaN", "Infinity", "-1", "invalid"):
            with self.assertRaises(ValueError): money(value)


class ContentRules(unittest.TestCase):
    def test_institute_codes(self):
        self.assertEqual(institute_code(" bc0050 "),"BC0050")
        for invalid in ("B", "BC-10", "0ABC", "../../BC"):
            with self.assertRaises(ValueError): institute_code(invalid)

    def test_billing(self):
        for count,expected in ((0,15000),(500,15000),(501,15050),(528,16400)):
            self.assertEqual(billing_total(count,15000),Decimal(expected))

    def test_graphemes(self):
        self.assertEqual(text_length("a\u0301"),1)
        self.assertEqual(text_length("👩‍🏫"),1)
        self.assertEqual(limited("a"*30,30,"Motivation"),"a"*30)
        with self.assertRaises(ValueError): limited("a"*31,30,"Motivation")

    def test_youtube_urls(self):
        for url in ("dQw4w9WgXcQ","https://youtu.be/dQw4w9WgXcQ","https://www.youtube.com/watch?v=dQw4w9WgXcQ","https://www.youtube.com/live/dQw4w9WgXcQ"):
            self.assertEqual(youtube_id(url),"dQw4w9WgXcQ")
        for url in ("https://evil.com/watch?v=dQw4w9WgXcQ","https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ","javascript:alert(1)"):
            with self.assertRaises(ValueError): youtube_id(url)

    def test_resource_protocol(self):
        for url in ("javascript:alert(1)","http://example.com","https://user:pass@example.com"):
            with self.assertRaises(ValueError): safe_url(url)


if __name__ == "__main__": unittest.main()
