-- Add student approval to the existing Supabase Auth workflow.
-- This migration preserves existing users and application records.
begin;

do $$
declare
  constraint_name text;
begin
  for constraint_name in
    select conname
    from pg_constraint
    where conrelid = 'public.account_applications'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%account_type%'
  loop
    execute format(
      'alter table public.account_applications drop constraint %I',
      constraint_name
    );
  end loop;
end
$$;

alter table public.account_applications
  add constraint account_applications_account_type_check
  check (account_type in ('student', 'teacher', 'institute'));

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
  safe_kind := case
    when requested in ('student', 'teacher', 'institute') then requested
    else 'student'
  end;
  safe_name := left(nullif(btrim(coalesce(new.raw_user_meta_data->>'full_name', '')), ''), 120);
  safe_name := coalesce(safe_name, 'Sisu user');

  insert into public.profiles (
    id, username, email, full_name, profile_kind, status, country
  )
  values (
    new.id,
    ('user_' || replace(left(new.id::text, 24), '-', ''))::public.citext,
    new.email,
    safe_name,
    safe_kind,
    'pending',
    nullif(left(coalesce(new.raw_user_meta_data->>'country', ''), 80), '')
  )
  on conflict (id) do update set email = excluded.email;

  insert into public.account_applications (user_id, account_type, details)
  values (new.id, safe_kind, new.raw_user_meta_data - 'account_type')
  on conflict (user_id) do nothing;

  return new;
end
$$;
revoke all on function public.handle_new_auth_user() from public, anon, authenticated;

do $$
begin
  if not exists (
    select 1
    from pg_trigger t
    join pg_proc p on p.oid = t.tgfoid
    where t.tgrelid = 'auth.users'::regclass
      and t.tgname = 'on_auth_user_created'
      and p.proname = 'handle_new_auth_user'
      and t.tgenabled <> 'D'
  ) then
    raise exception 'Expected Auth provisioning trigger is missing or has a different handler';
  end if;
end
$$;

-- Add an application only for pending student profiles; verified accounts are
-- left intact and remain available in the institution-assignment list.
insert into public.account_applications (user_id, account_type, details)
select
  p.id,
  'student',
  coalesce(u.raw_user_meta_data, '{}'::jsonb) - 'account_type'
from public.profiles p
join auth.users u on u.id = p.id
where p.profile_kind = 'student'
  and p.status = 'pending'
  and not exists (
    select 1 from public.account_applications a where a.user_id = p.id
  )
on conflict (user_id) do nothing;

-- Recover any student application previously given an administrator
-- membership by the incorrect role fallback without deleting membership rows.
update public.institution_memberships m
set status = 'suspended', updated_at = now()
from public.account_applications a
join public.profiles p on p.id = a.user_id
where a.user_id = m.user_id
  and a.account_type = 'student'
  and p.profile_kind = 'student'
  and m.role = 'institute_admin'
  and m.status in ('pending', 'active');

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
  profile_row public.profiles;
  membership_role text;
begin
  if not private.is_platform_admin() then
    raise insufficient_privilege;
  end if;
  if decision not in ('approved', 'rejected') then
    raise exception using errcode = '22023', message = 'Invalid application decision';
  end if;

  select * into application_row
  from public.account_applications
  where id = application
  for update;
  if not found or application_row.status <> 'pending' then
    raise exception using errcode = 'P0001', message = 'Application not pending';
  end if;

  select * into profile_row
  from public.profiles
  where id = application_row.user_id
  for update;
  if not found or profile_row.profile_kind <> application_row.account_type then
    raise exception using errcode = 'P0001', message = 'Application profile does not match its account type';
  end if;

  if decision = 'approved' then
    if application_row.account_type in ('teacher', 'institute') then
      if institution is null or not exists (
        select 1 from public.institutions i where i.id = institution
      ) then
        raise exception using errcode = 'P0001', message = 'A valid institution is required for provider approval';
      end if;
    end if;

    update public.profiles
    set status = 'verified', reviewed_by = auth.uid(), reviewed_at = now(), updated_at = now()
    where id = application_row.user_id;

    if application_row.account_type in ('teacher', 'institute') then
      membership_role := case application_row.account_type
        when 'teacher' then 'teacher'
        when 'institute' then 'institute_admin'
      end;

      insert into public.institution_memberships (
        institution_id, user_id, role, status, display_name, approved_by, approved_at
      )
      values (
        institution, application_row.user_id, membership_role, 'active',
        profile_row.full_name, auth.uid(), now()
      )
      on conflict (institution_id, user_id) do update
        set role = excluded.role,
            status = 'active',
            display_name = excluded.display_name,
            approved_by = auth.uid(),
            approved_at = now(),
            updated_at = now();
    end if;
  else
    update public.profiles
    set status = 'rejected', reviewed_by = auth.uid(), reviewed_at = now(), updated_at = now()
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
declare
  student_name text;
begin
  if not private.is_platform_admin() then
    raise insufficient_privilege;
  end if;

  perform pg_advisory_xact_lock(hashtextextended(student_profile::text, 0));

  if not exists (
    select 1 from public.institutions i where i.id = institution
  ) then
    raise exception using errcode = 'P0001', message = 'Unknown institution';
  end if;

  select p.full_name into student_name
  from public.profiles p
  where p.id = student_profile
    and p.profile_kind = 'student'
    and p.status = 'verified'
  for update;
  if not found then
    raise exception using errcode = 'P0001', message = 'Verified student required';
  end if;

  if exists (
    select 1
    from public.institution_memberships m
    where m.user_id = student_profile
      and m.role = 'student'
      and m.institution_id <> institution
      and m.status in ('pending', 'active')
  ) then
    raise exception using errcode = 'P0001',
      message = 'Student is already assigned to another institution.';
  end if;

  insert into public.institution_memberships (
    institution_id, user_id, role, status, display_name, approved_by, approved_at
  )
  values (
    institution, student_profile, 'student', 'active', student_name, auth.uid(), now()
  )
  on conflict (institution_id, user_id) do update
    set role = 'student',
        status = 'active',
        display_name = excluded.display_name,
        approved_by = auth.uid(),
        approved_at = now(),
        updated_at = now();
end
$$;
revoke all on function public.assign_student(uuid, uuid) from public, anon;
grant execute on function public.assign_student(uuid, uuid) to authenticated;

grant insert on public.institutions, public.classes, public.enrollments to authenticated;

drop policy if exists institutions_admin_insert on public.institutions;
create policy institutions_admin_insert
on public.institutions for insert to authenticated
with check (private.is_platform_admin());

drop policy if exists classes_admin_insert on public.classes;
create policy classes_admin_insert
on public.classes for insert to authenticated
with check (
  private.is_institute_admin(institution_id)
  and (
    classes.teacher_membership_id is null
    or exists (
      select 1
      from public.institution_memberships m
      where m.id = classes.teacher_membership_id
        and m.institution_id = classes.institution_id
        and m.role = 'teacher'
        and m.status = 'active'
    )
  )
);

drop policy if exists enrollments_admin_insert on public.enrollments;
create policy enrollments_admin_insert
on public.enrollments for insert to authenticated
with check (
  private.is_institute_admin(institution_id)
  and exists (
    select 1
    from public.institution_memberships m
    where m.id = enrollments.student_membership_id
      and m.institution_id = enrollments.institution_id
      and m.role = 'student'
      and m.status = 'active'
  )
);

drop policy if exists profiles_verified_students_platform_select on public.profiles;
create policy profiles_verified_students_platform_select
on public.profiles for select to authenticated
using (
  profile_kind = 'student'
  and status = 'verified'
  and private.is_active_profile()
  and private.is_platform_admin()
);

commit;
