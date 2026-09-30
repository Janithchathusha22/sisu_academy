-- Supabase Storage buckets and object-path authorization.

begin;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  (
    'public-media', 'public-media', true, 5242880,
    array['image/jpeg', 'image/png', 'image/webp']::text[]
  ),
  (
    'private-materials', 'private-materials', false, 26214400,
    array[
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/plain'
    ]::text[]
  ),
  (
    'private-answers', 'private-answers', false, 10485760,
    array['application/pdf']::text[]
  ),
  (
    'private-receipts', 'private-receipts', false, 10485760,
    array['application/pdf', 'image/jpeg', 'image/png', 'image/webp']::text[]
  )
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create or replace function private.try_uuid(value text)
returns uuid
language plpgsql
immutable
set search_path = ''
as $$
begin
  return value::uuid;
exception when invalid_text_representation then
  return null;
end;
$$;

create or replace function private.can_write_public_media(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  parts text[] := storage.foldername(object_name);
  institution_id uuid;
  class_id uuid;
begin
  if parts[1] = 'profiles' then
    return parts[2] = (select auth.uid())::text;
  end if;

  if parts[1] <> 'institutions' then
    return false;
  end if;

  institution_id := private.try_uuid(parts[2]);
  if institution_id is null then
    return false;
  end if;

  if parts[3] = 'classes' then
    class_id := private.try_uuid(parts[4]);
    return class_id is not null
      and exists (
        select 1 from public.classes c
        where c.id = class_id and c.institution_id = institution_id
      )
      and private.can_manage_class(class_id);
  end if;

  return private.is_institute_admin(institution_id);
end;
$$;

create or replace function private.can_read_material_object(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  parts text[] := storage.foldername(object_name);
  institution_id uuid;
  class_id uuid;
begin
  if parts[1] <> 'institutions' or parts[3] <> 'classes' then
    return false;
  end if;
  institution_id := private.try_uuid(parts[2]);
  class_id := private.try_uuid(parts[4]);
  return institution_id is not null
    and class_id is not null
    and exists (
      select 1 from public.classes c
      where c.id = class_id and c.institution_id = institution_id
    )
    and private.can_access_class_content(class_id);
end;
$$;

create or replace function private.can_write_material_object(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  parts text[] := storage.foldername(object_name);
  institution_id uuid;
  class_id uuid;
begin
  if parts[1] <> 'institutions' or parts[3] <> 'classes' then
    return false;
  end if;
  institution_id := private.try_uuid(parts[2]);
  class_id := private.try_uuid(parts[4]);
  return institution_id is not null
    and class_id is not null
    and exists (
      select 1 from public.classes c
      where c.id = class_id and c.institution_id = institution_id
    )
    and private.can_manage_class(class_id);
end;
$$;

create or replace function private.can_read_answer_object(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  parts text[] := storage.foldername(object_name);
  institution_id uuid;
  exam_id uuid;
begin
  if parts[1] <> 'institutions' or parts[3] <> 'exams' or parts[5] <> 'users' then
    return false;
  end if;
  institution_id := private.try_uuid(parts[2]);
  exam_id := private.try_uuid(parts[4]);
  return institution_id is not null
    and exam_id is not null
    and exists (
      select 1 from public.exams e
      where e.id = exam_id and e.institution_id = institution_id
    )
    and (
      parts[6] = (select auth.uid())::text
      or private.can_manage_exam(exam_id)
    );
end;
$$;

create or replace function private.can_write_answer_object(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  parts text[] := storage.foldername(object_name);
  institution_id uuid;
  exam_id uuid;
begin
  if parts[1] <> 'institutions' or parts[3] <> 'exams' or parts[5] <> 'users' then
    return false;
  end if;
  institution_id := private.try_uuid(parts[2]);
  exam_id := private.try_uuid(parts[4]);
  return institution_id is not null
    and exam_id is not null
    and parts[6] = (select auth.uid())::text
    and exists (
      select 1
      from public.exams e
      where e.id = exam_id
        and e.institution_id = institution_id
        and e.status = 'published'
        and (e.opens_at is null or e.opens_at <= now())
        and (e.closes_at is null or e.closes_at > now())
        and private.can_access_class_content(e.class_id)
    );
end;
$$;

create or replace function private.can_read_receipt_object(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  parts text[] := storage.foldername(object_name);
  institution_id uuid;
begin
  if parts[1] <> 'institutions' or parts[3] <> 'users' then
    return false;
  end if;
  institution_id := private.try_uuid(parts[2]);
  return institution_id is not null
    and (
      parts[4] = (select auth.uid())::text
      or private.is_institute_admin(institution_id)
      or private.is_platform_admin()
    );
end;
$$;

revoke all on function private.try_uuid(text) from public, anon;
revoke all on function private.can_write_public_media(text) from public, anon;
revoke all on function private.can_read_material_object(text) from public, anon;
revoke all on function private.can_write_material_object(text) from public, anon;
revoke all on function private.can_read_answer_object(text) from public, anon;
revoke all on function private.can_write_answer_object(text) from public, anon;
revoke all on function private.can_read_receipt_object(text) from public, anon;

grant execute on function private.try_uuid(text) to authenticated, service_role;
grant execute on function private.can_write_public_media(text) to authenticated, service_role;
grant execute on function private.can_read_material_object(text) to authenticated, service_role;
grant execute on function private.can_write_material_object(text) to authenticated, service_role;
grant execute on function private.can_read_answer_object(text) to authenticated, service_role;
grant execute on function private.can_write_answer_object(text) to authenticated, service_role;
grant execute on function private.can_read_receipt_object(text) to authenticated, service_role;

create policy public_media_read
on storage.objects for select to anon, authenticated
using (bucket_id = 'public-media');

create policy public_media_insert
on storage.objects for insert to authenticated
with check (
  bucket_id = 'public-media'
  and private.can_write_public_media(name)
);

create policy public_media_update
on storage.objects for update to authenticated
using (
  bucket_id = 'public-media'
  and private.can_write_public_media(name)
)
with check (
  bucket_id = 'public-media'
  and private.can_write_public_media(name)
);

create policy public_media_delete
on storage.objects for delete to authenticated
using (
  bucket_id = 'public-media'
  and private.can_write_public_media(name)
);

create policy private_materials_read
on storage.objects for select to authenticated
using (
  bucket_id = 'private-materials'
  and private.can_read_material_object(name)
);

create policy private_materials_insert
on storage.objects for insert to authenticated
with check (
  bucket_id = 'private-materials'
  and private.can_write_material_object(name)
);

create policy private_materials_update
on storage.objects for update to authenticated
using (
  bucket_id = 'private-materials'
  and private.can_write_material_object(name)
)
with check (
  bucket_id = 'private-materials'
  and private.can_write_material_object(name)
);

create policy private_materials_delete
on storage.objects for delete to authenticated
using (
  bucket_id = 'private-materials'
  and private.can_write_material_object(name)
);

create policy private_answers_read
on storage.objects for select to authenticated
using (
  bucket_id = 'private-answers'
  and private.can_read_answer_object(name)
);

create policy private_answers_insert
on storage.objects for insert to authenticated
with check (
  bucket_id = 'private-answers'
  and private.can_write_answer_object(name)
);

create policy private_answers_update
on storage.objects for update to authenticated
using (
  bucket_id = 'private-answers'
  and private.can_write_answer_object(name)
)
with check (
  bucket_id = 'private-answers'
  and private.can_write_answer_object(name)
);

create policy private_answers_delete
on storage.objects for delete to authenticated
using (
  bucket_id = 'private-answers'
  and private.can_write_answer_object(name)
);

create policy private_receipts_read
on storage.objects for select to authenticated
using (
  bucket_id = 'private-receipts'
  and private.can_read_receipt_object(name)
);

comment on policy public_media_read on storage.objects is
  'Intentional public read access, limited to the public-media bucket; all writes remain owner/tenant scoped.';
comment on policy private_receipts_read on storage.objects is
  'Receipt upload is service-role only; authenticated users receive scoped read access.';

commit;
