"""Authorization/transaction orchestration tests; live DB locking needs staging."""
import importlib
import sys
import types
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class WalletAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = ('frappe', 'frappe.utils', 'institute_lms.registration', 'institute_lms.wallet')
        cls.previous = {key: sys.modules.get(key) for key in cls.names}
        cls.f = types.ModuleType('frappe')
        cls.f.whitelist = lambda **kw: lambda fn: fn
        cls.f.PermissionError = PermissionError
        def throw(message, kind=ValueError):
            raise kind(message)
        cls.f.throw = throw
        util = types.ModuleType('frappe.utils')
        util.now_datetime = lambda: datetime(2026, 9, 25, 12)
        util.get_datetime = lambda value: datetime.fromisoformat(value)
        registration = types.ModuleType('institute_lms.registration')
        registration.require_owner = MagicMock()
        sys.modules.update({'frappe': cls.f, 'frappe.utils': util, 'institute_lms.registration': registration})
        sys.modules.pop('institute_lms.wallet', None)
        cls.api = importlib.import_module('institute_lms.wallet')

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.previous.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value

    def setUp(self):
        self.f.session = types.SimpleNamespace(user='teacher@example.invalid')
        self.f.conf = {'il_usd_lkr_rate': '301.234', 'il_usd_lkr_rate_updated_at': '2026-09-25 10:00:00'}
        self.f.db = MagicMock()
        self.f.db.exists.return_value = False
        self.f.db.get_value.return_value = None
        self.f.get_doc = MagicMock()
        self.wallet = types.SimpleNamespace(name='W1', owner_user=self.f.session.user,
            enabled=1, currency='LKR', country='Sri Lanka', available_minor=1000000, held_minor=0)

    def test_foreign_wallet_and_guest_are_denied(self):
        self.f.get_doc.return_value = self.wallet
        self.f.session.user = 'other@example.invalid'
        with self.assertRaises(PermissionError): self.api.authorized('W1')
        self.f.session.user = 'Guest'
        with self.assertRaises(PermissionError): self.api.authorized('W1')

    def test_lkr_minimum_uses_dated_rate_and_rounds_up(self):
        self.assertEqual(self.api.minimum('USD'), 2000)
        self.assertEqual(self.api.minimum('LKR'), 602468)
        self.f.conf['il_usd_lkr_rate_updated_at'] = '2026-09-17 00:00:00'
        with self.assertRaises(ValueError): self.api.minimum('LKR')
        self.f.conf['il_usd_lkr_rate_updated_at'] = '2026-09-26 00:00:00'
        with self.assertRaises(ValueError): self.api.minimum('LKR')

    def test_retry_returns_original_without_second_reservation(self):
        prior = types.SimpleNamespace(name='P1', amount_minor=700000, method='M1', status='Pending')
        self.f.db.get_value.return_value = prior
        with patch.object(self.api, 'authorized', return_value=self.wallet), patch.object(self.api, 'post') as post:
            self.assertIs(self.api.request_payout('W1', 'M1', '7000', 'a'*20), prior)
            post.assert_not_called()
            with self.assertRaises(ValueError): self.api.request_payout('W1', 'M1', '8000', 'a'*20)

    def test_foreign_or_unapproved_method_cannot_reserve(self):
        for wallet, status in [('OTHER', 'Approved'), ('W1', 'Pending'), ('W1', 'Superseded')]:
            self.f.get_doc.return_value = types.SimpleNamespace(wallet=wallet, status=status)
            with patch.object(self.api, 'authorized', return_value=self.wallet), patch.object(self.api, 'insert') as insert:
                with self.assertRaises(ValueError): self.api.request_payout('W1', 'M1', '7000', 'a'*20)
                insert.assert_not_called()

    def test_below_minimum_and_insufficient_balance_do_not_insert(self):
        self.f.get_doc.return_value = types.SimpleNamespace(wallet='W1', status='Approved')
        with patch.object(self.api, 'authorized', return_value=self.wallet), patch.object(self.api, 'insert') as insert:
            for amount in ('6000', '11000'):
                with self.assertRaises(ValueError): self.api.request_payout('W1', 'M1', amount, 'a'*20)
            insert.assert_not_called()

    def test_request_posts_exact_reservation(self):
        self.f.get_doc.return_value = types.SimpleNamespace(name='M1', wallet='W1', status='Approved')
        with patch.object(self.api, 'authorized', return_value=self.wallet), patch.object(self.api, 'insert', return_value=types.SimpleNamespace(name='P1')), patch.object(self.api, 'post') as post, patch.object(self.api, 'audit'):
            result = self.api.request_payout('W1', 'M1', '7000', 'a'*20)
            self.assertEqual(result['status'], 'Pending')
            post.assert_called_once_with(self.wallet, 'reserve:P1', 'Reserve', -700000, 700000, payout='P1')

    def test_completed_replay_never_posts_again(self):
        req = types.SimpleNamespace(wallet='W1', status='Completed', transaction_reference='TX1', reason='', receipt=None, reload=lambda: None)
        self.f.get_doc.return_value = req
        self.f.session.user = 'owner@example.invalid'
        with patch.object(self.api, 'owner'), patch.object(self.api, 'locked_wallet', return_value=self.wallet), patch.object(self.api, 'post') as post:
            self.assertEqual(self.api.update_payout('P1', 'Completed', reference='TX1'), {'status':'Completed'})
            with self.assertRaises(ValueError): self.api.update_payout('P1', 'Completed', reference='TX2')
            post.assert_not_called()

    def test_rejection_releases_exact_held_amount(self):
        req = MagicMock(name='request')
        req.name='P1'; req.wallet='W1'; req.status='Pending'; req.amount_minor=700000
        self.f.get_doc.return_value = req
        self.f.session.user = 'owner@example.invalid'
        with patch.object(self.api, 'owner'), patch.object(self.api, 'locked_wallet', return_value=self.wallet), patch.object(self.api, 'saved'), patch.object(self.api, 'post') as post, patch.object(self.api, 'audit'):
            self.api.update_payout('P1', 'Rejected', reason='Destination needs correction')
            post.assert_called_once_with(self.wallet, 'rejected:P1', 'Release', 700000, -700000, payout='P1', reference='', reason='Destination needs correction')
