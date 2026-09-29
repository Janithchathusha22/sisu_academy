"""Authorization contract tests with a minimal Frappe boundary double.

These are NOT a substitute for bench integration tests against real Frappe.
"""
import importlib
import sys
import types
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch


class Record(dict):
    def __getattr__(self, key): return self.get(key)


class PermissionDenied(Exception): pass


class ApiAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {key: sys.modules.get(key) for key in ('frappe','frappe.model','frappe.model.naming','frappe.utils')}
        cls.frappe = types.ModuleType('frappe')
        cls.frappe.whitelist = lambda *a, **k: lambda f: f
        cls.frappe.PermissionError = PermissionDenied
        cls.frappe.AuthenticationError = PermissionDenied
        cls.frappe._dict = Record
        def throw(message, kind=ValueError): raise kind(message)
        cls.frappe.throw = throw
        cls.frappe.db = MagicMock()
        cls.frappe.get_doc = MagicMock()
        naming = types.ModuleType('frappe.model.naming'); naming.make_autoname = MagicMock()
        utils = types.ModuleType('frappe.utils')
        utils.getdate = lambda value: date.fromisoformat(str(value)[:10])
        utils.get_datetime = datetime.fromisoformat
        utils.now_datetime = datetime.now
        utils.today = lambda: '2026-09-23'
        utils.cint = int
        sys.modules.update({'frappe':cls.frappe,'frappe.model':types.ModuleType('frappe.model'),'frappe.model.naming':naming,'frappe.utils':utils})
        cls.api = importlib.import_module('institute_lms.api')

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.saved.items():
            if value is None: sys.modules.pop(key,None)
            else: sys.modules[key]=value
        sys.modules.pop('institute_lms.api',None)

    def setUp(self):
        self.frappe.get_doc.reset_mock()
        self.frappe.db.reset_mock()
        self.inst=Record(name='institute-A')

    def test_cross_institute_record_rejected(self):
        self.frappe.get_doc.return_value=Record(institute='institute-B')
        with self.assertRaises(PermissionDenied): self.api.scoped('IL Classroom','foreign',self.inst)

    def test_student_cannot_create_or_change_classroom(self):
        with patch.object(self.api,'identity',return_value=(self.inst,Record(name='student',role='Student'))):
            with self.assertRaises(PermissionDenied): self.api.save_classroom({})

    def test_teacher_cannot_edit_another_teachers_class(self):
        room=Record(institute='institute-A',name='class',teacher='other-teacher')
        self.frappe.get_doc.return_value=room
        with patch.object(self.api,'identity',return_value=(self.inst,Record(name='teacher',role='Teacher'))):
            with self.assertRaises(PermissionDenied): self.api.classroom_for('class',write=True)

    def test_non_enrolled_student_cannot_read_detail(self):
        self.frappe.get_doc.return_value=Record(institute='institute-A',name='class',teacher='teacher')
        self.frappe.db.get_value.return_value=None
        with patch.object(self.api,'identity',return_value=(self.inst,Record(name='student',role='Student'))):
            with self.assertRaises(PermissionDenied): self.api.classroom_for('class')

    def test_teacher_must_be_explicitly_authorized_for_access_override(self):
        member=Record(name='teacher',role='Teacher')
        self.frappe.get_doc.return_value=Record(institute='institute-A',classroom='class')
        with patch.object(self.api,'identity',return_value=(self.inst,member)), patch.object(self.api,'classroom_for',return_value=(self.inst,member,Record(allow_teacher_access_override=0))):
            with self.assertRaises(PermissionDenied): self.api.set_access('enrollment','Open','a reason')

    def test_delete_restore_preserves_related_records_and_is_idempotent(self):
        room=types.SimpleNamespace(name='class',institute='institute-A',teacher='teacher',teacher_access='Full control',active=1,save=MagicMock(),add_comment=MagicMock())
        room.get=lambda key,default=None:getattr(room,key,default)
        self.frappe.get_doc.return_value=room
        with patch.object(self.api,'identity',return_value=(self.inst,Record(name='teacher',role='Teacher'))):
            self.assertEqual(self.api.set_classroom_deleted('class',1)['active'],0)
            self.api.set_classroom_deleted('class',1)
            self.assertEqual(room.save.call_count,1)
            self.assertEqual(self.api.set_classroom_deleted('class',0)['active'],1)
            self.assertEqual(room.save.call_count,2)
            self.frappe.db.delete.assert_not_called()

    def test_delete_rejects_student_other_teacher_and_other_institute(self):
        for person,tenant in [(Record(name='student',role='Student'),'institute-A'),(Record(name='other',role='Teacher'),'institute-A'),(Record(name='admin',role='Admin'),'institute-B')]:
            self.frappe.get_doc.return_value=Record(name='class',institute=tenant,teacher='teacher',active=1)
            with patch.object(self.api,'identity',return_value=(self.inst,person)):
                with self.assertRaises(PermissionDenied):self.api.set_classroom_deleted('class',1)

    def test_deleted_room_blocks_student_even_with_enrollment(self):
        self.frappe.get_doc.return_value=Record(name='class',institute='institute-A',teacher='teacher',active=0)
        with patch.object(self.api,'identity',return_value=(self.inst,Record(name='student',role='Student'))):
            with self.assertRaises(PermissionDenied):self.api.classroom_for('class')
            with self.assertRaises(PermissionDenied):self.api.classrooms(deleted=1)

    def test_generic_rest_roles_are_not_granted(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]/'institute_lms/institute_lms/doctype'
        for file in root.glob('*/*.json'):
            schema=json.loads(file.read_text())
            self.assertTrue(all(p['role']=='System Manager' for p in schema.get('permissions',[])),file.name)

    def test_pagination_has_hard_bounds(self):
        self.assertEqual(self.api.paginate(-100),0)
        self.assertEqual(self.api.paginate(100000),240000)

    def test_all_programme_modules_use_one_anchor_invoice(self):
        room=Record(name='module-12',owner_type='Institute',teacher='T12',billing_type='Programme module')
        student=Record(name='student',role='Student')
        e=Record(name='enroll-module-12',active=1,fee=135000,programme_enrollment='programme-enrollment')
        self.frappe.db.get_value.side_effect=[e,'enroll-module-1']
        with patch.object(self.frappe,'get_all',return_value=[Record(status='Paid',due_date='2026-09-01')],create=True) as query:
            self.assertTrue(self.api.access(room,student)['allowed'])
            self.assertEqual(query.call_args.kwargs['filters'],{'enrollment':'enroll-module-1'})
        self.frappe.db.get_value.side_effect=None

    def test_monthly_access_queries_only_the_current_month(self):
        room=Record(name='monthly',owner_type='Institute',billing_type='Monthly')
        self.frappe.db.get_value.return_value=Record(name='enrollment',active=1,fee=8000)
        with patch.object(self.frappe,'get_all',return_value=[],create=True) as query:
            self.assertFalse(self.api.access(room,Record(role='Student',name='student'))['allowed'])
            self.assertEqual(query.call_args.kwargs['filters']['billing_month'],'2026-09')


if __name__=='__main__': unittest.main()
