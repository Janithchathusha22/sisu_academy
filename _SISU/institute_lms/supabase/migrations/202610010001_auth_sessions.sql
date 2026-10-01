-- Additive Supabase Auth/application-session bridge. Safe for existing records.
-- Apply after 202609300001_core.sql. This migration does not delete application data.
begin;

alter table public.profiles alter column role drop not null;
alter table public.profiles add column if not exists account_status text not null default 'active';
alter table public.profiles drop constraint if exists profiles_account_status_check;
alter table public.profiles add constraint profiles_account_status_check
  check (account_status in ('pending','active','rejected','suspended'));

create table if not exists public.account_applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  account_type text not null check (account_type in ('teacher','institute')),
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  details jsonb not null default '{}'::jsonb,
  reviewed_by uuid references public.profiles(id),
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
create index if not exists app_sessions_user_expiry_idx on public.app_sessions(user_id,expires_at);

alter table public.account_applications enable row level security;
alter table public.app_sessions enable row level security;
revoke all on public.app_sessions from anon, authenticated;
revoke insert, update, delete on public.account_applications from anon, authenticated;

drop policy if exists applications_read_own on public.account_applications;
create policy applications_read_own on public.account_applications for select to authenticated
using (user_id=(select auth.uid()) or public.my_role()='super_admin');

create or replace function public.handle_new_auth_user() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  requested text := lower(coalesce(new.raw_user_meta_data->>'account_type','student'));
  safe_role text := case when requested='student' then 'student' else null end;
  safe_status text := case when requested='student' then 'active' else 'pending' end;
begin
  insert into public.profiles(id,full_name,email,role,account_status)
  values(new.id,left(coalesce(new.raw_user_meta_data->>'full_name',''),120),new.email,safe_role,safe_status)
  on conflict (id) do nothing;
  if requested in ('teacher','institute') then
    insert into public.account_applications(user_id,account_type,details)
    values(new.id,requested,new.raw_user_meta_data - 'account_type')
    on conflict (user_id) do nothing;
  end if;
  return new;
end $$;

-- Never drop an unrelated project's Auth trigger. Fail closed for operator review.
do $$ begin
  if exists(select 1 from pg_trigger t join pg_proc p on p.oid=t.tgfoid
    where t.tgrelid='auth.users'::regclass and t.tgname='on_auth_user_created'
      and p.proname<>'handle_new_auth_user') then
    raise exception 'Existing Auth trigger requires manual review';
  end if;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- Existing Auth users without profiles are intentionally not assigned a role.
insert into public.profiles(id,email,full_name,role,account_status)
select u.id,u.email,coalesce(u.raw_user_meta_data->>'full_name',''),null,'pending'
from auth.users u left join public.profiles p on p.id=u.id where p.id is null
on conflict (id) do nothing;
commit;
