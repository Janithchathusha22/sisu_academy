-- Review on staging first. No existing records are removed.
begin;

-- Suspended/pending accounts lose their database role even through direct Data API access.
create or replace function public.my_role() returns text language sql stable security definer
set search_path='' as $$ select p.role from public.profiles p
where p.id=(select auth.uid()) and p.account_status='active' $$;
create or replace function public.my_institution() returns uuid language sql stable security definer
set search_path='' as $$ select p.institution_id from public.profiles p
where p.id=(select auth.uid()) and p.account_status='active' $$;

revoke all on public.app_sessions from public, anon, authenticated;
grant all on public.app_sessions to service_role;
revoke insert, update, delete on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update(full_name) on public.profiles to authenticated;
create policy profiles_edit_name on public.profiles for update to authenticated
using(id=(select auth.uid())) with check(id=(select auth.uid()));

-- A restrictive policy applies in addition to every existing permissive policy.
do $$ declare t text; begin
foreach t in array array['institutions','students','teachers','courses','modules','lessons','classes',
'class_sessions','enrollments','attendance','assignments','materials','assignment_submissions','exams',
'exam_results','payments','notifications'] loop
  execute format('create policy active_account on public.%I as restrictive for all to authenticated using (public.my_role() is not null) with check (public.my_role() is not null)',t);
end loop; end $$;

create policy attendance_teacher_update on public.attendance for update to authenticated
using(public.my_role()='teacher' and public.can_record_attendance(class_id,student_id))
with check(public.my_role()='teacher' and public.can_record_attendance(class_id,student_id));
revoke update on public.attendance from authenticated;
grant update(status) on public.attendance to authenticated;

-- Prevent administrators from recording attendance for a student outside this class.
create policy attendance_enrolled on public.attendance as restrictive for insert to authenticated
with check(recorded_by=(select auth.uid()) and public.can_record_attendance(class_id,student_id));

grant select on public.account_applications to authenticated;
revoke insert, update, delete on public.account_applications from anon, authenticated;

-- Explicit grants: do not rely on project-specific default privileges.
grant select on public.institutions,public.students,public.teachers,public.courses,public.modules,
public.lessons,public.classes,public.class_sessions,public.enrollments,public.attendance,
public.assignments,public.materials,public.assignment_submissions,public.exam_results,
public.payments,public.notifications to authenticated;
grant insert on public.courses,public.classes,public.class_sessions,public.enrollments,public.attendance to authenticated;
grant update on public.courses to authenticated;
-- Exam answer payloads must not leak through direct Supabase REST queries.
revoke select on public.exams from public,anon,authenticated;
grant select(id,class_id,title,opens_at,closes_at,created_at,updated_at) on public.exams to authenticated;

create policy institutions_create on public.institutions for insert to authenticated
with check(public.my_role()='super_admin');
grant insert on public.institutions to authenticated;

-- One transaction provisions both profile and member. Browser-selected roles cannot grant privileges.
create or replace function public.review_application(application uuid, decision text, institution uuid)
returns void language plpgsql security definer set search_path='' as $$
declare a public.account_applications; assigned_role text;
begin
  if public.my_role() is distinct from 'super_admin' then raise insufficient_privilege; end if;
  if decision not in ('approved','rejected') then raise exception 'Invalid decision'; end if;
  select * into a from public.account_applications where id=application for update;
  if not found or a.status<>'pending' then raise exception 'Application not pending'; end if;
  if decision='approved' then
    if institution is null or not exists(select 1 from public.institutions where id=institution) then
      raise exception 'Valid institution required';
    end if;
    assigned_role := case when a.account_type='teacher' then 'teacher' else 'institute_admin' end;
    update public.profiles set role=assigned_role,institution_id=institution,account_status='active',updated_at=now() where id=a.user_id;
    if assigned_role='teacher' then
      insert into public.teachers(profile_id,institution_id) values(a.user_id,institution)
      on conflict(profile_id) do update set institution_id=excluded.institution_id;
    end if;
  else
    update public.profiles set role=null,account_status='rejected',updated_at=now() where id=a.user_id;
  end if;
  update public.account_applications set status=decision,reviewed_by=auth.uid(),reviewed_at=now(),updated_at=now() where id=application;
end $$;
revoke all on function public.review_application(uuid,text,uuid) from public,anon;
grant execute on function public.review_application(uuid,text,uuid) to authenticated;

create or replace function public.assign_student(student_profile uuid, institution uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
  if public.my_role() is distinct from 'super_admin' then raise insufficient_privilege; end if;
  if not exists(select 1 from public.institutions where id=institution) then raise exception 'Unknown institution'; end if;
  perform 1 from public.profiles where id=student_profile and role='student' and account_status='active' for update;
  if not found then raise exception 'Active student required'; end if;
  if exists(select 1 from public.students where profile_id=student_profile and institution_id<>institution) then
    raise exception 'Existing memberships must not be reassigned';
  end if;
  update public.profiles set institution_id=institution,updated_at=now() where id=student_profile;
  insert into public.students(profile_id,institution_id) values(student_profile,institution)
  on conflict(profile_id) do nothing;
end $$;
revoke all on function public.assign_student(uuid,uuid) from public,anon;
grant execute on function public.assign_student(uuid,uuid) to authenticated;
commit;
