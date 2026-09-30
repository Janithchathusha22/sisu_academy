-- Main application data. Apply in Supabase SQL Editor before starting the API.
create extension if not exists pgcrypto;

create table if not exists public.institutions (
  id uuid primary key default gen_random_uuid(), code text not null unique,
  title text not null, language text not null default 'en',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  institution_id uuid references public.institutions(id),
  role text not null check (role in ('super_admin','institute_admin','teacher','student')),
  full_name text not null default '', email text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists profiles_institution_role_idx on public.profiles(institution_id,role);

-- The first owner must be provisioned by a trusted operator after Auth signup.
-- New accounts get no role by default and cannot grant themselves one.
create or replace function public.my_role() returns text language sql stable security definer
set search_path = '' as $$ select p.role from public.profiles p where p.id = (select auth.uid()) $$;
create or replace function public.my_institution() returns uuid language sql stable security definer
set search_path = '' as $$ select p.institution_id from public.profiles p where p.id = (select auth.uid()) $$;
create or replace function public.can_manage(i uuid) returns boolean language sql stable security definer
set search_path = '' as $$ select public.my_role() = 'super_admin' or
  (public.my_role() = 'institute_admin' and public.my_institution() = i) $$;

create table if not exists public.students (
  id uuid primary key default gen_random_uuid(), profile_id uuid not null unique references public.profiles(id),
  institution_id uuid not null references public.institutions(id), student_code text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.teachers (
  id uuid primary key default gen_random_uuid(), profile_id uuid not null unique references public.profiles(id),
  institution_id uuid not null references public.institutions(id), teacher_code text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.courses (
  id uuid primary key default gen_random_uuid(), institution_id uuid not null references public.institutions(id),
  created_by uuid not null references public.profiles(id), title text not null, description text not null default '',
  published boolean not null default false, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.modules (
  id uuid primary key default gen_random_uuid(), course_id uuid not null references public.courses(id) on delete cascade,
  title text not null, position integer not null default 0,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.lessons (
  id uuid primary key default gen_random_uuid(), module_id uuid not null references public.modules(id) on delete cascade,
  title text not null, description text not null default '', video_url text, position integer not null default 0,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.classes (
  id uuid primary key default gen_random_uuid(), institution_id uuid not null references public.institutions(id),
  course_id uuid references public.courses(id), teacher_id uuid references public.teachers(id),
  title text not null, subject text, fee numeric(12,2) not null default 0,
  active boolean not null default true, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.class_sessions (
  id uuid primary key default gen_random_uuid(), class_id uuid not null references public.classes(id),
  title text not null, starts_at timestamptz not null, ends_at timestamptz not null,
  mode text not null default 'Online', location text, meeting_url text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.enrollments (
  id uuid primary key default gen_random_uuid(), institution_id uuid not null references public.institutions(id),
  class_id uuid not null references public.classes(id), student_id uuid not null references public.students(id),
  active boolean not null default true, access_override text not null default 'Automatic',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(class_id,student_id)
);
create table if not exists public.attendance (
  id uuid primary key default gen_random_uuid(), class_id uuid not null references public.classes(id),
  student_id uuid not null references public.students(id), occurred_at timestamptz not null,
  status text not null, recorded_by uuid references public.profiles(id),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.assignments (
  id uuid primary key default gen_random_uuid(), class_id uuid not null references public.classes(id),
  title text not null, instructions text not null default '', due_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.materials (
  id uuid primary key default gen_random_uuid(), class_id uuid not null references public.classes(id),
  title text not null, description text not null default '', storage_path text,
  external_url text, download_policy text not null default 'View only',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  check (storage_path is not null or external_url is not null)
);
create table if not exists public.assignment_submissions (
  id uuid primary key default gen_random_uuid(), assignment_id uuid not null references public.assignments(id),
  student_id uuid not null references public.students(id), storage_path text, submitted_at timestamptz,
  grade numeric(6,2), created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(assignment_id,student_id)
);
create table if not exists public.exams (
  id uuid primary key default gen_random_uuid(), class_id uuid not null references public.classes(id),
  title text not null, questions jsonb, opens_at timestamptz, closes_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.exam_results (
  id uuid primary key default gen_random_uuid(), exam_id uuid not null references public.exams(id),
  student_id uuid not null references public.students(id), score numeric(6,2), feedback text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(exam_id,student_id)
);
create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(), institution_id uuid not null references public.institutions(id),
  enrollment_id uuid not null references public.enrollments(id), amount numeric(12,2) not null check(amount >= 0),
  currency text not null default 'LKR', status text not null default 'Pending', provider_reference text unique,
  paid_at timestamptz, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(), institution_id uuid not null references public.institutions(id),
  recipient_id uuid not null references public.profiles(id), body text not null, read_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists students_institution_idx on public.students(institution_id);
create index if not exists teachers_institution_idx on public.teachers(institution_id);
create index if not exists courses_institution_idx on public.courses(institution_id);
create index if not exists modules_course_idx on public.modules(course_id,position);
create index if not exists lessons_module_idx on public.lessons(module_id,position);
create index if not exists classes_institution_idx on public.classes(institution_id);
create index if not exists class_sessions_class_idx on public.class_sessions(class_id,starts_at);
create index if not exists enrollments_student_idx on public.enrollments(student_id,class_id);
create index if not exists attendance_student_idx on public.attendance(student_id,occurred_at);
create index if not exists assignments_class_idx on public.assignments(class_id);
create index if not exists materials_class_idx on public.materials(class_id);
create index if not exists submissions_student_idx on public.assignment_submissions(student_id);
create index if not exists exams_class_idx on public.exams(class_id);
create index if not exists exam_results_student_idx on public.exam_results(student_id);
create index if not exists payments_institution_idx on public.payments(institution_id,status);
create index if not exists notifications_recipient_idx on public.notifications(recipient_id,created_at);

-- Reuse the institution and enrollment relationships in one audited function.
create or replace function public.can_teach_student(s uuid) returns boolean language sql stable security definer
set search_path = '' as $$ select exists(
  select 1 from public.enrollments e join public.classes c on c.id=e.class_id
  join public.teachers t on t.id=c.teacher_id
  where e.student_id=s and e.active and t.profile_id=(select auth.uid())) $$;
create or replace function public.can_view_class(c uuid) returns boolean language sql stable security definer
set search_path = '' as $$
  select exists(select 1 from public.classes x where x.id = c and (
    public.can_manage(x.institution_id) or
    exists(select 1 from public.teachers t where t.id = x.teacher_id and t.profile_id = (select auth.uid())) or
    exists(select 1 from public.enrollments e join public.students s on s.id=e.student_id
      where e.class_id=x.id and e.active and s.profile_id=(select auth.uid()))))
$$;
create or replace function public.can_record_attendance(c uuid, s uuid) returns boolean language sql stable security definer
set search_path = '' as $$
  select exists(select 1 from public.classes x
    join public.enrollments e on e.class_id=x.id and e.student_id=s and e.active
    where x.id=c and (public.can_manage(x.institution_id) or
      exists(select 1 from public.teachers t where t.id=x.teacher_id and t.profile_id=(select auth.uid()))))
$$;

do $$ declare t text; begin
  foreach t in array array['institutions','profiles','students','teachers','courses','modules','lessons','classes','class_sessions','enrollments','attendance','assignments','materials','assignment_submissions','exams','exam_results','payments','notifications'] loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

create policy institutions_read on public.institutions for select to authenticated
using (public.can_manage(id) or id=public.my_institution());
create policy profiles_read on public.profiles for select to authenticated
using (id=(select auth.uid()) or public.can_manage(institution_id));
create policy students_read on public.students for select to authenticated
using (profile_id=(select auth.uid()) or public.can_manage(institution_id) or
  public.can_teach_student(id));
create policy students_manage on public.students for all to authenticated
using (public.can_manage(institution_id)) with check (public.can_manage(institution_id) and
  exists(select 1 from public.profiles p where p.id=profile_id and p.institution_id=students.institution_id and p.role='student'));
create policy teachers_read on public.teachers for select to authenticated
using (institution_id=public.my_institution() or public.my_role()='super_admin');
create policy teachers_manage on public.teachers for all to authenticated
using (public.can_manage(institution_id)) with check (public.can_manage(institution_id) and
  exists(select 1 from public.profiles p where p.id=profile_id and p.institution_id=teachers.institution_id and p.role='teacher'));
create policy courses_read on public.courses for select to authenticated
using (public.can_manage(institution_id) or
  (institution_id=public.my_institution() and (published or public.my_role()='teacher')));
create policy courses_manage on public.courses for all to authenticated
using (public.can_manage(institution_id) or (public.my_role()='teacher' and institution_id=public.my_institution() and created_by=(select auth.uid())))
with check (public.can_manage(institution_id) or (public.my_role()='teacher' and institution_id=public.my_institution() and created_by=(select auth.uid())));
create policy classes_read on public.classes for select to authenticated using (public.can_view_class(id));
create policy classes_manage on public.classes for all to authenticated
using (public.can_manage(institution_id)) with check (public.can_manage(institution_id) and
  (course_id is null or exists(select 1 from public.courses c where c.id=course_id and c.institution_id=classes.institution_id)) and
  (teacher_id is null or exists(select 1 from public.teachers t where t.id=teacher_id and t.institution_id=classes.institution_id)));
create policy class_sessions_read on public.class_sessions for select to authenticated using (public.can_view_class(class_id));
create policy class_sessions_manage on public.class_sessions for all to authenticated
using (public.can_manage((select c.institution_id from public.classes c where c.id=class_id)))
with check (public.can_manage((select c.institution_id from public.classes c where c.id=class_id)));
create policy enrollments_read on public.enrollments for select to authenticated
using (public.can_view_class(class_id) and (public.my_role() <> 'student' or
  exists(select 1 from public.students s where s.id=student_id and s.profile_id=(select auth.uid()))));
create policy enrollments_manage on public.enrollments for all to authenticated
using (public.can_manage(institution_id)) with check (public.can_manage(institution_id) and
  exists(select 1 from public.classes c where c.id=class_id and c.institution_id=enrollments.institution_id) and
  exists(select 1 from public.students s where s.id=student_id and s.institution_id=enrollments.institution_id));
create policy attendance_read on public.attendance for select to authenticated
using (public.can_view_class(class_id) and (public.my_role()<>'student' or
  exists(select 1 from public.students s where s.id=student_id and s.profile_id=(select auth.uid()))));
create policy attendance_manage on public.attendance for all to authenticated
using (public.can_manage((select c.institution_id from public.classes c where c.id=class_id)))
with check (public.can_manage((select c.institution_id from public.classes c where c.id=class_id)));
create policy attendance_teacher_insert on public.attendance for insert to authenticated
with check (recorded_by=(select auth.uid()) and public.can_record_attendance(class_id,student_id));
create policy payments_read on public.payments for select to authenticated
using (public.can_manage(institution_id) or exists(select 1 from public.enrollments e join public.students s on s.id=e.student_id
where e.id=enrollment_id and s.profile_id=(select auth.uid())));
create policy payments_manage on public.payments for all to authenticated
using (public.can_manage(institution_id)) with check (public.can_manage(institution_id) and
  exists(select 1 from public.enrollments e where e.id=enrollment_id and e.institution_id=payments.institution_id));
create policy notifications_read on public.notifications for select to authenticated
using (recipient_id=(select auth.uid()) or public.can_manage(institution_id));
create policy notifications_manage on public.notifications for all to authenticated
using (public.can_manage(institution_id)) with check (public.can_manage(institution_id));

-- Child tables inherit access through their parent class. Mutation remains server/admin controlled.
create policy modules_read on public.modules for select to authenticated
using (exists(select 1 from public.courses c where c.id=course_id and c.institution_id=public.my_institution()) or public.my_role()='super_admin');
create policy lessons_read on public.lessons for select to authenticated
using (exists(select 1 from public.modules m join public.courses c on c.id=m.course_id
  where m.id=module_id and c.institution_id=public.my_institution()) or public.my_role()='super_admin');
create policy assignments_read on public.assignments for select to authenticated using (public.can_view_class(class_id));
create policy materials_read on public.materials for select to authenticated using (public.can_view_class(class_id));
create policy exams_read on public.exams for select to authenticated using (public.can_view_class(class_id));
create policy submissions_read on public.assignment_submissions for select to authenticated
using (exists(select 1 from public.assignments a where a.id=assignment_id and public.can_view_class(a.class_id)) and
 (public.my_role()<>'student' or exists(select 1 from public.students s where s.id=student_id and s.profile_id=(select auth.uid()))));
create policy exam_results_read on public.exam_results for select to authenticated
using (exists(select 1 from public.exams e where e.id=exam_id and public.can_view_class(e.class_id)) and
 (public.my_role()<>'student' or exists(select 1 from public.students s where s.id=student_id and s.profile_id=(select auth.uid()))));

-- Only the owner can assign the first profile; the browser must never set roles.
revoke insert, update, delete on public.profiles from anon;
