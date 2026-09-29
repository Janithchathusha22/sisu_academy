import unittest
from datetime import date
from institute_lms.private_contact_rules import normalize,age_on

class PrivateContactRules(unittest.TestCase):
    def setUp(self):
        self.data={'date_of_birth':'2010-09-29','notification_language':'en','guardian_name':'Parent example','guardian_relationship':'Mother','guardian_phone':'+94770000000'}
        self.today=date(2026,9,28)
    def test_exact_sixteenth_birthday(self):
        self.assertEqual(age_on('2010-09-29',self.today),15)
        self.assertEqual(age_on('2010-09-28',self.today),16)
        self.assertEqual(age_on('2012-02-29',date(2026,2,28)),13)
    def test_under16_guardian_is_required(self):
        for field in ('guardian_name','guardian_phone','guardian_relationship'):
            with self.assertRaises(ValueError):normalize({**self.data,field:''},'Student',self.today)
    def test_guardian_whatsapp_requires_permission_and_matching_number(self):
        data={**self.data,'whatsapp_opt_in':True,'whatsapp_phone':'+94770000001'}
        with self.assertRaises(ValueError):normalize(data,'Student',self.today)
        data['guardian_permission']=True
        with self.assertRaises(ValueError):normalize(data,'Student',self.today)
        data['whatsapp_phone']=data['guardian_phone']
        self.assertEqual(normalize(data,'Student',self.today)['whatsapp_opt_in'],1)
    def test_future_invalid_and_missing_birthdays(self):
        for value in ('2027-01-01','2026-02-30','1890-01-01',''):
            with self.assertRaises(ValueError):normalize({**self.data,'date_of_birth':value},'Student',self.today)
    def test_adult_and_provider_no_guardian_required(self):
        self.assertIsNone(normalize({'notification_language':'en'},'Institute',self.today)['date_of_birth'])
        self.assertEqual(normalize({'date_of_birth':'2000-01-01','notification_language':'en'},'Student',self.today)['guardian_name'],'')
    def test_invalid_phones_and_string_consent_rejected(self):
        for extra in ({'contact_phone':'0771234567'},{'whatsapp_opt_in':'false'},{'guardian_email':'<bad>'}):
            with self.assertRaises(ValueError):normalize({**self.data,**extra},'Student',self.today)
