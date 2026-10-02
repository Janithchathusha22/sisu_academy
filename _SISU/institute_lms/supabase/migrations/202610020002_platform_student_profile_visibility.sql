-- Allow an approved platform administrator to list verified Student identities
-- for institution assignment. Existing profile select rules remain in place.
begin;

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
