-- Run after all migrations with psql or the Supabase SQL editor.
-- The transaction always rolls back; fixed UUIDs exist only for this test.

begin;

create or replace function pg_temp.assert_true(condition boolean, message text)
returns void
language plpgsql
as $$
begin
  if condition is not true then
    raise exception 'assertion failed: %', message;
  end if;
end;
$$;

select pg_temp.assert_true(
  not exists (
    select 1
    from (values
      ('profiles'), ('platform_roles'), ('institutions'), ('institution_memberships'),
      ('courses'), ('course_modules'), ('lessons'), ('programmes'), ('classes'),
      ('class_sessions'), ('materials'), ('programme_modules'), ('programme_enrollments'),
      ('enrollments'), ('attendance'), ('assignments'), ('assignment_submissions'),
      ('exams'), ('exam_questions'), ('exam_attempts'), ('exam_answers'), ('exam_results'),
      ('announcements'), ('feedback'), ('news'), ('news_images'), ('invoices'), ('payments'),
      ('notifications'), ('support_tickets'), ('support_replies'), ('audit_events'), ('outbox_events')
    ) required(name)
    where to_regclass('public.' || required.name) is null
  ),
  'all primary application tables exist'
);

select pg_temp.assert_true(
  not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname in (
        'profiles', 'platform_roles', 'institutions', 'institution_memberships',
        'courses', 'course_modules', 'lessons', 'programmes', 'classes',
        'class_sessions', 'materials', 'programme_modules', 'programme_enrollments',
        'enrollments', 'attendance', 'assignments', 'assignment_submissions',
        'exams', 'exam_questions', 'exam_attempts', 'exam_answers', 'exam_results',
        'announcements', 'feedback', 'news', 'news_images', 'invoices', 'payments',
        'notifications', 'support_tickets', 'support_replies', 'audit_events', 'outbox_events'
      )
      and (not c.relrowsecurity or not c.relforcerowsecurity)
  ),
  'RLS is enabled and forced on every exposed application table'
);

select pg_temp.assert_true(
  not exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname in (
        'is_platform_admin', 'has_membership', 'is_institute_admin',
        'owns_membership', 'can_manage_course', 'can_view_course',
        'can_teach_class', 'can_manage_class', 'can_view_class',
        'can_access_class_content', 'can_view_membership', 'can_view_programme',
        'can_manage_exam', 'can_view_support_ticket'
      )
      and (
        not p.prosecdef
        or not exists (
          select 1 from unnest(coalesce(p.proconfig, '{}'::text[])) setting
          where setting = 'search_path=""'
        )
      )
  ),
  'all authorization helpers are SECURITY DEFINER with an empty search_path'
);

select pg_temp.assert_true(
  not exists (
    select 1
    from pg_policies
    where schemaname in ('public', 'storage')
      and coalesce(qual, '') in ('true', '(true)')
  ),
  'no application/storage policy has an unconditional USING true expression'
);

select pg_temp.assert_true(
  not exists (
    select 1
    from information_schema.role_table_grants
    where table_schema = 'private'
      and grantee in ('anon', 'authenticated')
  ),
  'browser roles have no direct table privileges in the private schema'
);

select pg_temp.assert_true(
  not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and column_name like '%\_minor' escape '\'
      and data_type <> 'bigint'
  ),
  'all minor-unit money columns use bigint'
);

select pg_temp.assert_true(
  not has_column_privilege('authenticated', 'public.exam_questions', 'correct_answer', 'select'),
  'authenticated clients cannot select exam answer keys'
);

select pg_temp.assert_true(
  (select count(*) = 4 from storage.buckets
   where id in ('public-media', 'private-materials', 'private-answers', 'private-receipts')),
  'all required storage buckets exist'
);

-- Minimal Auth identities for behavioral RLS checks. This shape is compatible
-- with Supabase Auth and is rolled back at the end of the test.
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
)
values
  ('00000000-0000-0000-0000-000000000000', '10000000-0000-0000-0000-000000000001', 'authenticated', 'authenticated', 'admin-a@example.invalid', '', now(), '{}'::jsonb, '{}'::jsonb, now(), now()),
  ('00000000-0000-0000-0000-000000000000', '10000000-0000-0000-0000-000000000002', 'authenticated', 'authenticated', 'teacher-a@example.invalid', '', now(), '{}'::jsonb, '{}'::jsonb, now(), now()),
  ('00000000-0000-0000-0000-000000000000', '10000000-0000-0000-0000-000000000003', 'authenticated', 'authenticated', 'student-a@example.invalid', '', now(), '{}'::jsonb, '{}'::jsonb, now(), now()),
  ('00000000-0000-0000-0000-000000000000', '10000000-0000-0000-0000-000000000004', 'authenticated', 'authenticated', 'student-b@example.invalid', '', now(), '{}'::jsonb, '{}'::jsonb, now(), now());

insert into public.profiles (id, username, full_name, profile_kind, status)
values
  ('10000000-0000-0000-0000-000000000001', 'admin_a', 'Admin A', 'institute', 'verified'),
  ('10000000-0000-0000-0000-000000000002', 'teacher_a', 'Teacher A', 'teacher', 'verified'),
  ('10000000-0000-0000-0000-000000000003', 'student_a', 'Student A', 'student', 'verified'),
  ('10000000-0000-0000-0000-000000000004', 'student_b', 'Student B', 'student', 'verified');

insert into public.institutions (id, owner_user_id, code, title)
values
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'TSTA', 'Test Academy A'),
  ('20000000-0000-0000-0000-000000000002', null, 'TSTB', 'Test Academy B');

insert into public.institution_memberships
  (id, institution_id, user_id, role, status, member_code, display_name)
values
  ('30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'institute_admin', 'active', 'AD-TSTA-0001', 'Admin A'),
  ('30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000002', 'teacher', 'active', 'TC-TSTA-0001', 'Teacher A'),
  ('30000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000003', 'student', 'active', 'ST-TSTA-00001', 'Student A'),
  ('30000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000004', 'student', 'active', 'ST-TSTB-00001', 'Student B');

insert into public.classes (
  id, institution_id, teacher_membership_id, owner_type, title, subject,
  fee_minor, currency, published
)
values (
  '40000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000002',
  'institution', 'Test Class', 'Mathematics', 100000, 'LKR', false
);

insert into public.class_sessions (
  id, institution_id, class_id, title, starts_at, ends_at, mode
)
values (
  '50000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '40000000-0000-0000-0000-000000000001',
  'Session One', now() - interval '1 hour', now() + interval '1 hour', 'online'
);

insert into public.enrollments (
  id, institution_id, class_id, student_membership_id, fee_minor, currency,
  status, access_override
)
values (
  '60000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '40000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000003',
  100000, 'LKR', 'active', 'automatic'
);

insert into public.invoices (
  id, institution_id, enrollment_id, student_membership_id, class_id,
  amount_minor, beneficiary_minor, platform_minor, currency, due_date, status
)
values (
  '70000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '60000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000003',
  '40000000-0000-0000-0000-000000000001',
  100000, 90000, 10000, 'LKR', current_date, 'paid'
);

insert into public.materials (
  id, institution_id, class_id, title, kind, storage_bucket, storage_path
)
values (
  '80000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '40000000-0000-0000-0000-000000000001',
  'Private Handout', 'document', 'private-materials',
  'institutions/20000000-0000-0000-0000-000000000001/classes/40000000-0000-0000-0000-000000000001/handout.pdf'
);

set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000003', true);

select pg_temp.assert_true(
  (select count(*) = 1 from public.institutions),
  'student sees only their institution'
);
select pg_temp.assert_true(
  (select count(*) = 1 from public.materials),
  'paid enrolled student can read private material metadata'
);
select pg_temp.assert_true(
  private.can_access_class_content('40000000-0000-0000-0000-000000000001'),
  'paid enrollment opens the content gate'
);

reset role;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000004', true);

select pg_temp.assert_true(
  (select count(*) = 0 from public.materials),
  'student in another tenant cannot read material metadata'
);
select pg_temp.assert_true(
  not private.can_access_class_content('40000000-0000-0000-0000-000000000001'),
  'student in another tenant fails the content gate'
);

reset role;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000002', true);

select pg_temp.assert_true(
  (select count(*) = 1 from public.enrollments),
  'assigned teacher can read enrollment for their class'
);
select pg_temp.assert_true(
  (select count(*) = 1 from public.students where id = '30000000-0000-0000-0000-000000000003'),
  'teacher compatibility view exposes only an enrolled student'
);

reset role;

rollback;
