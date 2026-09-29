import unittest
from institute_lms.profile_rules import provider_socials

class ProfileSocialRules(unittest.TestCase):
    def test_provider_links_and_student_exclusion(self):
        links={'facebook':'https://www.facebook.com/example'}
        for kind in ('Teacher','Institute'):
            self.assertEqual(provider_socials(kind,links),links)
        self.assertEqual(provider_socials('Student',links),{})

    def test_unsafe_links_rejected(self):
        for url in ('javascript:alert(1)','http://example.com','https://user:password@example.com'):
            with self.assertRaises(ValueError):
                provider_socials('Teacher',{'youtube':url})

    def test_unknown_keys_ignored(self):
        self.assertEqual(provider_socials('Institute',{'unknown':'https://example.com'}),{})
