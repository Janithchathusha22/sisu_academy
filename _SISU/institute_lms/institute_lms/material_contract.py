"""Bounded file validation and material access policy; no file execution."""
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile, BadZipFile

MAX_BYTES = 10 * 1024 * 1024
TYPES = {'pdf':'application/pdf', 'ppt':'application/vnd.ms-powerpoint',
         'pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation',
         'doc':'application/msword', 'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}


def validate_file(filename, content, preview=False):
    if not isinstance(filename,str) or not filename or len(filename)>180 or any(c in filename for c in '/\\\r\n\x00'):
        raise ValueError('Use a simple filename of at most 180 characters')
    suffix=filename.rsplit('.',1)[-1].lower()
    if suffix not in TYPES or (preview and suffix!='pdf'):raise ValueError('Use PDF, PPT/PPTX or DOC/DOCX; previews must be PDF')
    if not isinstance(content,bytes) or not content or len(content)>MAX_BYTES:raise ValueError('Choose a nonempty document of at most 10 MB')
    if suffix=='pdf' and not content.startswith(b'%PDF-'):raise ValueError('File is not a PDF')
    if suffix in ('ppt','doc') and not content.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):raise ValueError('Invalid legacy Office file')
    if suffix in ('pptx','docx'):
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries=archive.infolist();names={e.filename for e in entries}
                required='ppt/presentation.xml' if suffix=='pptx' else 'word/document.xml'
                if len(entries)>2000 or sum(e.file_size for e in entries)>50*1024*1024:raise ValueError('Office document is too complex; use a smaller file')
                if required not in names or '[Content_Types].xml' not in names:raise ValueError('Invalid Office document type')
                for e in entries:
                    path=PurePosixPath(e.filename)
                    if path.is_absolute() or '..' in path.parts or '\\' in e.filename or e.flag_bits&1 or 'vbaproject' in e.filename.lower():raise ValueError('Encrypted or macro-bearing Office files are not supported')
        except BadZipFile:raise ValueError('Invalid Office archive') from None
    return suffix,TYPES[suffix]


def require_download(policy, role):
    if role=='Student' and policy!='Downloadable':raise PermissionError('Your teacher has made this material view only')


def require_preview(suffix, preview_file, policy):
    if policy not in ('View only','Downloadable'):raise ValueError('Choose View only or Downloadable')
    if suffix!='pdf' and policy=='View only' and not preview_file:raise ValueError('Add a matching PDF preview for view-only PowerPoint or Word materials')
