"""Document boundaries. Real Frappe private-file routes also need staging tests."""
import importlib
import sys
import types
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from unittest.mock import MagicMock, patch
from institute_lms.material_contract import validate_file,require_download,require_preview,MAX_BYTES


class Record(dict):
    def __getattr__(self,key):return self.get(key)


class MaterialContract(unittest.TestCase):
    def test_rejects_wrong_type_size_path_and_preview_type(self):
        self.assertEqual(validate_file('lesson.pdf',b'%PDF-1.7 test')[0],'pdf')
        for name,body in [('lesson.pdf',b'<html>'),('../lesson.pdf',b'%PDF-'),('lesson.exe',b'MZ'),('lesson.pdf',b''),('lesson.pdf',b'%PDF-'+b'0'*MAX_BYTES)]:
            with self.assertRaises(ValueError):validate_file(name,body)
        with self.assertRaises(ValueError):validate_file('lesson.doc',bytes.fromhex('D0CF11E0A1B11AE1'),preview=True)

    def test_office_container_rejects_wrong_root_and_macro(self):
        def office(extra=None):
            data=BytesIO()
            with ZipFile(data,'w') as z:
                z.writestr('[Content_Types].xml','<Types/>');z.writestr('word/document.xml','<document/>')
                if extra:z.writestr(extra,'test')
            return data.getvalue()
        self.assertEqual(validate_file('lesson.docx',office())[0],'docx')
        for name,body in [('lesson.pptx',office()),('lesson.docx',office('word/vbaProject.bin')),('lesson.docx',office('../bad'))]:
            with self.assertRaises(ValueError):validate_file(name,body)

    def test_office_view_only_requires_pdf_companion(self):
        require_preview('pdf',None,'View only');require_preview('pptx','pdf-id','View only')
        require_preview('docx',None,'Downloadable')
        with self.assertRaises(ValueError):require_preview('pptx',None,'View only')
        with self.assertRaises(ValueError):require_preview('pdf',None,'Unknown')

    def test_student_download_fails_closed(self):
        for policy in ('View only',None,''):
            with self.assertRaises(PermissionError):require_download(policy,'Student')
        require_download('Downloadable','Student');require_download('View only','Teacher')


class MaterialAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names=('frappe','frappe.utils','institute_lms.api','institute_lms.materials')
        cls.saved={k:sys.modules.get(k) for k in names}
        cls.f=types.ModuleType('frappe');cls.f.whitelist=lambda **kw:lambda fn:fn;cls.f.PermissionError=PermissionError
        def throw(message,kind=ValueError):raise kind(message)
        cls.f.throw=throw
        utils=types.ModuleType('frappe.utils');utils.now_datetime=MagicMock()
        api=types.ModuleType('institute_lms.api');api.classroom_for=MagicMock();api.accessible_room=MagicMock();api.scoped=MagicMock()
        sys.modules.update({'frappe':cls.f,'frappe.utils':utils,'institute_lms.api':api})
        cls.mod=importlib.import_module('institute_lms.materials')

    @classmethod
    def tearDownClass(cls):
        for k,v in cls.saved.items():
            if v is None:sys.modules.pop(k,None)
            else:sys.modules[k]=v

    def setUp(self):
        self.f.get_doc=MagicMock();self.f.session=Record(user='teacher@example.invalid')
        self.f.local=Record(response={},response_headers={})
        self.mod.accessible_room.reset_mock(side_effect=True)
        self.room=Record(name='room-A',institute='A')
        self.mod.accessible_room.return_value=(Record(name='A'),Record(role='Student'),self.room)

    def test_locked_class_prevents_any_file_read(self):
        self.f.get_doc.return_value=Record(classroom='room-A')
        self.mod.accessible_room.side_effect=PermissionError('Payment required')
        with patch.object(self.mod,'checked_file') as read:
            with self.assertRaises(PermissionError):self.mod.content('material')
            read.assert_not_called()

    def test_view_only_student_cannot_request_original(self):
        self.f.get_doc.return_value=Record(classroom='room-A',download_policy='View only',file_id='original')
        with patch.object(self.mod,'checked_file') as read:
            with self.assertRaises(PermissionError):self.mod.content('material','download')
            read.assert_not_called()

    def test_private_files_must_be_bound_to_this_class_and_path(self):
        self.f.get_doc.return_value=Record(is_private=0,attached_to_doctype='IL Classroom',attached_to_name='room-A')
        with self.assertRaises(PermissionError):self.mod.checked_file('file',self.room)
        self.f.get_doc.return_value=Record(is_private=1,attached_to_doctype='IL Classroom',attached_to_name='room-B')
        with self.assertRaises(PermissionError):self.mod.checked_file('file',self.room)
        with TemporaryDirectory() as directory:
            private=Path(directory)/'private';private.mkdir();outside=Path(directory)/'outside.pdf';outside.write_bytes(b'%PDF-')
            self.f.get_site_path=lambda *args:str(private)
            self.f.get_doc.return_value=MagicMock(is_private=1,attached_to_doctype='IL Classroom',attached_to_name='room-A',get_full_path=lambda:str(outside))
            with self.assertRaises(PermissionError):self.mod.checked_file('file',self.room)

    def test_office_view_serves_only_pdf_companion(self):
        self.f.get_doc.return_value=Record(classroom='room-A',download_policy='View only',file_id='office-original',preview_file_id='pdf-preview',file_type='pptx')
        with TemporaryDirectory() as directory:
            path=Path(directory)/'preview.pdf';path.write_bytes(b'%PDF-1.7 test')
            with patch.object(self.mod,'checked_file',return_value=(Record(file_name='preview.pdf'),path)) as read:
                self.mod.content('material','view')
                read.assert_called_once_with('pdf-preview',self.room)
        self.assertEqual(self.f.local.response['content_type'],'application/pdf')
        self.assertEqual(self.f.local.response_headers['Cache-Control'],'no-store, private')


if __name__=='__main__':unittest.main()
