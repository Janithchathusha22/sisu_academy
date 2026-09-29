"""Contact and OAuth boundaries with mocked Frappe; no external requests."""
import importlib
import sys
import types
import time
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse, parse_qs
from institute_lms.calendar_contract import event_id, event_payload


class Record(dict):
    def __getattr__(self, key): return self.get(key)


class CalendarContact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names=('frappe','frappe.utils','institute_lms.api','institute_lms.contact','institute_lms.calendar_sync')
        cls.saved={k:sys.modules.get(k) for k in names}
        cls.f=types.ModuleType('frappe');cls.f.whitelist=lambda **kw:lambda fn:fn
        cls.f.PermissionError=PermissionError
        def throw(message,kind=ValueError):raise kind(message)
        cls.f.throw=throw
        utils=types.ModuleType('frappe.utils');utils.get_url=lambda path='':'https://test.example.invalid'+path
        utils.now_datetime=MagicMock()
        api=types.ModuleType('institute_lms.api');api.identity=MagicMock()
        def require_role(member,role):
            if member.role!=role:raise PermissionError('Role required')
        api.require_role=require_role
        sys.modules.update({'frappe':cls.f,'frappe.utils':utils,'institute_lms.api':api})
        cls.contact=importlib.import_module('institute_lms.contact')
        cls.calendar=importlib.import_module('institute_lms.calendar_sync')

    @classmethod
    def tearDownClass(cls):
        for k,v in cls.saved.items():
            if v is None:sys.modules.pop(k,None)
            else:sys.modules[k]=v

    def setUp(self):
        self.f.conf=Record(encryption_key='unit-test-only',il_calendar_client_id='test-client',il_calendar_client_secret='test-secret')
        self.f.session=Record(user='test@example.invalid');self.f.cache=MagicMock();self.f.db=MagicMock()
        self.f.db.get_value.return_value=None
        self.member=Record(name='ST-TEST-00001',role='Student',contact_email='test@example.invalid',contact_email_verified=1)
        self.contact.identity.return_value=(Record(name='TEST'),self.member)

    def test_payload_minimizes_data_and_preserves_offsets(self):
        body=event_payload({'title':'Lesson','starts_at':'2026-09-24T12:00:00+00:00','ends_at':'2026-09-24T13:00:00+00:00','youtube_id':'PRIVATE','payment':100},'Math','Asia/Colombo','https://test.example.invalid/campus#schedule')
        self.assertEqual(body['start']['dateTime'],'2026-09-24T17:30:00+05:30')
        self.assertEqual(body['visibility'],'private');self.assertEqual(body['status'],'confirmed')
        self.assertNotIn('PRIVATE',str(body));self.assertNotIn('payment',str(body));self.assertNotIn('attendees',body)
        self.assertNotEqual(event_id('A','S','C'),event_id('B','S','C'))
        self.assertEqual(event_id('A','S','C'),event_id('A','S','C'))

    def test_invalid_calendar_range_rejected(self):
        with self.assertRaises(ValueError):event_payload({'title':'X','starts_at':'2026-09-24 12:00','ends_at':'2026-09-24 11:00'},'Math','UTC','https://test.example.invalid')

    def test_connect_requires_verified_student_and_limited_scope(self):
        self.member['contact_email_verified']=0
        with self.assertRaises(ValueError):self.calendar.connect()
        self.member['contact_email_verified']=1;self.member['role']='Teacher'
        with self.assertRaises(PermissionError):self.calendar.connect()
        self.member['role']='Student'
        q=parse_qs(urlparse(self.calendar.connect()['url']).query)
        self.assertEqual(q['scope'],['openid email '+self.calendar.SCOPE])
        self.assertEqual(q['code_challenge_method'],['S256']);self.assertGreater(len(q['state'][0]),32)
        self.assertNotIn('test-secret',str(q))

    def test_callback_consumes_state_and_rejects_different_account(self):
        self.f.cache.get_value.return_value={'user':'someone-else','member':self.member.name,'institute':'TEST','email':self.member.contact_email}
        with patch.object(self.calendar,'request') as request:
            with self.assertRaises(PermissionError):self.calendar.callback('state','code')
            request.assert_not_called()
        self.f.cache.delete_value.assert_called_once_with('il_calendar_oauth:state')

    def test_codes_are_member_bound_limited_and_consumed(self):
        pending={'email':self.member.contact_email,'created':time.time(),'attempts':0,'digest':self.contact.code_digest(self.member.name,self.member.contact_email,'123456','unit-test-only')}
        self.f.cache.get_value.return_value=pending
        with self.assertRaises(ValueError):self.contact.verify('000000')
        self.f.db.set_value.assert_not_called();self.assertEqual(pending['attempts'],1)
        self.contact.verify('123456')
        self.f.cache.delete_value.assert_called_once_with('il_contact:'+self.member.name)
        self.assertNotEqual(pending['digest'],self.contact.code_digest('OTHER',self.member.contact_email,'123456','unit-test-only'))
        pending['attempts']=5
        with self.assertRaises(ValueError):self.contact.verify('123456')

    def test_email_consent_requires_verification_and_boolean(self):
        self.member['contact_email_verified']=0
        with self.assertRaises(ValueError):self.contact.preferences(True)
        with self.assertRaises(ValueError):self.contact.preferences('true')
        self.f.db.set_value.assert_not_called()
        self.contact.preferences(False)
        self.f.db.set_value.assert_called_once_with('IL Member',self.member.name,'email_opt_in',0)
        with self.assertRaises(ValueError):self.contact.email_address('student@example.invalid\r\nBcc: other@example.invalid')


if __name__=='__main__':unittest.main()
