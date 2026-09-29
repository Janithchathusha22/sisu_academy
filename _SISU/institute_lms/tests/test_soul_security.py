"""SOUL authorization and provider-boundary tests; no real API or Frappe site."""
import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class Record(dict):
    def __getattr__(self, key): return self.get(key)


class SoulSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = ('frappe', 'frappe.utils', 'institute_lms.api', 'institute_lms.soul','institute_lms.wallet')
        cls.saved = {k: sys.modules.get(k) for k in names}
        cls.frappe = types.ModuleType('frappe')
        cls.frappe.whitelist = lambda **kwargs: lambda fn: fn
        cls.frappe.PermissionError = PermissionError
        def throw(message, kind=ValueError): raise kind(message)
        cls.frappe.throw = throw
        utils = types.ModuleType('frappe.utils')
        utils.get_url = lambda: 'https://test.example.invalid'
        api = types.ModuleType('institute_lms.api')
        api.identity = MagicMock()
        def require_role(member, role):
            if member.role != role: raise PermissionError('Role required')
        api.require_role = require_role
        sys.modules.update({'frappe': cls.frappe, 'frappe.utils': utils, 'institute_lms.api': api})
        wallet=types.ModuleType('institute_lms.wallet')
        wallet.owner=MagicMock(side_effect=PermissionError('Only platform owner may configure SOUL'))
        sys.modules['institute_lms.wallet']=wallet
        cls.soul = importlib.import_module('institute_lms.soul','institute_lms.wallet')

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.saved.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value

    def setUp(self):
        self.frappe.conf = Record(encryption_key='unit-test-only')
        self.frappe.session = Record(user='test@example.invalid')
        self.member = Record(role='Teacher', name='TC-TEST-0001')
        self.soul.identity.return_value = (Record(name='TEST'), self.member)
        self.doc = MagicMock(enabled=True, model='gpt-4.1-mini')
        self.doc.get_password.return_value = 'unit-test-key'
        self.frappe.get_single = MagicMock(return_value=self.doc)

    def test_students_need_deployment_review_and_individual_enablement(self):
        self.member.role = 'Student'
        with patch.object(self.soul, 'provider') as provider:
            with self.assertRaises(PermissionError): self.soul.chat('Help', consent=True)
            self.frappe.conf.update(il_soul_student_ai_reviewed=True, il_soul_zdr_verified=True)
            with self.assertRaises(PermissionError): self.soul.chat('Help', consent=True)
            provider.assert_not_called()
        self.member['soul_ai_enabled'] = 1
        self.assertTrue(self.soul.student_ready(self.member))

    def test_only_platform_owner_can_change_key(self):
        with self.assertRaises(PermissionError): self.soul.configure()
        self.member.role='Admin'
        with self.assertRaises(PermissionError): self.soul.configure()
        self.frappe.get_single.assert_not_called()

    def test_chat_requires_explicit_notice_acceptance(self):
        with patch.object(self.soul, 'provider') as provider:
            with self.assertRaises(ValueError): self.soul.chat('Help', consent=False)
            provider.assert_not_called()

    def test_flagged_input_never_reaches_response_model(self):
        with patch.object(self.soul, 'reserve'), patch.object(self.soul, 'provider', return_value={'results':[{'flagged':True}]}) as provider:
            result = self.soul.chat('Test input', consent=True)
            self.assertEqual(result['mode'], 'safety')
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(provider.call_args.args[0], 'moderations')

    def test_output_is_moderated_and_storage_disabled(self):
        response = {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Test reply'}]}]}
        with patch.object(self.soul, 'reserve'), patch.object(self.soul, 'provider', side_effect=[{'results':[{'flagged':False}]}, response, {'results':[{'flagged':True}]}]) as provider:
            result = self.soul.chat('Help', consent=True)
            self.assertEqual(result['reply'], self.soul.SAFE_REPLY)
            body = provider.call_args_list[1].args[2]
            self.assertIs(body['store'], False)
            self.assertNotIn(self.frappe.session.user, str(body))
            self.assertNotIn('tools', body)

    def test_missing_moderation_result_fails_closed(self):
        with patch.object(self.soul, 'reserve'), patch.object(self.soul, 'provider', return_value={'results':[]}) as provider:
            with self.assertRaises(ValueError): self.soul.chat('Help', consent=True)
            self.assertEqual(provider.call_count, 1)


if __name__ == '__main__': unittest.main()
