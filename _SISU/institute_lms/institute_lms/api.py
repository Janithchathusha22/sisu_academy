"""Explicit allowlisted API. Framework REST access is restricted to System Manager.

Roles are resolved from active memberships on the server, never from browser state.
Each Frappe site has exactly one institute, including its upstream LMS content.
"""
import json
from datetime import date, timedelta
import frappe
from frappe.model.naming import make_autoname
from frappe.utils import getdate, get_datetime, now_datetime, today, cint
from .domain import access_decision, limited, money, safe_url, youtube_id, institute_code


def payload(value):
    return frappe._dict(json.loads(value) if isinstance(value, str) else value)


def institute():
    rows = frappe.get_all("IL Institute", pluck="name", limit_page_length=2)
    if len(rows) != 1:
        frappe.throw("An administrator must configure one institute on this site.")
    return frappe.get_doc("IL Institute", rows[0])


def identity():
    if frappe.session.user == "Guest":
        frappe.throw("Please sign in", frappe.AuthenticationError)
    inst = institute()
    if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
        return inst, frappe._dict(name=None, role="Admin", full_name=frappe.session.user, user=frappe.session.user)
    member = frappe.db.get_value("IL Member", {"institute": inst.name, "user": frappe.session.user, "active": 1}, "*", as_dict=True)
    if not member:
        frappe.throw("No active institute membership", frappe.PermissionError)
    if member.role == "Student":
        from .portal_policy import require_google_student
        require_google_student()
    return inst, member


def require_role(member, *roles):
    if member.role not in roles:
        frappe.throw("You do not have permission for this action", frappe.PermissionError)


def scoped(doctype, name, inst):
    doc = frappe.get_doc(doctype, name)
    if doc.institute != inst.name:
        frappe.throw("Record unavailable", frappe.PermissionError)
    return doc


def classroom_for(name, write=False):
    inst, member = identity()
    room = scoped("IL Classroom", name, inst)
    from .teaching import rights
    if rights(room, member)['teach']:
        return inst, member, room
    if write or member.role != "Student":
        frappe.throw("Classroom unavailable", frappe.PermissionError)
    if not room.active:
        frappe.throw("This classroom is archived", frappe.PermissionError)
    enrollment = frappe.db.get_value("IL Enrollment", {"classroom": room.name, "student": member.name, "active": 1}, "*", as_dict=True)
    if not enrollment:
        frappe.throw("Please enroll in this classroom", frappe.PermissionError)
    return inst, member, room


def access(room, member):
    from .teaching import rights
    if rights(room, member)['teach']:
        return {"allowed": True, "reason": "Classroom manager"}
    enrollment = frappe.db.get_value("IL Enrollment", {"classroom": room.name, "student": member.name}, "*", as_dict=True)
    anchor = enrollment.name if enrollment else None
    if enrollment and enrollment.get('programme_enrollment'):
        anchor = frappe.db.get_value('IL Programme Enrollment',enrollment.programme_enrollment,'billing_enrollment')
    filters={'enrollment':anchor}
    if room.get('billing_type')=='Monthly':filters['billing_month']=today()[:7]
    invoices = frappe.get_all("IL Invoice", filters=filters, fields=["status", "due_date"]) if anchor else []
    allowed, reason = access_decision(enrollment, invoices, getdate(today()))
    return {"allowed": allowed, "reason": reason}


def accessible_room(name):
    inst, member, room = classroom_for(name)
    decision = access(room, member)
    if not decision["allowed"]:
        frappe.throw(decision["reason"], frappe.PermissionError)
    return inst, member, room


def room_filters(inst, member):
    filters = {"institute": inst.name, "active": 1}
    if member.role == "Teacher":
        filters["teacher"] = member.name
        filters['teacher_assignment_active'] = 1
    elif member.role == 'Admin':
        filters['owner_type'] = 'Institute'
    elif member.role == "Student":
        names = frappe.get_all("IL Enrollment", filters={"student": member.name, "active": 1}, pluck="classroom")
        filters["name"] = ["in", names or ["__none__"]]
    return filters


def paginate(page, size=24):
    return max(0, min(cint(page), 10000)) * size


@frappe.whitelist()
def bootstrap():
    inst, member = identity()
    return {"payment_provider": frappe.conf.get("il_payment_provider", "payments_lk"), "institute": {k: inst.get(k) for k in ("name", "code", "title", "logo", "accent", "language", "base_fee")},
            "member": member, "csrf_token": frappe.sessions.get_csrf_token(), "mode": "live",
            "lms_base": "/" + str(frappe.conf.get("lms_path", "lms")).strip("/"),
            "username": frappe.db.get_value("User", frappe.session.user, "username") or frappe.session.user}


@frappe.whitelist()
def classrooms(page: int = 0, search: str = "", deleted: int = 0):
    inst, member = identity()
    if cint(deleted):
        require_role(member, "Teacher", "Admin")
    filters = room_filters(inst, member)
    if cint(deleted):
        filters["active"] = 0
    or_filters = None
    if search:
        term = f"%{str(search)[:80]}%"
        or_filters = [["title", "like", term], ["subject", "like", term]]
    rooms = frappe.get_all("IL Classroom", filters=filters, fields=["*"],
                           or_filters=or_filters, limit_start=paginate(page), limit_page_length=24, order_by="creation desc")
    # Fetch only public teacher identity for this page, without exposing account details.
    teacher_ids = list({room.teacher for room in rooms if room.teacher})
    teachers = frappe.get_all("IL Member", filters={"name": ["in", teacher_ids], "institute": inst.name},
                              fields=["name", "user"]) if teacher_ids else []
    users = [teacher.user for teacher in teachers if teacher.user]
    profiles = frappe.get_all("IL Public Profile", filters={"user": ["in", users], "kind": "Teacher", "status": "Verified"},
                              fields=["user", "display_name", "qualifications", "profile_image", "socials"]) if users else []
    profiles_by_user = {p.user: {"kind": "Teacher", "display_name": p.display_name,
                               "profile_image": p.profile_image, "qualifications": p.qualifications, "socials": p.socials} for p in profiles}
    teacher_profiles = {t.name: profiles_by_user.get(t.user) for t in teachers}
    for room in rooms:
        from .teaching import rights
        room['permissions'] = rights(room,member)
        room["access"] = access(room, member)
        room["teacher_name"] = frappe.db.get_value("IL Member", room.teacher, "full_name")
        room["teacher_profile"] = teacher_profiles.get(room.teacher)
        room["students"] = frappe.db.count("IL Enrollment", {"classroom": room.name, "active": 1})
    return rooms


@frappe.whitelist(methods=["POST"])
def set_classroom_deleted(name: str, deleted: int):
    """Recoverable removal: preserve enrollments, materials and financial history."""
    _, member, room = classroom_for(name, write=True)
    from .teaching import require
    require(room,member,'delete')
    require_role(member, "Teacher", "Admin")
    if str(deleted) not in ("0", "1"):
        frappe.throw("Invalid classroom state")
    active = 1 - int(deleted)
    if cint(room.active) != active:
        room.active = active
        room.save(ignore_permissions=True)
        room.add_comment("Info", "Classroom restored" if active else "Classroom moved to Deleted classrooms; related records retained")
    return {"name": room.name, "active": active}


@frappe.whitelist()
def classroom_detail(name: str, page: int = 0):
    inst, member, room = classroom_for(name)
    decision = access(room, member)
    from .teaching import rights
    room_data=room.as_dict();room_data['permissions']=rights(room,member)
    result = {"room": room_data, "access": decision, "sessions": [], "materials": [], "feedback": [], "announcements": []}
    if decision["allowed"]:
        for key, dt in (("sessions", "IL Session"), ("materials", "IL Material"), ("feedback", "IL Feedback"), ("announcements", "IL Announcement")):
            result[key] = frappe.get_all(dt, filters={"classroom": name}, fields=["*"], limit_page_length=50,
                                        limit_start=paginate(page, 50), order_by="starts_at desc" if key == "sessions" else "creation desc")
    return result


@frappe.whitelist(methods=["POST"])
def save_classroom(data: dict | str):
    inst, member = identity()
    require_role(member, "Teacher", "Admin")
    data = payload(data)
    if data.get("name"):
        _, _, room = classroom_for(data.name, write=True)
        from .teaching import require
        require(room,member,'edit')
    else:
        room = frappe.new_doc("IL Classroom")
        room.institute = inst.name
        room.owner_type='Institute' if member.role=='Admin' else 'Teacher'
        room.owner_user=member.user if member.role=='Teacher' else None
    if member.role=='Admin':
        from .teaching import institute_profile,approved_teacher
        data.public_provider=institute_profile(inst)
        approved_teacher(inst,data.get('teacher') or room.teacher,data.public_provider)
        room.teacher_access=data.get('teacher_access','Teaching only')
        if room.teacher_access not in ('Teaching only','Full control'):frappe.throw('Invalid teaching permission')
        room.teacher_assignment_active=1
    elif room.owner_type=='Teacher':
        data.public_provider=frappe.db.get_value('IL Public Profile',{'user':member.user,'kind':'Teacher','status':'Verified'},'name')
        room.teacher_access='Full control';room.teacher_assignment_active=1
    else:data.public_provider=room.public_provider
    teacher_name = data.get("teacher") if member.role == "Admin" else member.name
    teacher = scoped("IL Member", teacher_name or room.teacher, inst)
    if teacher.role != "Teacher" or not teacher.active:
        frappe.throw("Select an active teacher")
    room.teacher = teacher.name
    room.title = limited(data.title, 120, "Title")
    room.subject = limited(data.subject, 60, "Subject")
    room.description = limited(data.description, 1500, "Description")
    room.motivation = limited(data.motivation, 30, "Motivation")
    # Tuition belongs to the provider. Platform fees remain Super Admin controlled.
    room.fee=money(data.get('fee',room.fee or 0))
    mode=data.get('billing_type',room.get('billing_type') or 'One-time')
    if mode not in ('One-time','Monthly','Programme module'):frappe.throw('Invalid billing model')
    if mode=='Programme module' and not room.get('programme'):frappe.throw('Add the classroom to a programme first')
    if not room.is_new() and mode!=room.billing_type and frappe.db.exists('IL Enrollment',{'classroom':room.name}):frappe.throw('An enrolled classroom cannot change billing model')
    room.billing_type=mode
    room.exam_date = data.get("exam_date") or None
    for key in ("exam_type", "curriculum", "grade", "teaching_medium"):
        room.set(key, limited(str(data.get(key, "")), 120, key))
    room.font = data.get("font", "sans")
    if room.font not in ("sans", "serif", "handwritten"):
        frappe.throw("Invalid font")
    room.comments_enabled = cint(data.get("comments_enabled", 1))
    for image_field in ("profile_image", "cover_image"):
        if image_field in data:
            room.set(image_field, verified_image(data[image_field], member))
    if member.role == "Admin":
        room.allow_teacher_access_override = cint(data.get("allow_teacher_access_override", 0))
        if data.get("lms_course"):
            frappe.get_doc("LMS Course", data.lms_course)  # Site-local course only.
        room.lms_course = data.get("lms_course") or None
    from .catalog import validate_publication
    validate_publication(room, member, data)
    room.save(ignore_permissions=True)
    return room.name


def verified_image(url, member):
    if not url:
        return ""
    file = frappe.db.get_value("File", {"file_url": url}, ["name", "owner", "file_size", "file_name", "is_private"], as_dict=True)
    if not file or (file.owner != frappe.session.user and member.role != "Admin"):
        frappe.throw("Upload an image using your account")
    if file.file_size > 5 * 1024 * 1024 or not file.file_name.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
        frappe.throw("Use a WebP, PNG or JPEG image up to 5 MB")
    if file.is_private:
        frappe.throw("Branding/news images must be uploaded as public images")
    return url


@frappe.whitelist(methods=["POST"])
def save_session(data: dict | str):
    data = payload(data)
    inst, member, room = classroom_for(data.classroom, write=True)
    doc = scoped("IL Session", data.name, inst) if data.get("name") else frappe.new_doc("IL Session")
    if not doc.is_new() and doc.classroom != room.name:
        frappe.throw("Cannot move sessions between classrooms")
    doc.update({"institute": inst.name, "classroom": room.name,
                "title": limited(data.title, 120, "Title"), "description": limited(data.description, 2000, "Description"),
                "starts_at": get_datetime(data.starts_at), "ends_at": get_datetime(data.ends_at),
                "mode": data.mode, "location": limited(data.location, 200, "Location"),
                "comments": data.get("comments", "Inherit"), "status": data.get("status", "Scheduled")})
    if doc.ends_at <= doc.starts_at:
        frappe.throw("End time must be after start time")
    if "youtube_id" in data:
        doc.youtube_id = youtube_id(data.youtube_id) if data.youtube_id else ""
    from .teaching_rules import meeting_link
    doc.meeting_provider=data.get('meeting_provider','YouTube')
    doc.meeting_url=meeting_link(doc.meeting_provider,data.get('meeting_url','')) if doc.mode=='Online' else ''
    if doc.meeting_provider!='YouTube':doc.youtube_id=''
    elif doc.meeting_url:doc.youtube_id=youtube_id(doc.meeting_url)
    doc.save(ignore_permissions=True)
    from .notifications import classroom_event
    classroom_event(room, f"session:{doc.name}:{doc.modified}", f"{doc.title}: {doc.status}. {doc.starts_at} (Asia/Colombo)")
    return doc.name


@frappe.whitelist()
def schedule(page: int = 0, starts_on: str | None = None, ends_on: str | None = None):
    inst, member = identity()
    names = frappe.get_all("IL Classroom", filters=room_filters(inst, member), pluck="name")
    # Timetable exposes no protected media URLs.
    filters = {"classroom": ["in", names or ["__none__"]]}
    if starts_on and ends_on:
        if (getdate(ends_on) - getdate(starts_on)).days > 62:
            frappe.throw("Request at most two months at a time")
        filters["starts_at"] = ["between", [str(getdate(starts_on)) + " 00:00:00", str(getdate(ends_on)) + " 23:59:59"]]
    return frappe.get_all("IL Session", filters=filters,
                          fields=["name", "classroom", "title", "starts_at", "ends_at", "mode", "status", "location"],
                          order_by="starts_at desc", limit_start=paginate(page, 50), limit_page_length=50)


@frappe.whitelist(methods=["POST"])
def add_material(data: dict | str):
    data = payload(data)
    inst, member, room = classroom_for(data.classroom, write=True)
    if data.kind not in ('Document','Recording','Link'):
        frappe.throw('Choose a valid resource type')
    attachment={}
    if data.kind=='Document' and data.get('file_id'):
        from .materials import attachment_fields
        attachment=attachment_fields(data,room)
    elif data.kind=='Document' and data.get('download_policy')=='View only':
        frappe.throw('Upload the document to use LMS view-only access; external links use provider permissions')
    if data.get("session"):
        session = scoped("IL Session", data.session, inst)
        if session.classroom != room.name:
            frappe.throw("Session belongs to a different classroom")
    doc = frappe.get_doc({"doctype": "IL Material", "institute": inst.name, "classroom": room.name,
        "session": data.get("session"), "title": limited(data.title, 120, "Title"), "kind": data.kind,
        "description": limited(data.description, 1000, "Description"),
        "youtube_id": youtube_id(data.url) if data.kind == "Recording" else "",
        "url": safe_url(data.url, False) if data.kind != "Recording" and not attachment else "",
        **attachment}).insert(ignore_permissions=True)
    from .notifications import classroom_event
    classroom_event(room, f"material:{doc.name}", f"New material: {doc.title}")
    return doc.name


@frappe.whitelist(methods=["POST"])
def post_announcement(data: dict | str):
    data = payload(data)
    inst, _, room = classroom_for(data.classroom, write=True)
    doc = frappe.get_doc({"doctype": "IL Announcement", "institute": inst.name, "classroom": room.name,
        "headline": limited(data.headline, 80, "Headline"), "body": limited(data.body, 2000, "Announcement")}).insert(ignore_permissions=True)
    from .notifications import classroom_event
    classroom_event(room, f"announcement:{doc.name}", doc.headline)
    return doc.name


@frappe.whitelist(methods=["POST"])
def post_feedback(session: str, body: str):
    inst, member = identity()
    require_role(member, "Student")
    session = scoped("IL Session", session, inst)
    _, _, room = accessible_room(session.classroom)
    enabled = session.comments == "Enabled" or (session.comments == "Inherit" and room.comments_enabled)
    if not enabled or session.status == "Cancelled" or get_datetime(session.ends_at) > now_datetime():
        frappe.throw("Feedback is unavailable for this session")
    body = limited(body, 1000, "Feedback")
    if not body:
        frappe.throw("Write your feedback first")
    return frappe.get_doc({"doctype": "IL Feedback", "institute": inst.name, "classroom": room.name,
                          "session": session.name, "student": member.name, "body": body}).insert(ignore_permissions=True).name


@frappe.whitelist()
def news(page: int = 0):
    inst, _ = identity()
    names = frappe.get_all("IL News", filters={"institute": inst.name, "starts_on": ["<=", today()], "ends_on": [">=", today()], "creation": [">", now_datetime() - timedelta(days=30)]},
                           pluck="name", limit_start=paginate(page), limit_page_length=24, order_by="creation desc")
    return [frappe.get_doc("IL News", name).as_dict() for name in names]


@frappe.whitelist(methods=["POST"])
def publish_news(data: dict | str):
    inst, member = identity()
    require_role(member, "Teacher", "Admin")
    data = payload(data)
    if not 1 <= len(data.get("images", [])) <= 5:
        frappe.throw("Add 1 to 5 images")
    if getdate(data.ends_on) < getdate(data.starts_on):
        frappe.throw("End date must follow start date")
    doc = frappe.get_doc({"doctype": "IL News", "institute": inst.name, "author": member.name,
        "headline": limited(data.headline, 80, "Headline"), "description": limited(data.description, 240, "Description"),
        "cta_label": limited(data.cta_label, 24, "Button label"), "cta_url": safe_url(data.cta_url),
        "starts_on": data.starts_on, "ends_on": data.ends_on,
        "images": [{"image": verified_image(i["image"], member), "alt": limited(i.get("alt"), 120, "Image description") or data.headline} for i in data.images]})
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def members(page: int = 0, role: str | None = None, search: str | None = None):
    inst, member = identity()
    require_role(member, "Admin")
    filters = {"institute": inst.name}
    if role:
        filters["role"] = role
    if search:
        filters["full_name"] = ["like", f"%{str(search)[:80]}%"]
    return frappe.get_all("IL Member", filters=filters, fields=["*"], limit_start=paginate(page, 50), limit_page_length=50)


@frappe.whitelist(methods=["POST"])
def add_member(data: dict | str):
    inst, admin = identity()
    require_role(admin, "Admin")
    data = payload(data)
    if data.role == "Student":
        frappe.throw("Students must sign up and request to join themselves", frappe.PermissionError)
    if data.role not in ("Teacher", "Admin"):
        frappe.throw("Invalid role")
    if data.user in ("Administrator", "Guest"):
        frappe.throw("Reserved system accounts cannot be added as institute members")
    if not frappe.db.exists("User", data.user):
        frappe.throw("Teachers apply and verify their own accounts before joining an institute")
    if data.role == "Teacher":
        provider = frappe.db.get_value("IL Public Profile", {"workspace": inst.name, "kind": "Institute", "status": "Verified"}, "name")
        verified = frappe.db.exists("IL Public Profile", {"user": data.user, "kind": "Teacher", "status": "Verified"})
        accepted = provider and frappe.db.exists("IL Profile Relationship", {"profile": provider, "user": data.user, "kind": "Teacher membership", "status": "Active"})
        if not verified or not accepted:
            frappe.throw("An approved teacher profile and accepted institute membership are required", frappe.PermissionError)
    user = frappe.get_doc("User", data.user)
    if "System Manager" in frappe.get_roles(user.name) and "System Manager" not in frappe.get_roles():
        frappe.throw("Only a site operator may change a system manager", frappe.PermissionError)
    user.append_roles(f"Institute {data.role}")
    native_role = {"Teacher": "Course Creator", "Admin": "Moderator", "Student": "LMS Student"}[data.role]
    if frappe.db.exists("Role", native_role):
        user.append_roles(native_role)
    user.save(ignore_permissions=True)
    prefix, width = ("ST", 5) if data.role == "Student" else ("TC", 4) if data.role == "Teacher" else ("AD", 4)
    name = make_autoname(f"{prefix}-{inst.code}-.{'#' * width}")
    doc = frappe.get_doc({"doctype": "IL Member", "institute": inst.name, "user": data.user,
        "role": data.role, "full_name": limited(data.full_name, 100, "Name"), "phone": data.phone,
        "language": data.get("language", "en"), "whatsapp_opt_in": 0, "active": 1})
    doc.insert(ignore_permissions=True, set_name=name)
    return doc.name


@frappe.whitelist(methods=["POST"])
def set_member_active(member_id: str, active: int):
    inst, actor = identity()
    require_role(actor, "Admin")
    member = scoped("IL Member", member_id, inst)
    if member.user == frappe.session.user:
        frappe.throw("You cannot deactivate your own membership")
    member.active = int(bool(cint(active)))
    member.save(ignore_permissions=True)
    # One institute per site: disabling the login also blocks the upstream LMS.
    if member.user != "Administrator" and "System Manager" not in frappe.get_roles(member.user):
        user = frappe.get_doc("User", member.user)
        user.enabled = member.active
        user.save(ignore_permissions=True)
        if not member.active:
            frappe.sessions.clear_sessions(user=member.user, force=True)


@frappe.whitelist()
def teachers(search: str = ""):
    inst, member = identity()
    require_role(member, "Admin", "Teacher")
    filters = {"institute": inst.name, "active": 1, "role": "Teacher"}
    if member.role == "Teacher":
        filters["name"] = member.name
    else:
        from .teaching import institute_profile
        users=frappe.get_all('IL Profile Relationship',filters={'profile':institute_profile(inst),'kind':'Teacher membership','status':'Active'},pluck='user')
        filters['user']=['in',users or ['__none__']]
        if search:filters["full_name"] = ["like", f"%{str(search)[:80]}%"]
    return frappe.get_all("IL Member", filters=filters, fields=["name", "full_name"], limit_page_length=100)


@frappe.whitelist(methods=["POST"])
def notification_preferences(phone: str, opted_in: int, language: str = "en"):
    inst, member = identity()
    if not member.name:
        frappe.throw("An institute membership is required")
    import re
    if phone and not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        frappe.throw("Use international phone format, e.g. +94771234567")
    if language not in ("en", "si", "ta"):
        frappe.throw("Unsupported language")
    if cint(opted_in):
        from .private_contact import own
        from .private_contact_rules import normalize,guardian_updates_without_otp
        details=own()
        guardian_exempt=False
        if member.role=='Student' and not details:frappe.throw('Complete private contact and guardian details in My profile first')
        if details:
            values=details.as_dict();values.update(whatsapp_phone=phone,whatsapp_opt_in=True)
            try:normalize(values,'Student' if member.role=='Student' else 'Teacher')
            except ValueError as e:frappe.throw(str(e))
            guardian_exempt=guardian_updates_without_otp(values,'Student' if member.role=='Student' else 'Teacher')
        if not guardian_exempt and not frappe.db.exists('IL Verified Phone',{'user':member.user,'phone':phone}):frappe.throw('Verify this WhatsApp number first')
    doc = frappe.get_doc("IL Member", member.name)
    doc.update({"phone": phone, "whatsapp_opt_in": cint(opted_in), "language": language})
    doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def enroll(data: dict | str):
    data = payload(data)
    inst, member, room = classroom_for(data.classroom, write=True)
    student = scoped("IL Member", data.student, inst)
    if student.role != "Student" or not student.active:
        frappe.throw("Select an active student")
    return create_enrollment(inst, room, student, data.get("installments", []))


def create_enrollment(inst, room, student, installments):
    frappe.db.sql('SELECT name FROM `tabIL Classroom` WHERE name=%s FOR UPDATE',(room.name,))
    room.reload()
    if room.get('programme'):frappe.throw('Enroll in the complete programme; modules are not charged separately')
    fee = money(0 if room.get("fee_mode") == "Free" else room.fee)
    if not inst.get("school_mode") and fee and (not installments or len(installments) > 24 or sum(money(i["amount"]) for i in installments) != fee):
        frappe.throw("Installments must total the classroom fee (maximum 24)")
    if not inst.get("school_mode") and any(money(i["amount"]) <= 0 for i in installments):
        frappe.throw("Each installment must be greater than zero")
    from .class_billing import invoice_split
    if inst.get("school_mode"):
        installments=[]
    elif not fee:
        installments=[{"amount":0,"due_date":today()}]
    if room.get('billing_type')=='Monthly':installments=[{'amount':fee,'due_date':today()}]
    quotes=[(item,invoice_split(inst,money(item["amount"]),student.user,room=room)) for item in sorted(installments,key=lambda x:x["due_date"])]
    total=sum((q["amount"] for _,q in quotes if q),money(0))
    doc = frappe.get_doc({"doctype": "IL Enrollment", "institute": inst.name, "classroom": room.name,
                         "student": student.name, "fee": total, "active": 1, "access_override": "Automatic"}).insert(ignore_permissions=True)
    for idx,(item,quote) in enumerate(quotes,1):
        extra={}
        if room.get('billing_type')=='Monthly':
            import hashlib
            month=today()[:7]
            extra={'billing_month':month,'billing_key':hashlib.sha256((doc.name+':'+month).encode()).hexdigest()}
        if quote and quote["amount"] > 0:
            frappe.get_doc({"doctype":"IL Invoice","institute":inst.name,"enrollment":doc.name,
                "classroom":room.name,"student":student.name,**quote,**extra,
                "due_date":getdate(item["due_date"]),"installment":idx,"status":"Unpaid"}).insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def enrollments(classroom: str, page: int = 0):
    inst, _, room = classroom_for(classroom, write=True)
    return frappe.get_all("IL Enrollment", filters={"classroom": room.name}, fields=["*"], limit_start=paginate(page, 100), limit_page_length=100)


@frappe.whitelist(methods=["POST"])
def set_access(enrollment: str, override: str, reason: str, grace_until: str | None = None):
    inst, member = identity()
    doc = scoped("IL Enrollment", enrollment, inst)
    _, _, room = classroom_for(doc.classroom, write=True)
    if member.role != "Admin" and not room.allow_teacher_access_override and not (room.get("owner_type")=="Teacher" and room.get("owner_user")==member.user):
        frappe.throw("Only an administrator may override access for this classroom", frappe.PermissionError)
    if override not in ("Automatic", "Open", "Closed") or not (reason or "").strip():
        frappe.throw("Choose an access rule and provide a reason")
    before = json.dumps({"access_override": doc.access_override, "grace_until": str(doc.grace_until)})
    doc.update({"access_override": override, "grace_until": getdate(grace_until) if grace_until else None,
                "override_reason": limited(reason, 500, "Reason")})
    doc.save(ignore_permissions=True)
    frappe.get_doc({"doctype": "IL Access Audit", "institute": inst.name, "enrollment": doc.name,
        "actor": frappe.session.user, "before_state": before,
        "after_state": json.dumps({"access_override": override, "grace_until": str(doc.grace_until)}), "reason": reason}).insert(ignore_permissions=True)


@frappe.whitelist()
def invoices(page: int = 0):
    inst, member = identity()
    filters = {"institute": inst.name}
    if member.role == "Student":
        filters["student"] = member.name
    elif member.role in ("Teacher","Admin"):
        filters["classroom"] = ["in", frappe.get_all("IL Classroom", filters=room_filters(inst, member), pluck="name") or ["__none__"]]
    rows=frappe.get_all("IL Invoice", filters=filters, fields=["*"], order_by="due_date asc", limit_start=paginate(page, 50), limit_page_length=50)
    for row in rows:
        wallet=frappe.db.get_value('IL Wallet',row.payout_wallet,['beneficiary','owner_user'],as_dict=True) if row.payout_wallet else None
        row['recipient']=inst.title if not wallet or wallet.beneficiary=='Institute' else frappe.db.get_value('User',wallet.owner_user,'full_name')
        bundle=frappe.db.get_value('IL Enrollment',row.enrollment,'programme_enrollment')
        row['programme']=frappe.db.get_value('IL Programme Enrollment',bundle,'programme') if bundle else None
    return rows


@frappe.whitelist()
def notifications(page: int = 0):
    inst, member = identity()
    filters = {"institute": inst.name}
    if member.role != "Admin":
        filters["recipient"] = member.name
    return frappe.get_all("IL Notification", filters=filters, fields=["name", "body", "status", "creation", "recipient", "channel"],
                          limit_start=paginate(page, 50), limit_page_length=50, order_by="creation desc")


@frappe.whitelist()
def dashboard_summary():
    inst, member = identity()
    filters = {"institute": inst.name}
    if member.role == "Student":
        filters["student"] = member.name
    elif member.role in ("Teacher","Admin"):
        filters["classroom"] = ["in", frappe.get_all("IL Classroom", filters=room_filters(inst, member), pluck="name") or ["__none__"]]
    totals = frappe.get_all("IL Invoice", filters=filters, fields=["status", "sum(amount) as total", "count(name) as count"], group_by="status")
    return {"classrooms": frappe.db.count("IL Classroom", room_filters(inst, member)),
            "paid_total": sum(float(row.total or 0) for row in totals if row.status == "Paid"),
            "outstanding_total": sum(float(row.total or 0) for row in totals if row.status != "Paid"),
            "paid_count": sum(row.count for row in totals if row.status == "Paid"),
            "unpaid_count": sum(row.count for row in totals if row.status != "Paid")}


@frappe.whitelist(methods=["POST"])
def save_branding(data: dict | str):
    inst, member = identity()
    require_role(member, "Admin")
    data = payload(data)
    inst.title = limited(data.title, 100, "Institute name")
    if "logo" in data:
        inst.logo = verified_image(data.logo, member)
    import re
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", data.get("accent", "")):
        frappe.throw("Choose a valid brand color")
    inst.accent = data.accent
    inst.save(ignore_permissions=True)
    return bootstrap()
