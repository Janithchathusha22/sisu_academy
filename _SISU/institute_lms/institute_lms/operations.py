"""Shared attendance and support services, scoped to active site membership."""
import csv
import hashlib
import io
from datetime import timedelta
import frappe
from frappe.utils import now_datetime,get_datetime
from .api import identity,classroom_for,accessible_room,scoped,require_role,room_filters
from .wallet_rules import csv_cell

def save(doc):
    doc.flags.operations_service=True
    return doc.save(ignore_permissions=True)

def record(room,session,student,status,channel,note):
    key=hashlib.sha256((session.name+':'+student).encode()).hexdigest()
    frappe.db.sql('SELECT name FROM `tabIL Member` WHERE name=%s FOR UPDATE',(student,))
    name=frappe.db.get_value('IL Attendance',{'attendance_key':key},'name')
    doc=frappe.get_doc('IL Attendance',name) if name else frappe.get_doc({'doctype':'IL Attendance','attendance_key':key,
        'institute':room.institute,'classroom':room.name,'session':session.name,'student':student})
    # Repeated joins never override a teacher's physical register or excused entry.
    if name and channel=='Online':return {'name':doc.name,'status':doc.status}
    doc.status=status;doc.channel=channel;doc.recorded_at=now_datetime();doc.recorded_by=frappe.session.user;doc.note=str(note)[:500];save(doc)
    return {'name':doc.name,'status':doc.status}

@frappe.whitelist(methods=['POST'])
def mark_attendance(session,student,status,note=''):
    meeting=frappe.get_doc('IL Session',session);inst,member,room=classroom_for(meeting.classroom,write=True)
    if status not in ('Present','Absent','Excused') or meeting.institute!=inst.name:frappe.throw('Invalid attendance record')
    person=scoped('IL Member',student,inst)
    if person.role!='Student' or not person.active or not frappe.db.exists('IL Enrollment',{'classroom':room.name,'student':student,'active':1}):frappe.throw('Select an active enrolled student')
    return record(room,meeting,student,status,'Physical',note)

@frappe.whitelist(methods=['POST'])
def join_session(session):
    meeting=frappe.get_doc('IL Session',session);inst,member,room=accessible_room(meeting.classroom)
    require_role(member,'Student')
    if meeting.institute!=inst.name or meeting.status=='Cancelled':frappe.throw('Session unavailable')
    now=now_datetime()
    if not get_datetime(meeting.starts_at)-timedelta(minutes=15)<=now<=get_datetime(meeting.ends_at):frappe.throw('Join within the scheduled session time')
    if not meeting.youtube_id:frappe.throw('An online session has not been connected')
    record(room,meeting,member.name,'Present','Online','Joined through the LMS; not proof of viewing duration')
    return {'youtube_id':meeting.youtube_id}

def attendance_rows(classroom,session=None,page=0):
    inst,member,room=classroom_for(classroom)
    filters={'institute':inst.name,'classroom':room.name}
    if member.role=='Student':filters['student']=member.name
    if session:filters['session']=session
    return frappe.get_all('IL Attendance',filters=filters,fields=['name','session','student','channel','status','recorded_at','note'],
        order_by='recorded_at desc',start=max(0,min(int(page),10000))*100,limit_page_length=100)

@frappe.whitelist()
def attendance(classroom,session=None,page=0):return attendance_rows(classroom,session,page)

@frappe.whitelist(methods=['GET'])
def attendance_csv(classroom,session=None,page=0):
    classroom_for(classroom,write=True)
    rows=attendance_rows(classroom,session,page)
    output=io.StringIO();writer=csv.writer(output);keys=['session','student','channel','status','recorded_at','note'];writer.writerow(keys)
    writer.writerows([[csv_cell(str(row.get(k) or '')) for k in keys] for row in rows])
    frappe.local.response.update({'type':'download','filename':'attendance-page-'+str(int(page)+1)+'.csv','filecontent':('\ufeff'+output.getvalue()).encode('utf-8'),'content_type':'text/csv','display_content_as':'attachment'})
    frappe.local.response_headers.update({'Cache-Control':'no-store, private'})

@frappe.whitelist(methods=['POST'])
def create_ticket(subject,category,body):
    inst,member=identity()
    subject=str(subject).strip();body=str(body).strip()
    if not 1<=len(subject)<=120 or not 1<=len(body)<=2000 or category not in ('Account','Payment','Classroom','Technical','Other'):frappe.throw('Use a subject up to 120 characters and a message up to 2,000 characters')
    from .registration import limit
    limit('support:'+frappe.session.user)
    doc=save(frappe.get_doc({'doctype':'IL Support Ticket','institute':inst.name,'requester':frappe.session.user,'subject':subject,'category':category,'status':'Open'}))
    save(frappe.get_doc({'doctype':'IL Support Reply','ticket':doc.name,'author_user':frappe.session.user,'body':body}))
    return {'name':doc.name}

def ticket_for(name):
    inst,member=identity();doc=scoped('IL Support Ticket',name,inst)
    if member.role!='Admin' and doc.requester!=frappe.session.user:frappe.throw('Ticket unavailable',frappe.PermissionError)
    return doc,member

@frappe.whitelist()
def tickets(page=0):
    inst,member=identity();filters={'institute':inst.name}
    if member.role!='Admin':filters['requester']=frappe.session.user
    return frappe.get_all('IL Support Ticket',filters=filters,fields=['name','subject','category','status','requester','modified'],order_by='modified desc',
        start=max(0,min(int(page),10000))*30,limit_page_length=30)

@frappe.whitelist()
def thread(ticket,page=0):
    ticket_for(ticket)
    return frappe.get_all('IL Support Reply',filters={'ticket':ticket},fields=['name','author_user','body','creation'],order_by='creation asc',
        start=max(0,min(int(page),10000))*50,limit_page_length=50)

@frappe.whitelist(methods=['POST'])
def reply(ticket,body,status=None):
    doc,member=ticket_for(ticket);body=str(body).strip()
    if not 1<=len(body)<=2000:frappe.throw('Write a reply of at most 2,000 characters')
    if status:
        require_role(member,'Admin')
        if status not in ('Open','In progress','Resolved'):frappe.throw('Invalid ticket status')
        doc.status=status
    save(frappe.get_doc({'doctype':'IL Support Reply','ticket':doc.name,'author_user':frappe.session.user,'body':body}));save(doc)
    return {'saved':True}
