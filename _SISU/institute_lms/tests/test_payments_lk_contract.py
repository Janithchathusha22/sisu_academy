import hashlib
import hmac
import unittest
from institute_lms.payments_lk_contract import amount_cents, verify_signature, valid_payment, hosted_url


class PaymentsLkContract(unittest.TestCase):
    raw = b'{"type":"payment.succeeded"}'
    secret = 'whsec_unit_test_only'
    now = 1800000000

    def signature(self, raw=None, timestamp=None):
        raw = self.raw if raw is None else raw
        timestamp = self.now if timestamp is None else timestamp
        sig = hmac.new(self.secret.encode(), str(timestamp).encode()+b'.'+raw, hashlib.sha256).hexdigest()
        return f't={timestamp},v1={sig}'

    def test_exact_cents_and_limits(self):
        self.assertEqual(amount_cents('3500.01'),350001)
        self.assertEqual(amount_cents(10),1000)
        for value in ('NaN','Infinity',-1,9.99,'10.001',1000001,True):
            with self.assertRaises(ValueError): amount_cents(value)

    def test_raw_bytes_and_rotation(self):
        self.assertTrue(verify_signature(self.raw,self.signature(),self.secret,now=self.now))
        self.assertTrue(verify_signature(self.raw,self.signature()+',v1='+'0'*64,self.secret,now=self.now))
        self.assertFalse(verify_signature(self.raw+b' ',self.signature(),self.secret,now=self.now))
        self.assertFalse(verify_signature(self.raw,self.signature(),'different',now=self.now))

    def test_replay_and_future_tolerance(self):
        for delta in (-301,301):
            self.assertFalse(verify_signature(self.raw,self.signature(timestamp=self.now+delta),self.secret,now=self.now))
        self.assertFalse(verify_signature(self.raw,self.signature()+f',t={self.now}',self.secret,now=self.now))
        self.assertFalse(verify_signature(self.raw,None,self.secret,now=self.now))

    def test_hosted_redirect_allowlist(self):
        self.assertTrue(hosted_url('https://payments.lk/checkout/chk_abc'))
        self.assertTrue(hosted_url('https://payments.lk/si/checkout/chk_abc'))
        for value in ('https://payments.lk.evil.test/checkout/chk_a','https://payments.lk@evil.test/checkout/chk_a','http://payments.lk/checkout/chk_a','https://payments.lk:999/checkout/chk_a','javascript:alert(1)',None):
            self.assertFalse(hosted_url(value))

    def test_payment_binding(self):
        invoice=dict(name='INV-1',amount=3000,gateway_checkout_id='chk_original')
        payment=dict(object='payment',status='succeeded',mode='test',currency='LKR',amountCents=300000,reference='INV-1',checkoutId='chk_original',id='pay_'+'a'*24)
        self.assertTrue(valid_payment(payment,invoice,'test'))
        for key,value in [('status','failed'),('mode','live'),('currency','USD'),('amountCents',300001),('amountCents',300000.0),('reference','INV-2'),('checkoutId','chk_other'),('id','pay_bad')]:
            self.assertFalse(valid_payment(dict(payment,**{key:value}),invoice,'test'),key)
        self.assertFalse(valid_payment(payment,dict(invoice,gateway_checkout_id=None),'test'))


if __name__ == '__main__': unittest.main()
