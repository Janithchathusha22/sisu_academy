"""Private document uploads and authorization on every read/download."""
import secrets
from datetime import timedelta
from pathlib import Path
import frappe
from frappe.utils import now_datetime
from .api import classroom_for, accessible_room, scoped
from .material_contract import MAX_BYTES, TYPES, validate_file, require_download, require_preview


@frappe.whitelist(methods=['POST'])
def upload(classroom, purpose='original'):
    _,member,room=classroom_for(classroom,write=True)
    if purpose not in ('original','preview'):frappe.throw('Invalid upload purpose')
    item=frappe.request.files.get('file')
    if not item:frappe.throw('Choose a document')
    content=item.stream.read(MAX_BYTES+1)
    try:suffix,_=validate_file(item.filename,content,preview=purpose=='preview')
    except ValueError as exc:frappe.throw(str(exc))
    # Bound bulk storage abuse; configure reverse-proxy and per-site quotas as well.
    if frappe.db.count('File',{'owner':frappe.session.user,'attached_to_doctype':'IL Classroom','creation':['>',now_datetime()-timedelta(hours=1)]})>=40:
        frappe.throw('Upload limit reached. Please try again later')
    from frappe.utils.file_manager import save_file
    file=save_file('material-'+secrets.token_hex(12)+'.'+suffix,content,'IL Classroom',room.name,is_private=1)
    return {'file_id':file.name,'filename':item.filename,'file_type':suffix,'file_size':len(content)}


def checked_file(name,room,require_owner=False):
    file=frappe.get_doc('File',name)
    if not file.is_private or file.attached_to_doctype!='IL Classroom' or file.attached_to_name!=room.name:
        frappe.throw('Document unavailable',frappe.PermissionError)
    if require_owner and file.owner!=frappe.session.user:
        frappe.throw('Upload your own copy of the document',frappe.PermissionError)
    # Only local private storage is supported. Do not fetch a client-controlled URL.
    private=Path(frappe.get_site_path('private','files')).resolve()
    path=Path(file.get_full_path()).resolve()
    if private not in path.parents or not path.is_file() or path.stat().st_size>MAX_BYTES:
        frappe.throw('Document unavailable',frappe.PermissionError)
    return file,path


def attachment_fields(data,room):
    file,path=checked_file(data.file_id,room,require_owner=True)
    content=path.read_bytes()
    try:suffix,_=validate_file(file.file_name,content)
    except ValueError as exc:frappe.throw(str(exc))
    preview=data.get('preview_file_id')
    if preview:
        pdf,pdf_path=checked_file(preview,room,require_owner=True)
        try:validate_file(pdf.file_name,pdf_path.read_bytes(),preview=True)
        except ValueError as exc:frappe.throw(str(exc))
    policy=data.get('download_policy') or 'View only'
    try:require_preview(suffix,preview,policy)
    except ValueError as exc:frappe.throw(str(exc))
    # Friendly name is display metadata only; the server chooses file paths.
    filename=str(data.get('filename') or file.file_name)
    if any(c in filename for c in '/\\\r\n\x00') or len(filename)>180:frappe.throw('Invalid display filename')
    return {'file_id':file.name,'preview_file_id':preview,'filename':filename,'file_type':suffix,
            'file_size':len(content),'download_policy':policy,'url':''}


@frappe.whitelist(methods=['GET'])
def content(material, action='view'):
    doc=frappe.get_doc('IL Material',material)
    inst,member,room=accessible_room(doc.classroom)
    scoped('IL Material',material,inst)
    if action not in ('view','download'):frappe.throw('Invalid document action')
    if action=='download':
        try:require_download(doc.download_policy,member.role)
        except PermissionError as exc:frappe.throw(str(exc),frappe.PermissionError)
        file_id=doc.file_id;filename=doc.filename
    else:
        file_id=doc.file_id if doc.file_type=='pdf' else doc.preview_file_id
        filename='preview.pdf'
    if not file_id:frappe.throw('No PDF preview has been uploaded for this material')
    file,path=checked_file(file_id,room)
    raw=path.read_bytes()
    try:suffix,mime=validate_file(file.file_name,raw,preview=action=='view')
    except ValueError as exc:frappe.throw(str(exc))
    frappe.local.response.update({'type':'download','filename':filename or 'document.'+suffix,
        'filecontent':raw,'content_type':mime,'display_content_as':'inline' if action=='view' else 'attachment'})
    frappe.local.response_headers.update({'Cache-Control':'no-store, private','X-Content-Type-Options':'nosniff'})
