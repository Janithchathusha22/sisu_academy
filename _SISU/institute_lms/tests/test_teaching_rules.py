import unittest
from institute_lms.teaching_rules import capabilities,meeting_link,billing_month,module_plan

class TeachingRules(unittest.TestCase):
    def setUp(self):
        self.room=dict(owner_type='Institute',teacher='T1',teacher_access='Teaching only',teacher_assignment_active=1)
        self.teacher=dict(role='Teacher',name='T1',user='teacher@example.invalid')

    def test_teaching_only_cannot_edit_fees_or_delete(self):
        rights=capabilities(self.room,self.teacher)
        self.assertTrue(rights['teach'])
        for key in ('edit','fees','delete','assign'):self.assertFalse(rights[key])

    def test_full_control_can_manage_but_not_reassign(self):
        self.room['teacher_access']='Full control'
        rights=capabilities(self.room,self.teacher)
        self.assertTrue(rights['delete']);self.assertTrue(rights['fees']);self.assertFalse(rights['assign'])

    def test_revoked_membership_and_left_assignment_block_access(self):
        self.room['teacher_access']='Full control'
        self.assertFalse(capabilities(self.room,self.teacher,False)['teach'])
        self.room['teacher_assignment_active']=0
        self.assertFalse(capabilities(self.room,self.teacher)['teach'])

    def test_institute_admin_cannot_take_personal_class(self):
        self.room.update(owner_type='Teacher',owner_user=self.teacher['user'])
        self.assertFalse(capabilities(self.room,dict(role='Admin'))['teach'])
        self.assertTrue(capabilities(self.room,self.teacher,False)['delete'])

    def test_meeting_host_cannot_impersonate_provider(self):
        for provider,url in [('Zoom','https://us02web.zoom.us/j/123'),('Google Meet','https://meet.google.com/abc-defg-hij'),('YouTube','https://youtu.be/YSul9yrAvN4')]:self.assertEqual(meeting_link(provider,url),url)
        for provider,url in [('Zoom','https://zoom.us.evil.test/x'),('Google Meet','https://evil.test/meet.google.com'),('Zoom','http://zoom.us/j/123'),('Zoom','https://user:pass@zoom.us/j/123')]:
            with self.assertRaises(ValueError):meeting_link(provider,url)

    def test_module_and_month_validation(self):
        self.assertEqual(module_plan([dict(classroom=str(i),duration_weeks=2) for i in range(12)]),24)
        with self.assertRaises(ValueError):module_plan([dict(classroom='same'),dict(classroom='same')])
        self.assertEqual(billing_month('2026-09'),'2026-09')
        with self.assertRaises(ValueError):billing_month('2026-13')
