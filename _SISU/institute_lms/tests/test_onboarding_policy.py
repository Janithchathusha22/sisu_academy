"""Boundary tests; real OAuth, SMS and database migrations still need site acceptance."""
import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock,patch

class PolicyBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names=('frappe','frappe.utils','institute_lms.wallet','institute_lms.portal_policy')
        cls.saved={n:sys.modules.get(n) for n in names}
        cls.f=types.ModuleType('frappe');cls.f.whitelist=lambda **kw:lambda f:f;cls.f.AuthenticationError=PermissionError
        def throw(message,kind=ValueError):raise kind(message)
        cls.f.throw=throw
        utils=types.ModuleType('frappe.utils');utils.cint=lambda n:int(n or 0)
        cls.wallet=types.ModuleType('institute_lms.wallet');cls.wallet.owner=MagicMock();cls.wallet.audit=MagicMock()
        sys.modules.update({'frappe':cls.f,'frappe.utils':utils,'institute_lms.wallet':cls.wallet})
        sys.modules.pop('institute_lms.portal_policy',None)
        cls.policy=importlib.import_module('institute_lms.portal_policy')
    @classmethod
    def tearDownClass(cls):
        for n,v in cls.saved.items():
            if v is None:sys.modules.pop(n,None)
            else:sys.modules[n]=v
    def setUp(self):
        self.f.db=MagicMock();self.f.db.exists.return_value=False
        self.d=types.SimpleNamespace(privacy_policy_url='',privacy_policy_version='',provider_applications_enabled=0,save=MagicMock(),name='IL Portal Settings')
        self.f.get_single=MagicMock(return_value=self.d)
        self.f.session=types.SimpleNamespace(user='student@example.invalid',data={})
        self.f.local=types.SimpleNamespace(request=types.SimpleNamespace(path='/api/method/login'),session_obj=MagicMock())
        self.f.form_dict={'cmd':'frappe.integrations.oauth2_logins.login_via_google'}
        self.wallet.owner.reset_mock(side_effect=True)
    def test_empty_policy_is_placeholder_not_consent(self):
        self.assertEqual(self.policy.public()['privacy_policy_url'],'')
        self.assertFalse(self.policy.public()['provider_applications_enabled'])
        with self.assertRaises(ValueError):self.policy.save('','',1)
        self.d.save.assert_not_called()
    def test_only_owner_can_change_policy(self):
        self.wallet.owner.side_effect=PermissionError('owner required')
        with self.assertRaises(PermissionError):self.policy.save('https://example.invalid/privacy','v1',1)
        self.f.get_single.assert_not_called()
    def test_policy_requires_https_and_version(self):
        with self.assertRaises(ValueError):self.policy.save('javascript:alert(1)','v1',1)
        with self.assertRaises(ValueError):self.policy.save('https://example.invalid/privacy','',1)
        self.d.save.assert_not_called()
    def test_string_zero_does_not_enable_applications(self):
        self.policy.save('','','0')
        self.assertEqual(self.d.provider_applications_enabled,0)
    def test_policy_can_be_enabled_after_publication(self):
        r=self.policy.save('https://example.invalid/privacy','v1',1)
        self.assertTrue(r['provider_applications_enabled'])
        self.wallet.audit.assert_called()
    def test_forged_cmd_on_password_login_does_not_grant_google_session(self):
        self.policy.stamp_session()
        with self.assertRaises(PermissionError):self.policy.require_google_student()
    def test_google_callback_session_is_persisted(self):
        self.f.local.request.path='/api/method/frappe.integrations.oauth2_logins.login_via_google'
        self.policy.stamp_session();self.policy.require_google_student()
        self.f.local.session_obj.update.assert_called_once_with(force=True)
    def test_guest_callback_cannot_be_marked_verified(self):
        self.f.session.user='Guest';self.f.local.request.path='/api/method/frappe.integrations.oauth2_logins.login_via_google'
        self.policy.stamp_session()
        with self.assertRaises(PermissionError):self.policy.require_google_student()
    def test_student_password_login_is_blocked_before_session_creation(self):
        self.f.db.exists.return_value=True
        with self.assertRaises(PermissionError):self.policy.validate_login(types.SimpleNamespace(user='student@example.invalid'))
    def test_provider_password_login_remains_supported(self):
        self.policy.validate_login(types.SimpleNamespace(user='teacher@example.invalid'))

if __name__=='__main__':unittest.main()
