-- Tenant isolation and role-aware access for the primary application schema.

begin;

grant usage on schema private to authenticated, service_role;

create or replace function private.is_platform_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select (select auth.uid()) is not null and exists (
    select 1
    from public.platform_roles pr
    where pr.user_id = (select auth.uid())
      and pr.role = 'super_admin'
      and pr.active
  )
$$;

create or replace function private.has_membership(
  target_institution_id uuid,
  allowed_roles text[] default null
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select (select auth.uid()) is not null and exists (
    select 1
    from public.institution_memberships m
    where m.institution_id = target_institution_id
      and m.user_id = (select auth.uid())
      and m.status = 'active'
      and (allowed_roles is null or m.role = any(allowed_roles))
  )
$$;

create or replace function private.is_institute_admin(target_institution_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select private.is_platform_admin()
      or private.has_membership(target_institution_id, array['institute_admin']::text[])
$$;

create or replace function private.owns_membership(target_membership_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select (select auth.uid()) is not null and exists (
    select 1
    from public.institution_memberships m
    where m.id = target_membership_id
      and m.user_id = (select auth.uid())
      and m.status = 'active'
  )
$$;

create or replace function private.can_manage_course(target_course_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.courses c
    where c.id = target_course_id
      and (
        private.is_institute_admin(c.institution_id)
        or (
          c.created_by = (select auth.uid())
          and private.has_membership(c.institution_id, array['teacher']::text[])
        )
      )
  )
$$;

create or replace function private.can_view_course(target_course_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.courses c
    where c.id = target_course_id
      and (
        (c.active and c.published)
        or private.can_manage_course(c.id)
        or private.has_membership(c.institution_id, null)
      )
  )
$$;

create or replace function private.can_teach_class(target_class_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.classes c
    left join public.institution_memberships teacher
      on teacher.id = c.teacher_membership_id
     and teacher.institution_id = c.institution_id
    where c.id = target_class_id
      and (
        private.is_platform_admin()
        or (
          c.owner_type = 'institution'
          and private.has_membership(c.institution_id, array['institute_admin']::text[])
        )
        or (
          c.owner_type = 'teacher'
          and c.owner_user_id = (select auth.uid())
          and private.has_membership(c.institution_id, array['teacher']::text[])
        )
        or (
          c.teacher_assignment_active
          and teacher.user_id = (select auth.uid())
          and teacher.role = 'teacher'
          and teacher.status = 'active'
        )
      )
  )
$$;

create or replace function private.can_manage_class(target_class_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.classes c
    left join public.institution_memberships teacher
      on teacher.id = c.teacher_membership_id
     and teacher.institution_id = c.institution_id
    where c.id = target_class_id
      and (
        private.is_platform_admin()
        or (
          c.owner_type = 'institution'
          and private.has_membership(c.institution_id, array['institute_admin']::text[])
        )
        or (
          c.owner_type = 'teacher'
          and c.owner_user_id = (select auth.uid())
          and private.has_membership(c.institution_id, array['teacher']::text[])
        )
        or (
          c.teacher_assignment_active
          and c.teacher_access = 'full_control'
          and teacher.user_id = (select auth.uid())
          and teacher.role = 'teacher'
          and teacher.status = 'active'
        )
      )
  )
$$;

create or replace function private.can_view_class(target_class_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select private.can_teach_class(target_class_id) or exists (
    select 1
    from public.enrollments e
    join public.institution_memberships student
      on student.id = e.student_membership_id
     and student.institution_id = e.institution_id
    where e.class_id = target_class_id
      and e.status = 'active'
      and student.user_id = (select auth.uid())
      and student.role = 'student'
      and student.status = 'active'
  )
$$;

create or replace function private.can_access_class_content(target_class_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select private.can_teach_class(target_class_id) or exists (
    select 1
    from public.enrollments e
    join public.classes c
      on c.id = e.class_id
     and c.institution_id = e.institution_id
    join public.institution_memberships student
      on student.id = e.student_membership_id
     and student.institution_id = e.institution_id
    where e.class_id = target_class_id
      and e.status = 'active'
      and student.user_id = (select auth.uid())
      and student.role = 'student'
      and student.status = 'active'
      and e.access_override <> 'closed'
      and (
        e.access_override = 'open'
        or e.fee_minor = 0
        or (e.grace_until is not null and e.grace_until >= current_date)
        or (
          exists (
            select 1
            from public.invoices paid
            where paid.institution_id = e.institution_id
              and (
                paid.enrollment_id = e.id
                or (
                  e.programme_enrollment_id is not null
                  and paid.programme_enrollment_id = e.programme_enrollment_id
                )
              )
              and (
                c.billing_type <> 'monthly'
                or paid.billing_month = date_trunc('month', current_date)::date
              )
              and paid.status = 'paid'
          )
          and not exists (
            select 1
            from public.invoices due_invoice
            where due_invoice.institution_id = e.institution_id
              and (
                due_invoice.enrollment_id = e.id
                or (
                  e.programme_enrollment_id is not null
                  and due_invoice.programme_enrollment_id = e.programme_enrollment_id
                )
              )
              and (
                c.billing_type <> 'monthly'
                or due_invoice.billing_month = date_trunc('month', current_date)::date
              )
              and due_invoice.status not in ('paid', 'void')
              and due_invoice.due_date <= current_date
          )
        )
      )
  )
$$;

create or replace function private.can_view_membership(target_membership_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select private.owns_membership(target_membership_id) or exists (
    select 1
    from public.institution_memberships target
    where target.id = target_membership_id
      and (
        private.is_institute_admin(target.institution_id)
        or (
          target.role = 'student'
          and exists (
            select 1
            from public.enrollments e
            where e.student_membership_id = target.id
              and e.status = 'active'
              and private.can_teach_class(e.class_id)
          )
        )
      )
  )
$$;

create or replace function private.can_view_programme(target_programme_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.programmes p
    where p.id = target_programme_id
      and (
        (p.active and p.published)
        or private.is_institute_admin(p.institution_id)
        or exists (
          select 1
          from public.programme_modules pm
          where pm.programme_id = p.id
            and private.can_teach_class(pm.class_id)
        )
        or exists (
          select 1
          from public.programme_enrollments pe
          join public.institution_memberships student
            on student.id = pe.student_membership_id
          where pe.programme_id = p.id
            and pe.status = 'active'
            and student.user_id = (select auth.uid())
        )
      )
  )
$$;

create or replace function private.can_manage_exam(target_exam_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.exams e
    where e.id = target_exam_id
      and private.can_manage_class(e.class_id)
  )
$$;

create or replace function private.can_view_support_ticket(target_ticket_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.support_tickets t
    where t.id = target_ticket_id
      and (
        t.requester_user_id = (select auth.uid())
        or private.is_institute_admin(t.institution_id)
        or exists (
          select 1 from public.platform_roles pr
          where pr.user_id = (select auth.uid())
            and pr.role in ('super_admin', 'support_admin')
            and pr.active
        )
      )
  )
$$;

revoke all on function private.is_platform_admin() from public, anon;
revoke all on function private.has_membership(uuid, text[]) from public, anon;
revoke all on function private.is_institute_admin(uuid) from public, anon;
revoke all on function private.owns_membership(uuid) from public, anon;
revoke all on function private.can_manage_course(uuid) from public, anon;
revoke all on function private.can_view_course(uuid) from public, anon;
revoke all on function private.can_teach_class(uuid) from public, anon;
revoke all on function private.can_manage_class(uuid) from public, anon;
revoke all on function private.can_view_class(uuid) from public, anon;
revoke all on function private.can_access_class_content(uuid) from public, anon;
revoke all on function private.can_view_membership(uuid) from public, anon;
revoke all on function private.can_view_programme(uuid) from public, anon;
revoke all on function private.can_manage_exam(uuid) from public, anon;
revoke all on function private.can_view_support_ticket(uuid) from public, anon;

grant execute on function private.is_platform_admin() to authenticated, service_role;
grant execute on function private.has_membership(uuid, text[]) to authenticated, service_role;
grant execute on function private.is_institute_admin(uuid) to authenticated, service_role;
grant execute on function private.owns_membership(uuid) to authenticated, service_role;
grant execute on function private.can_manage_course(uuid) to authenticated, service_role;
grant execute on function private.can_view_course(uuid) to authenticated, service_role;
grant execute on function private.can_teach_class(uuid) to authenticated, service_role;
grant execute on function private.can_manage_class(uuid) to authenticated, service_role;
grant execute on function private.can_view_class(uuid) to authenticated, service_role;
grant execute on function private.can_access_class_content(uuid) to authenticated, service_role;
grant execute on function private.can_view_membership(uuid) to authenticated, service_role;
grant execute on function private.can_view_programme(uuid) to authenticated, service_role;
grant execute on function private.can_manage_exam(uuid) to authenticated, service_role;
grant execute on function private.can_view_support_ticket(uuid) to authenticated, service_role;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'profiles', 'platform_roles', 'institutions', 'institution_memberships',
    'courses', 'course_modules', 'lessons', 'programmes', 'classes',
    'class_sessions', 'materials', 'programme_modules', 'programme_enrollments',
    'enrollments', 'attendance', 'assignments', 'assignment_submissions',
    'exams', 'exam_questions', 'exam_attempts', 'exam_answers', 'exam_results',
    'announcements', 'feedback', 'news', 'news_images', 'invoices', 'payments',
    'notifications', 'support_tickets', 'support_replies', 'audit_events',
    'outbox_events'
  ]
  loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format('alter table public.%I force row level security', table_name);
  end loop;
end;
$$;

alter table private.user_contacts enable row level security;
alter table private.user_contacts force row level security;
alter table private.verified_phones enable row level security;
alter table private.verified_phones force row level security;

revoke all on all tables in schema public from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;
grant usage on schema public to anon, authenticated, service_role;
grant all on all tables in schema public to service_role;
grant all on all tables in schema private to service_role;

grant select (id, username, full_name, profile_kind, status, language, country, bio,
  tagline, curriculum, languages, grades, qualifications, socials, avatar_path,
  cover_path, created_at, updated_at)
on public.profiles to anon, authenticated;
grant update (username, full_name, language, country, bio, tagline, curriculum,
  languages, grades, qualifications, socials, avatar_path, cover_path)
on public.profiles to authenticated;

grant select on public.platform_roles, public.institutions,
  public.institution_memberships, public.courses, public.course_modules,
  public.lessons, public.programmes, public.classes, public.class_sessions,
  public.materials, public.programme_modules, public.programme_enrollments,
  public.enrollments, public.attendance, public.assignments,
  public.assignment_submissions, public.exams, public.exam_attempts,
  public.exam_answers, public.exam_results, public.announcements, public.feedback,
  public.news, public.news_images, public.invoices, public.payments,
  public.notifications, public.support_tickets, public.support_replies,
  public.audit_events
to authenticated;

grant select (id, institution_id, exam_id, position, kind, prompt, options, marks,
  created_at, updated_at)
on public.exam_questions to authenticated;
grant update (read_at) on public.notifications to authenticated;
grant insert on public.institutions, public.courses, public.classes,
  public.class_sessions, public.enrollments, public.attendance
to authenticated;
grant update (title, description, published, active) on public.courses to authenticated;
grant update (status, note) on public.attendance to authenticated;

create policy profiles_own_select
on public.profiles for select to anon, authenticated
using (
  id = (select auth.uid())
  or (status = 'verified' and profile_kind in ('teacher', 'institute'))
);

create policy profiles_own_update
on public.profiles for update to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()));

create policy platform_roles_own_or_platform_select
on public.platform_roles for select to authenticated
using (user_id = (select auth.uid()) or private.is_platform_admin());

create policy institutions_member_select
on public.institutions for select to authenticated
using (private.is_platform_admin() or private.has_membership(id, null));

create policy institution_memberships_scoped_select
on public.institution_memberships for select to authenticated
using (private.can_view_membership(id));

create policy courses_scoped_select
on public.courses for select to authenticated
using (private.can_view_course(id));

create policy courses_authorized_insert
on public.courses for insert to authenticated
with check (
  created_by = (select auth.uid())
  and (
    private.is_institute_admin(institution_id)
    or private.has_membership(institution_id, array['teacher']::text[])
  )
);

create policy courses_authorized_update
on public.courses for update to authenticated
using (private.can_manage_course(id))
with check (
  created_by = (select auth.uid())
  or private.is_institute_admin(institution_id)
);

create policy course_modules_scoped_select
on public.course_modules for select to authenticated
using (private.can_view_course(course_id));

create policy lessons_scoped_select
on public.lessons for select to authenticated
using (
  exists (
    select 1 from public.course_modules cm
    where cm.id = lessons.module_id
      and private.can_view_course(cm.course_id)
  )
);

create policy programmes_scoped_select
on public.programmes for select to authenticated
using (private.can_view_programme(id));

create policy classes_catalog_or_member_select
on public.classes for select to authenticated
using ((active and published) or private.can_view_class(id));

create policy classes_admin_insert
on public.classes for insert to authenticated
with check (
  private.is_institute_admin(institution_id)
  and (
    teacher_membership_id is null
    or exists (
      select 1 from public.institution_memberships teacher
      where teacher.id = teacher_membership_id
        and teacher.institution_id = classes.institution_id
        and teacher.role = 'teacher'
        and teacher.status = 'active'
    )
  )
);

create policy class_sessions_member_select
on public.class_sessions for select to authenticated
using (private.can_view_class(class_id));

create policy class_sessions_manager_insert
on public.class_sessions for insert to authenticated
with check (private.can_manage_class(class_id));

create policy materials_content_select
on public.materials for select to authenticated
using (private.can_access_class_content(class_id));

create policy programme_modules_scoped_select
on public.programme_modules for select to authenticated
using (private.can_view_programme(programme_id));

create policy programme_enrollments_scoped_select
on public.programme_enrollments for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or private.is_institute_admin(institution_id)
  or exists (
    select 1 from public.programme_modules pm
    where pm.programme_id = programme_enrollments.programme_id
      and private.can_teach_class(pm.class_id)
  )
);

create policy enrollments_scoped_select
on public.enrollments for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or private.can_teach_class(class_id)
);

create policy enrollments_admin_insert
on public.enrollments for insert to authenticated
with check (
  private.is_institute_admin(institution_id)
  and exists (
    select 1 from public.institution_memberships student
    where student.id = student_membership_id
      and student.institution_id = enrollments.institution_id
      and student.role = 'student'
      and student.status = 'active'
  )
);

create policy attendance_scoped_select
on public.attendance for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or private.can_teach_class(class_id)
);

create policy attendance_teacher_insert
on public.attendance for insert to authenticated
with check (
  private.can_teach_class(class_id)
  and recorded_by = (select auth.uid())
);

create policy attendance_teacher_update
on public.attendance for update to authenticated
using (private.can_teach_class(class_id))
with check (private.can_teach_class(class_id));

create policy assignments_scoped_select
on public.assignments for select to authenticated
using (
  private.can_manage_class(class_id)
  or (status = 'published' and private.can_access_class_content(class_id))
);

create policy assignment_submissions_scoped_select
on public.assignment_submissions for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or exists (
    select 1 from public.assignments a
    where a.id = assignment_submissions.assignment_id
      and private.can_manage_class(a.class_id)
  )
);

create policy exams_scoped_select
on public.exams for select to authenticated
using (
  private.can_manage_class(class_id)
  or (status = 'published' and private.can_access_class_content(class_id))
);

create policy exam_questions_scoped_select
on public.exam_questions for select to authenticated
using (
  private.can_manage_exam(exam_id)
  or exists (
    select 1 from public.exams e
    where e.id = exam_questions.exam_id
      and e.status = 'published'
      and private.can_access_class_content(e.class_id)
  )
);

create policy exam_attempts_scoped_select
on public.exam_attempts for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or private.can_manage_exam(exam_id)
);

create policy exam_answers_scoped_select
on public.exam_answers for select to authenticated
using (
  exists (
    select 1
    from public.exam_attempts ea
    where ea.id = exam_answers.attempt_id
      and (
        private.owns_membership(ea.student_membership_id)
        or private.can_manage_exam(ea.exam_id)
      )
  )
);

create policy exam_results_scoped_select
on public.exam_results for select to authenticated
using (
  private.can_manage_exam(exam_id)
  or (published_at is not null and private.owns_membership(student_membership_id))
);

create policy announcements_content_select
on public.announcements for select to authenticated
using (private.can_access_class_content(class_id));

create policy feedback_scoped_select
on public.feedback for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or private.can_teach_class(class_id)
);

create policy news_member_select
on public.news for select to authenticated
using (
  private.is_institute_admin(institution_id)
  or (
    published
    and starts_on <= current_date
    and ends_on >= current_date
    and private.has_membership(institution_id, null)
  )
);

create policy news_images_member_select
on public.news_images for select to authenticated
using (
  exists (
    select 1 from public.news n
    where n.id = news_images.news_id
      and (
        private.is_institute_admin(n.institution_id)
        or (
          n.published
          and n.starts_on <= current_date
          and n.ends_on >= current_date
          and private.has_membership(n.institution_id, null)
        )
      )
  )
);

create policy invoices_scoped_select
on public.invoices for select to authenticated
using (
  private.owns_membership(student_membership_id)
  or private.is_institute_admin(institution_id)
);

create policy payments_scoped_select
on public.payments for select to authenticated
using (
  exists (
    select 1 from public.invoices i
    where i.id = payments.invoice_id
      and (
        private.owns_membership(i.student_membership_id)
        or private.is_institute_admin(i.institution_id)
      )
  )
);

create policy notifications_scoped_select
on public.notifications for select to authenticated
using (
  recipient_user_id = (select auth.uid())
  or (institution_id is not null and private.is_institute_admin(institution_id))
  or private.is_platform_admin()
);

create policy notifications_recipient_update
on public.notifications for update to authenticated
using (recipient_user_id = (select auth.uid()))
with check (recipient_user_id = (select auth.uid()));

create policy support_tickets_scoped_select
on public.support_tickets for select to authenticated
using (private.can_view_support_ticket(id));

create policy support_replies_scoped_select
on public.support_replies for select to authenticated
using (private.can_view_support_ticket(ticket_id));

create policy audit_events_admin_select
on public.audit_events for select to authenticated
using (
  private.is_platform_admin()
  or (institution_id is not null and private.is_institute_admin(institution_id))
);

create policy institutions_platform_insert
on public.institutions for insert to authenticated
with check (private.is_platform_admin());

create or replace view public.students
with (security_invoker = true, security_barrier = true)
as
select
  m.id,
  m.institution_id,
  m.user_id as profile_id,
  m.member_code as student_code,
  m.display_name as full_name,
  m.status,
  m.language,
  m.created_at,
  m.updated_at
from public.institution_memberships m
where m.role = 'student';

create or replace view public.teachers
with (security_invoker = true, security_barrier = true)
as
select
  m.id,
  m.institution_id,
  m.user_id as profile_id,
  m.member_code as teacher_code,
  m.display_name as full_name,
  m.status,
  m.language,
  m.created_at,
  m.updated_at
from public.institution_memberships m
where m.role = 'teacher';

revoke all on public.students, public.teachers from public, anon;
grant select on public.students, public.teachers to authenticated, service_role;

comment on function private.can_access_class_content(uuid) is
  'Authoritative classroom-content gate: membership, override, free/grace, and due-invoice checks.';
comment on view public.students is 'Read-only compatibility projection over authoritative institution_memberships.';
comment on view public.teachers is 'Read-only compatibility projection over authoritative institution_memberships.';

commit;
