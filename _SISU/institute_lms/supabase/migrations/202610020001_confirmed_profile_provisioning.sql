-- Recover application identities for confirmed Auth users created before the
-- profile trigger was installed. This uses the existing profiles and
-- account_applications schema; it does not create a parallel identity model.
begin;

create or replace function public.provision_current_profile()
returns public.profiles
language plpgsql
security definer
set search_path = ''
as $$
declare
  auth_user auth.users;
  requested text;
  safe_kind text;
  safe_name text;
  provisioned public.profiles;
begin
  if auth.uid() is null then
    raise insufficient_privilege using message = 'Authentication required';
  end if;

  select * into auth_user
  from auth.users
  where id = auth.uid();

  if not found then
    raise insufficient_privilege using message = 'Authenticated user not found';
  end if;
  if auth_user.email_confirmed_at is null then
    raise insufficient_privilege using message = 'Email confirmation required';
  end if;

  requested := lower(coalesce(auth_user.raw_user_meta_data->>'account_type', 'student'));
  safe_kind := case
    when requested in ('student', 'teacher', 'institute') then requested
    else 'student'
  end;
  safe_name := coalesce(
    left(nullif(btrim(coalesce(auth_user.raw_user_meta_data->>'full_name', '')), ''), 120),
    'Sisu user'
  );

  insert into public.profiles (
    id, username, email, full_name, profile_kind, status, country
  ) values (
    auth_user.id,
    ('user_' || left(md5(auth_user.id::text), 25))::extensions.citext,
    auth_user.email,
    safe_name,
    safe_kind,
    case when safe_kind = 'student' then 'verified' else 'pending' end,
    nullif(left(coalesce(auth_user.raw_user_meta_data->>'country', ''), 80), '')
  )
  on conflict (id) do update
  set email = excluded.email,
      -- The migration backfill deliberately left historical identities pending.
      -- A confirmed Student may complete that onboarding, but rejected/suspended
      -- users and provider roles are never elevated here.
      status = case
        when public.profiles.profile_kind = 'student'
          and excluded.profile_kind = 'student'
          and public.profiles.status = 'pending'
        then 'verified'
        else public.profiles.status
      end,
      updated_at = case
        when public.profiles.email is distinct from excluded.email
          or (
            public.profiles.profile_kind = 'student'
            and excluded.profile_kind = 'student'
            and public.profiles.status = 'pending'
          )
        then now()
        else public.profiles.updated_at
      end
  returning * into provisioned;

  if provisioned.profile_kind in ('teacher', 'institute') then
    insert into public.account_applications (user_id, account_type, details)
    values (
      auth_user.id,
      provisioned.profile_kind,
      auth_user.raw_user_meta_data - 'account_type'
    )
    on conflict (user_id) do nothing;
  end if;

  return provisioned;
end
$$;

revoke all on function public.provision_current_profile() from public, anon;
grant execute on function public.provision_current_profile() to authenticated;

commit;
