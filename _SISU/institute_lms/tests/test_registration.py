import unittest
import importlib
import sys
import types
import time
from unittest.mock import MagicMock
from institute_lms.registration_contract import registration_details

class Registration(unittest.TestCase):
    def test_owner_requires_exact_server_allowlist(self):
        with self.assertRaises(PermissionError): registration_details({'kind':'Super Admin','email':'attacker@example.com'},'owner@example.com')
        with self.assertRaises(PermissionError): registration_details({'kind':'Super Admin','email':'owner@example.com'},'')
        self.assertEqual(registration_details({'kind':'Super Admin','email':'OWNER@example.com'},'owner@example.com')['email'],'owner@example.com')
    def test_client_roles_rejected_and_students_can_self_register(self):
        with self.assertRaises(ValueError): registration_details({'kind':'System Manager','email':'test@example.com'},'')
        self.assertEqual(registration_details({'kind':'Student','email':'test@example.com','full_name':'Test'},'')['kind'],'Student')
        d=registration_details({'kind':'Student','email':'test@example.com','full_name':'Test','invite':'INVITE'},'')
        self.assertNotIn('roles',d)
    def test_business_recovery_contact_is_separate_and_required(self):
        d={'kind':'Institute','email':'test@example.com','full_name':'Test','organization':'Academy','country':'LK','job':'Director','phone':'+940000','backup_name':'Backup','backup_email':'test@example.com'}
        with self.assertRaises(ValueError): registration_details(d,'')
        d['backup_email']='recovery@example.com';self.assertEqual(registration_details(d,'')['kind'],'Institute')

class VerificationBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved={k:sys.modules.get(k) for k in ('frappe','frappe.utils','institute_lms.registration')}
        cls.f=types.ModuleType('frappe');cls.f.whitelist=lambda **kw:lambda fn:fn;cls.f.PermissionError=PermissionError
        def throw(message,kind=ValueError):raise kind(message)
        cls.f.throw=throw
        utils=types.ModuleType('frappe.utils');utils.get_url=lambda:'https://test.example.invalid'
        sys.modules.update({'frappe':cls.f,'frappe.utils':utils});sys.modules.pop('institute_lms.registration',None)
        cls.api=importlib.import_module('institute_lms.registration')
    @classmethod
    def tearDownClass(cls):
        for k,v in cls.saved.items():
            if v is None:sys.modules.pop(k,None)
            else:sys.modules[k]=v
    def setUp(self):
        class Config(dict):
            __getattr__=dict.get
        self.f.conf=Config(il_registration_enabled=True,encryption_key='unit-test-only',il_owner_email='owner@example.com')
        self.f.db=MagicMock();self.f.db.exists.return_value=True
        self.f.cache=MagicMock();self.f.get_doc=MagicMock();self.f.sendmail=MagicMock()
        self.f.local=types.SimpleNamespace(request_ip='127.0.0.1')
        self.f.session=types.SimpleNamespace(user='Guest')
    def test_owner_rejected_before_sending_code(self):
        with self.assertRaises(PermissionError):self.api.request_code({'kind':'Super Admin','email':'other@example.com'})
        self.f.sendmail.assert_not_called()
    def test_wrong_code_and_exhausted_challenge_never_create_request(self):
        pending={'details':{'kind':'Super Admin','email':'owner@example.com'},'created':time.time(),'attempts':0,'digest':self.api.digest('challenge','123456')}
        self.f.cache.get_value.return_value=pending
        with self.assertRaises(ValueError):self.api.verify_code('challenge','999999')
        self.assertEqual(pending['attempts'],1)
        pending['attempts']=5
        with self.assertRaises(ValueError):self.api.verify_code('challenge','123456')
        self.f.get_doc.assert_not_called()
    def test_success_creates_pending_request_without_user_or_role(self):
        self.f.cache.get_value.return_value={'details':{'kind':'Super Admin','email':'owner@example.com'},'created':time.time(),'attempts':0,'digest':self.api.digest('challenge','123456')}
        result=self.api.verify_code('challenge','123456')
        self.assertEqual(result['status'],'Pending review')
        record=self.f.get_doc.call_args_list[0].args[0]
        self.assertEqual(record['doctype'],'IL Registration Request');self.assertNotIn('roles',record)
        self.f.cache.delete_value.assert_called_once_with('il_signup:challenge')
    def test_guest_and_different_email_cannot_access_owner_services(self):
        with self.assertRaises(PermissionError):self.api.require_owner()
        self.f.session.user='other@example.com'
        with self.assertRaises(PermissionError):self.api.require_owner()

if __name__=='__main__':unittest.main()
