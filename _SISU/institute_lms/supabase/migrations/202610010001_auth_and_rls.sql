-- Supabase Auth provisioning, server-side sessions, and auth-specific RLS.
-- Apply after 202609300002_rls.sql. This migration is additive and removes no data.
begin;

alter table public.profiles add column if not exists email citext;

create table if not exists public.account_applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  account_type text not null check (account_type in ('teacher', 'institute')),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  details jsonb not null default '{}'::jsonb,
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.app_sessions (
  id uuid primary key default gen_random_uuid(),
  session_hash text not null unique,
  user_id uuid not null references auth.users(id) on delete cascade,
  token_ciphertext text not null,
  csrf_hash text not null,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists app_sessions_user_expiry_idx
  on public.app_sessions (user_id, expires_at);

alter table public.account_applications enable row level security;
alter table public.app_sessions enable row level security;
revoke all on public.app_sessions from public, anon, authenticated;
grant all on public.app_sessions to service_role;
grant all on public.account_applications to service_role;
revoke insert, update, delete on public.account_applications from anon, authenticated;
grant select on public.account_applications to authenticated;
grant select (email) on public.profiles to authenticated;

drop policy if exists applications_read_own on public.account_applications;
create policy applications_read_own
on public.account_applications for select to authenticated
using (user_id = (select auth.uid()) or private.is_platform_admin());

-- The browser can change only the display name. Identity, account kind/status,
-- email and memberships remain controlled by Auth or privileged server flows.
revoke update on public.profiles from authenticated;
grant update (full_name) on public.profiles to authenticated;
drop policy if exists profiles_own_update on public.profiles;
create policy profiles_own_update
on public.profiles for update to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()));

create or replace function private.is_active_profile()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.status = 'verified'
  )
$$;
revoke all on function private.is_active_profile() from public, anon;
grant execute on function private.is_active_profile() to authenticated, service_role;

-- An authenticated but pending/suspended account cannot use application data.
do $$
declare table_name text;
begin
  foreach table_name in array array[
    'institutions', 'institution_memberships', 'courses', 'course_modules',
    'lessons', 'programmes', 'classes', 'class_sessions', 'materials',
    'programme_modules', 'programme_enrollments', 'enrollments', 'attendance',
    'assignments', 'assignment_submissions', 'exams', 'exam_questions',
    'exam_attempts', 'exam_answers', 'exam_results', 'announcements', 'feedback',
    'news', 'news_images', 'invoices', 'payments', 'notifications',
    'support_tickets', 'support_replies'
  ] loop
    execute format('drop policy if exists active_profile on public.%I', table_name);
    execute format(
      'create policy active_profile on public.%I as restrictive for all to authenticated using (private.is_active_profile()) with check (private.is_active_profile())',
      table_name
    );
  end loop;
end $$;

-- Sign-up metadata chooses a profile kind, never an administrative database role.
-- Provider profiles remain pending until the review RPC activates a membership.
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  requested text := lower(coalesce(new.raw_user_meta_data->>'account_type', 'student'));
  safe_kind text;
  safe_name text;
begin
  safe_kind := case when requested in ('student', 'teacher', 'institute') then requested else 'student' end;
  safe_name := left(nullif(btrim(coalesce(new.raw_user_meta_data->>'full_name', '')), ''), 120);
  safe_name := coalesce(safe_name, 'Sisu user');

  insert into public.profiles (id, username, email, full_name, profile_kind, status, country)
  values (
    new.id,
    ('user_' || replace(left(new.id::text, 24), '-', ''))::public.citext,
    new.email,
    safe_name,
    safe_kind,
    case when safe_kind = 'student' then 'verified' else 'pending' end,
    nullif(left(coalesce(new.raw_user_meta_data->>'country', ''), 80), '')
  )
  on conflict (id) do update set email = excluded.email;

  if safe_kind in ('teacher', 'institute') then
    insert into public.account_applications (user_id, account_type, details)
    values (new.id, safe_kind, new.raw_user_meta_data - 'account_type')
    on conflict (user_id) do nothing;
  end if;
  return new;
end
$$;

-- Never replace an unrelated Auth trigger silently.
do $$
begin
  if exists (
    select 1 from pg_trigger t
    join pg_proc p on p.oid = t.tgfoid
    where t.tgrelid = 'auth.users'::regclass
      and t.tgname = 'on_auth_user_created'
      and p.proname <> 'handle_new_auth_user'
  ) then
    raise exception 'Existing Auth trigger requires manual review';
  end if;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- Backfill identities only; existing users stay pending until reviewed.
insert into public.profiles (id, username, email, full_name, profile_kind, status)
select
  u.id,
  ('user_' || replace(left(u.id::text, 24), '-', ''))::public.citext,
  u.email,
  coalesce(nullif(left(btrim(coalesce(u.raw_user_meta_data->>'full_name', '')), 120), ''), 'Sisu user'),
  case
    when lower(coalesce(u.raw_user_meta_data->>'account_type', 'student')) in ('student', 'teacher', 'institute')
      then lower(coalesce(u.raw_user_meta_data->>'account_type', 'student'))
    else 'student'
  end,
  'pending'
from auth.users u
left join public.profiles p on p.id = u.id
where p.id is null
on conflict (id) do nothing;

update public.profiles p
set email = u.email
from auth.users u
where p.id = u.id and p.email is distinct from u.email;

insert into public.account_applications (user_id, account_type, details)
select
  u.id,
  lower(u.raw_user_meta_data->>'account_type'),
  u.raw_user_meta_data - 'account_type'
from auth.users u
where lower(u.raw_user_meta_data->>'account_type') in ('teacher', 'institute')
on conflict (user_id) do nothing;

create or replace function public.review_application(
  application uuid,
  decision text,
  institution uuid
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  application_row public.account_applications;
  membership_role text;
  display_name text;
begin
  if not private.is_platform_admin() then
    raise insufficient_privilege;
  end if;
  if decision not in ('approved', 'rejected') then
    raise exception 'Invalid decision';
  end if;

  select * into application_row
  from public.account_applications
  where id = application
  for update;
  if not found or application_row.status <> 'pending' then
    raise exception 'Application not pending';
  end if;

  if decision = 'approved' then
    if institution is null or not exists (select 1 from public.institutions i where i.id = institution) then
      raise exception 'Valid institution required';
    end if;
    membership_role := case when application_row.account_type = 'teacher' then 'teacher' else 'institute_admin' end;
    select p.full_name into display_name from public.profiles p where p.id = application_row.user_id;
    update public.profiles set status = 'verified', updated_at = now()
      where id = application_row.user_id;
    insert into public.institution_memberships (
      institution_id, user_id, role, status, display_name, approved_by, approved_at
    ) values (
      institution, application_row.user_id, membership_role, 'active', display_name, auth.uid(), now()
    )
    on conflict (institution_id, user_id) do update
      set role = excluded.role, status = 'active', display_name = excluded.display_name,
          approved_by = auth.uid(), approved_at = now(), updated_at = now();
  else
    update public.profiles set status = 'rejected', updated_at = now()
      where id = application_row.user_id;
  end if;

  update public.account_applications
  set status = decision, reviewed_by = auth.uid(), reviewed_at = now(), updated_at = now()
  where id = application;
end
$$;
revoke all on function public.review_application(uuid, text, uuid) from public, anon;
grant execute on function public.review_application(uuid, text, uuid) to authenticated;

create or replace function public.assign_student(student_profile uuid, institution uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare student_name text;
begin
  if not private.is_platform_admin() then
    raise insufficient_privilege;
  end if;
  if not exists (select 1 from public.institutions i where i.id = institution) then
    raise exception 'Unknown institution';
  end if;
  select p.full_name into student_name
  from public.profiles p
  where p.id = student_profile and p.profile_kind = 'student' and p.status = 'verified'
  for update;
  if not found then
    raise exception 'Verified student required';
  end if;
  if exists (
    select 1 from public.institution_memberships m
    where m.user_id = student_profile and m.role = 'student' and m.institution_id <> institution
      and m.status in ('pending', 'active')
  ) then
    raise exception 'Existing memberships must not be reassigned';
  end if;
  insert into public.institution_memberships (institution_id, user_id, role, status, display_name, approved_by, approved_at)
  values (institution, student_profile, 'student', 'active', student_name, auth.uid(), now())
  on conflict (institution_id, user_id) do update
    set role = 'student', status = 'active', display_name = excluded.display_name,
        approved_by = auth.uid(), approved_at = now(), updated_at = now();
end
$$;
revoke all on function public.assign_student(uuid, uuid) from public, anon;
grant execute on function public.assign_student(uuid, uuid) to authenticated;

commit;
