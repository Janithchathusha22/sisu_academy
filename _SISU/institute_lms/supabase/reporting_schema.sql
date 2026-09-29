-- SISU Academy: private, server-written Supabase reporting schema.
-- Run with a trusted database administrator connection. Do not expose this
-- schema through the Supabase Data API.

begin;

create schema if not exists reporting;
revoke all on schema reporting from public, anon, authenticated, service_role;

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'sisu_reporting_writer') then
        create role sisu_reporting_writer
            nologin
            nosuperuser
            nocreatedb
            nocreaterole
            noinherit
            noreplication
            nobypassrls;
    end if;
end
$$;

create table if not exists reporting.institutes (
    source_site_id varchar(64) not null,
    frappe_name varchar(140) not null,
    code varchar(12) not null,
    title text not null,
    language text not null,
    school_mode boolean not null default false,
    source_created_at timestamptz not null,
    source_modified_at timestamptz not null,
    synced_at timestamptz not null default now(),

    primary key (source_site_id, frappe_name),
    unique (source_site_id, code),
    constraint institutes_source_site_format
        check (source_site_id ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
    constraint institutes_code_format
        check (code ~ '^[A-Z][A-Z0-9]{1,11}$'),
    constraint institutes_language
        check (language in ('en', 'si', 'ta')),
    constraint institutes_title_not_blank
        check (btrim(title) <> '')
);

create table if not exists reporting.members (
    source_site_id varchar(64) not null,
    frappe_name varchar(140) not null,
    institute_frappe_name varchar(140) not null,
    role text not null,
    active boolean not null,
    source_created_at timestamptz not null,
    source_modified_at timestamptz not null,
    synced_at timestamptz not null default now(),

    primary key (source_site_id, frappe_name),
    foreign key (source_site_id, institute_frappe_name)
        references reporting.institutes (source_site_id, frappe_name)
        on update restrict
        on delete restrict,
    constraint members_role
        check (role in ('Student', 'Teacher', 'Admin'))
);

create index if not exists members_site_role_active_idx
    on reporting.members (source_site_id, role, active);

alter table reporting.institutes enable row level security;
alter table reporting.institutes force row level security;
alter table reporting.members enable row level security;
alter table reporting.members force row level security;

revoke all on reporting.institutes, reporting.members
    from public, anon, authenticated, service_role;
alter default privileges in schema reporting
    revoke all on tables from public, anon, authenticated, service_role;

grant usage on schema reporting to sisu_reporting_writer;
grant select, insert, update on reporting.institutes, reporting.members
    to sisu_reporting_writer;

drop policy if exists reporting_writer_select on reporting.institutes;
create policy reporting_writer_select on reporting.institutes
    for select to sisu_reporting_writer using (true);
drop policy if exists reporting_writer_insert on reporting.institutes;
create policy reporting_writer_insert on reporting.institutes
    for insert to sisu_reporting_writer with check (true);
drop policy if exists reporting_writer_update on reporting.institutes;
create policy reporting_writer_update on reporting.institutes
    for update to sisu_reporting_writer using (true) with check (true);

drop policy if exists reporting_writer_select on reporting.members;
create policy reporting_writer_select on reporting.members
    for select to sisu_reporting_writer using (true);
drop policy if exists reporting_writer_insert on reporting.members;
create policy reporting_writer_insert on reporting.members
    for insert to sisu_reporting_writer with check (true);
drop policy if exists reporting_writer_update on reporting.members;
create policy reporting_writer_update on reporting.members
    for update to sisu_reporting_writer using (true) with check (true);

alter role sisu_reporting_writer set statement_timeout = '30s';
alter role sisu_reporting_writer set lock_timeout = '5s';

comment on schema reporting is
    'Server-written SISU reporting snapshot; not browser-facing application storage.';
comment on table reporting.members is
    'Privacy-minimised member summary; intentionally excludes identity and contact data.';

commit;
