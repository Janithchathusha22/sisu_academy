-- SISU Academy primary application schema.
-- This is deliberately independent of the legacy reporting schema.

begin;

create extension if not exists pgcrypto;
create extension if not exists citext with schema extensions;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := statement_timestamp();
  return new;
end;
$$;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username extensions.citext not null unique,
  full_name text not null,
  profile_kind text not null check (profile_kind in ('student', 'teacher', 'institute')),
  status text not null default 'pending' check (status in ('pending', 'verified', 'rejected', 'suspended')),
  language text not null default 'en' check (language in ('en', 'si', 'ta')),
  country text,
  bio text,
  tagline text,
  curriculum text,
  languages text[] not null default '{}',
  grades text[] not null default '{}',
  qualifications text,
  socials jsonb not null default '{}'::jsonb check (jsonb_typeof(socials) = 'object'),
  avatar_path text,
  cover_path text,
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  review_reason text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_username_format check (username::text ~ '^[a-z][a-z0-9_]{2,29}$'),
  constraint profiles_full_name_not_blank check (btrim(full_name) <> ''),
  constraint profiles_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.platform_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('super_admin', 'finance_admin', 'support_admin')),
  active boolean not null default true,
  granted_by uuid references auth.users(id) on delete set null,
  granted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, role)
);

create table public.institutions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references auth.users(id) on delete set null,
  code extensions.citext not null unique,
  title text not null,
  logo_path text,
  accent text,
  language text not null default 'en' check (language in ('en', 'si', 'ta')),
  school_mode boolean not null default false,
  base_fee_minor bigint not null default 0 check (base_fee_minor >= 0),
  currency text not null default 'LKR' check (currency ~ '^[A-Z]{3}$'),
  billing_day smallint not null default 1 check (billing_day between 1 and 28),
  support_email text,
  phone text,
  address text,
  city text,
  active boolean not null default true,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint institutions_code_format check (code::text ~ '^[A-Z][A-Z0-9]{1,11}$'),
  constraint institutions_title_not_blank check (btrim(title) <> ''),
  constraint institutions_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.institution_memberships (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  user_id uuid not null references auth.users(id) on delete restrict,
  role text not null check (role in ('student', 'teacher', 'institute_admin')),
  status text not null default 'pending' check (status in ('pending', 'active', 'rejected', 'left', 'removed', 'suspended')),
  member_code text,
  display_name text not null,
  language text not null default 'en' check (language in ('en', 'si', 'ta')),
  whatsapp_opt_in boolean not null default false,
  email_opt_in boolean not null default false,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint institution_memberships_display_name_not_blank check (btrim(display_name) <> ''),
  constraint institution_memberships_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (institution_id, user_id),
  unique (institution_id, member_code),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table private.user_contacts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  date_of_birth date,
  gender text,
  gender_description text,
  contact_phone text,
  city text,
  address text,
  guardian_name text,
  guardian_relationship text,
  guardian_phone text,
  guardian_email text,
  guardian_permission boolean not null default false,
  whatsapp_phone text,
  notification_language text not null default 'en' check (notification_language in ('en', 'si', 'ta')),
  consent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table private.verified_phones (
  user_id uuid primary key references auth.users(id) on delete cascade,
  phone text not null,
  verified_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint verified_phones_e164 check (phone ~ '^\+[1-9][0-9]{7,14}$')
);

create table public.courses (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  created_by uuid not null references auth.users(id) on delete restrict,
  title text not null,
  description text not null default '',
  teaching_medium text,
  published boolean not null default false,
  active boolean not null default true,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint courses_title_not_blank check (btrim(title) <> ''),
  constraint courses_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.course_modules (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  course_id uuid not null,
  title text not null,
  position integer not null check (position >= 0),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint course_modules_course_fk foreign key (course_id, institution_id)
    references public.courses(id, institution_id) on delete cascade,
  constraint course_modules_title_not_blank check (btrim(title) <> ''),
  constraint course_modules_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (course_id, position),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.lessons (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  module_id uuid not null,
  title text not null,
  description text not null default '',
  video_url text,
  storage_path text,
  position integer not null check (position >= 0),
  published boolean not null default false,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint lessons_module_fk foreign key (module_id, institution_id)
    references public.course_modules(id, institution_id) on delete cascade,
  constraint lessons_title_not_blank check (btrim(title) <> ''),
  constraint lessons_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (module_id, position),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.programmes (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  provider_profile_id uuid references public.profiles(id) on delete restrict,
  title text not null,
  description text not null default '',
  cover_path text,
  duration_months integer check (duration_months between 1 and 60),
  fee_minor bigint not null default 0 check (fee_minor >= 0),
  currency text not null default 'LKR' check (currency ~ '^[A-Z]{3}$'),
  starts_on date,
  ends_on date,
  active boolean not null default true,
  published boolean not null default false,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint programmes_title_not_blank check (btrim(title) <> ''),
  constraint programmes_date_order check (ends_on is null or starts_on is null or ends_on >= starts_on),
  constraint programmes_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.classes (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  course_id uuid,
  programme_id uuid,
  teacher_membership_id uuid,
  public_provider_profile_id uuid references public.profiles(id) on delete restrict,
  owner_type text not null default 'institution' check (owner_type in ('institution', 'teacher')),
  owner_user_id uuid references auth.users(id) on delete restrict,
  teacher_access text not null default 'teaching_only' check (teacher_access in ('teaching_only', 'full_control')),
  teacher_assignment_active boolean not null default true,
  title text not null,
  subject text not null,
  description text not null default '',
  profile_image_path text,
  cover_image_path text,
  font text not null default 'sans' check (font in ('sans', 'serif', 'handwritten')),
  fee_minor bigint not null default 0 check (fee_minor >= 0),
  currency text not null default 'LKR' check (currency ~ '^[A-Z]{3}$'),
  fee_mode text not null default 'paid' check (fee_mode in ('paid', 'free')),
  billing_type text not null default 'one_time' check (billing_type in ('one_time', 'monthly', 'programme_module')),
  exam_date date,
  exam_type text,
  curriculum text,
  grade text,
  teaching_medium text,
  schedule_label text,
  motivation text,
  comments_enabled boolean not null default true,
  allow_teacher_access_override boolean not null default false,
  published boolean not null default false,
  active boolean not null default true,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint classes_course_fk foreign key (course_id, institution_id)
    references public.courses(id, institution_id) on delete restrict,
  constraint classes_programme_fk foreign key (programme_id, institution_id)
    references public.programmes(id, institution_id) on delete restrict,
  constraint classes_teacher_fk foreign key (teacher_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint classes_title_not_blank check (btrim(title) <> ''),
  constraint classes_subject_not_blank check (btrim(subject) <> ''),
  constraint classes_owner_shape check (
    (owner_type = 'institution' and owner_user_id is null)
    or (owner_type = 'teacher' and owner_user_id is not null)
  ),
  constraint classes_programme_billing_shape check (billing_type <> 'programme_module' or programme_id is not null),
  constraint classes_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.class_sessions (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  title text not null,
  description text not null default '',
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  mode text not null check (mode in ('physical', 'online')),
  location text,
  meeting_provider text check (meeting_provider in ('youtube', 'zoom', 'google_meet')),
  meeting_url text,
  youtube_id text,
  status text not null default 'scheduled' check (status in ('scheduled', 'live', 'completed', 'cancelled')),
  comments text not null default 'inherit' check (comments in ('inherit', 'enabled', 'disabled')),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint class_sessions_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint class_sessions_time_order check (ends_at > starts_at),
  constraint class_sessions_title_not_blank check (btrim(title) <> ''),
  constraint class_sessions_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.materials (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  class_session_id uuid,
  title text not null,
  kind text not null check (kind in ('document', 'recording', 'link')),
  description text not null default '',
  storage_bucket text,
  storage_path text,
  preview_storage_path text,
  external_url text,
  youtube_id text,
  filename text,
  content_type text,
  size_bytes bigint check (size_bytes is null or size_bytes >= 0),
  download_policy text not null default 'view_only' check (download_policy in ('view_only', 'downloadable')),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint materials_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint materials_session_fk foreign key (class_session_id, institution_id)
    references public.class_sessions(id, institution_id) on delete restrict,
  constraint materials_location check (
    storage_path is not null or external_url is not null or youtube_id is not null
  ),
  constraint materials_title_not_blank check (btrim(title) <> ''),
  constraint materials_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.programme_modules (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  programme_id uuid not null,
  class_id uuid not null,
  teacher_membership_id uuid not null,
  title text not null,
  duration_weeks integer not null check (duration_weeks between 1 and 52),
  starts_on date,
  position integer not null check (position >= 0),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint programme_modules_programme_fk foreign key (programme_id, institution_id)
    references public.programmes(id, institution_id) on delete cascade,
  constraint programme_modules_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint programme_modules_teacher_fk foreign key (teacher_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint programme_modules_title_not_blank check (btrim(title) <> ''),
  constraint programme_modules_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (programme_id, class_id),
  unique (programme_id, position),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.programme_enrollments (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  programme_id uuid not null,
  student_membership_id uuid not null,
  status text not null default 'active' check (status in ('pending', 'active', 'completed', 'cancelled')),
  billing_enrollment_id uuid,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint programme_enrollments_programme_fk foreign key (programme_id, institution_id)
    references public.programmes(id, institution_id) on delete restrict,
  constraint programme_enrollments_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint programme_enrollments_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (programme_id, student_membership_id),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.enrollments (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  student_membership_id uuid not null,
  programme_enrollment_id uuid,
  fee_minor bigint not null default 0 check (fee_minor >= 0),
  currency text not null default 'LKR' check (currency ~ '^[A-Z]{3}$'),
  status text not null default 'active' check (status in ('pending', 'active', 'completed', 'cancelled', 'suspended')),
  access_override text not null default 'automatic' check (access_override in ('automatic', 'open', 'closed')),
  grace_until date,
  override_reason text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint enrollments_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint enrollments_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint enrollments_programme_fk foreign key (programme_enrollment_id, institution_id)
    references public.programme_enrollments(id, institution_id) on delete restrict,
  constraint enrollments_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (class_id, student_membership_id),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

alter table public.programme_enrollments
  add constraint programme_enrollments_billing_enrollment_fk
  foreign key (billing_enrollment_id, institution_id)
  references public.enrollments(id, institution_id) on delete restrict
  deferrable initially deferred;

create table public.attendance (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  class_session_id uuid not null,
  student_membership_id uuid not null,
  channel text not null check (channel in ('physical', 'online')),
  status text not null check (status in ('present', 'absent', 'excused')),
  recorded_at timestamptz not null default now(),
  recorded_by uuid references auth.users(id) on delete set null,
  note text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint attendance_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint attendance_session_fk foreign key (class_session_id, institution_id)
    references public.class_sessions(id, institution_id) on delete restrict,
  constraint attendance_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint attendance_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (class_session_id, student_membership_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.assignments (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  title text not null,
  instructions text not null default '',
  status text not null default 'draft' check (status in ('draft', 'published', 'closed', 'archived')),
  due_at timestamptz,
  max_points numeric(8,2) not null default 100 check (max_points >= 0),
  allow_upload boolean not null default true,
  published_by uuid references auth.users(id) on delete set null,
  published_at timestamptz,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint assignments_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint assignments_title_not_blank check (btrim(title) <> ''),
  constraint assignments_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.assignment_submissions (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  assignment_id uuid not null,
  student_membership_id uuid not null,
  status text not null default 'draft' check (status in ('draft', 'submitted', 'graded', 'returned')),
  answer_text text,
  storage_path text,
  submitted_at timestamptz,
  score numeric(8,2) check (score is null or score >= 0),
  feedback text,
  graded_by uuid references auth.users(id) on delete set null,
  graded_at timestamptz,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint assignment_submissions_assignment_fk foreign key (assignment_id, institution_id)
    references public.assignments(id, institution_id) on delete restrict,
  constraint assignment_submissions_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint assignment_submissions_answer check (answer_text is not null or storage_path is not null or status = 'draft'),
  constraint assignment_submissions_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (assignment_id, student_membership_id),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.exams (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  material_id uuid,
  title text not null,
  description text not null default '',
  source text not null default 'manual' check (source in ('manual', 'ai', 'imported')),
  status text not null default 'draft' check (status in ('draft', 'published', 'closed', 'archived')),
  duration_minutes integer not null check (duration_minutes between 1 and 360),
  opens_at timestamptz,
  closes_at timestamptz,
  max_marks numeric(8,2) not null default 0 check (max_marks >= 0),
  allow_upload boolean not null default false,
  published_by uuid references auth.users(id) on delete set null,
  published_at timestamptz,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exams_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint exams_material_fk foreign key (material_id, institution_id)
    references public.materials(id, institution_id) on delete restrict,
  constraint exams_time_order check (closes_at is null or opens_at is null or closes_at > opens_at),
  constraint exams_title_not_blank check (btrim(title) <> ''),
  constraint exams_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.exam_questions (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  exam_id uuid not null,
  position integer not null check (position >= 0),
  kind text not null check (kind in ('multiple_choice', 'true_false', 'written')),
  prompt text not null,
  options jsonb,
  correct_answer jsonb,
  marks numeric(8,2) not null check (marks > 0),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exam_questions_exam_fk foreign key (exam_id, institution_id)
    references public.exams(id, institution_id) on delete cascade,
  constraint exam_questions_prompt_not_blank check (btrim(prompt) <> ''),
  constraint exam_questions_options_shape check (
    (kind = 'written' and options is null)
    or (kind <> 'written' and jsonb_typeof(options) = 'array' and jsonb_array_length(options) >= 2)
  ),
  constraint exam_questions_answer_shape check (
    (kind = 'written' and correct_answer is null) or (kind <> 'written' and correct_answer is not null)
  ),
  constraint exam_questions_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (exam_id, position),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.exam_attempts (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  exam_id uuid not null,
  student_membership_id uuid not null,
  status text not null default 'started' check (status in ('started', 'submitted', 'graded', 'expired')),
  started_at timestamptz not null default now(),
  deadline timestamptz not null,
  submitted_at timestamptz,
  answer_storage_path text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exam_attempts_exam_fk foreign key (exam_id, institution_id)
    references public.exams(id, institution_id) on delete restrict,
  constraint exam_attempts_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint exam_attempts_deadline check (deadline > started_at),
  constraint exam_attempts_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (exam_id, student_membership_id),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.exam_answers (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  attempt_id uuid not null,
  question_id uuid not null,
  answer jsonb,
  awarded_marks numeric(8,2) check (awarded_marks is null or awarded_marks >= 0),
  marker_feedback text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exam_answers_attempt_fk foreign key (attempt_id, institution_id)
    references public.exam_attempts(id, institution_id) on delete cascade,
  constraint exam_answers_question_fk foreign key (question_id, institution_id)
    references public.exam_questions(id, institution_id) on delete restrict,
  constraint exam_answers_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (attempt_id, question_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.exam_results (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  exam_id uuid not null,
  attempt_id uuid not null,
  student_membership_id uuid not null,
  score numeric(8,2) not null check (score >= 0),
  feedback text,
  graded_by uuid references auth.users(id) on delete set null,
  graded_at timestamptz not null default now(),
  published_at timestamptz,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exam_results_exam_fk foreign key (exam_id, institution_id)
    references public.exams(id, institution_id) on delete restrict,
  constraint exam_results_attempt_fk foreign key (attempt_id, institution_id)
    references public.exam_attempts(id, institution_id) on delete restrict,
  constraint exam_results_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint exam_results_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (exam_id, student_membership_id),
  unique (attempt_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.announcements (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  headline text not null,
  body text not null,
  created_by uuid references auth.users(id) on delete set null,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint announcements_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint announcements_headline_not_blank check (btrim(headline) <> ''),
  constraint announcements_body_not_blank check (btrim(body) <> ''),
  constraint announcements_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  class_id uuid not null,
  class_session_id uuid not null,
  student_membership_id uuid not null,
  body text not null,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint feedback_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint feedback_session_fk foreign key (class_session_id, institution_id)
    references public.class_sessions(id, institution_id) on delete restrict,
  constraint feedback_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint feedback_body_not_blank check (btrim(body) <> ''),
  constraint feedback_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (class_session_id, student_membership_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.news (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  author_membership_id uuid,
  headline text not null,
  description text not null default '',
  cta_label text,
  cta_url text,
  starts_on date not null,
  ends_on date not null,
  published boolean not null default false,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint news_author_fk foreign key (author_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint news_date_order check (ends_on >= starts_on),
  constraint news_headline_not_blank check (btrim(headline) <> ''),
  constraint news_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.news_images (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  news_id uuid not null,
  storage_path text not null,
  alt_text text not null,
  position integer not null check (position between 0 and 4),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint news_images_news_fk foreign key (news_id, institution_id)
    references public.news(id, institution_id) on delete cascade,
  constraint news_images_alt_not_blank check (btrim(alt_text) <> ''),
  constraint news_images_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (news_id, position),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  enrollment_id uuid,
  programme_enrollment_id uuid,
  student_membership_id uuid not null,
  class_id uuid not null,
  amount_minor bigint not null check (amount_minor >= 0),
  beneficiary_minor bigint not null default 0 check (beneficiary_minor >= 0),
  platform_minor bigint not null default 0 check (platform_minor >= 0),
  currency text not null default 'LKR' check (currency ~ '^[A-Z]{3}$'),
  due_date date not null,
  installment integer not null default 1 check (installment >= 1),
  billing_month date,
  status text not null default 'unpaid' check (status in ('unpaid', 'paid', 'overdue', 'void', 'refunded')),
  paid_at timestamptz,
  receipt_number text,
  gateway_status text,
  gateway_checkout_id text,
  gateway_request_key text,
  provider_payment_id text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint invoices_enrollment_fk foreign key (enrollment_id, institution_id)
    references public.enrollments(id, institution_id) on delete restrict,
  constraint invoices_programme_enrollment_fk foreign key (programme_enrollment_id, institution_id)
    references public.programme_enrollments(id, institution_id) on delete restrict,
  constraint invoices_student_fk foreign key (student_membership_id, institution_id)
    references public.institution_memberships(id, institution_id) on delete restrict,
  constraint invoices_class_fk foreign key (class_id, institution_id)
    references public.classes(id, institution_id) on delete restrict,
  constraint invoices_split_reconciles check (beneficiary_minor + platform_minor = amount_minor),
  constraint invoices_billing_month_first check (billing_month is null or extract(day from billing_month) = 1),
  constraint invoices_anchor check (enrollment_id is not null or programme_enrollment_id is not null),
  constraint invoices_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (provider_payment_id),
  unique (gateway_request_key),
  unique (enrollment_id, billing_month),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.payments (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  invoice_id uuid not null,
  provider text not null,
  provider_reference text not null,
  amount_minor bigint not null check (amount_minor >= 0),
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  status text not null default 'pending' check (status in ('pending', 'authorized', 'paid', 'failed', 'cancelled', 'refunded')),
  paid_at timestamptz,
  receipt_storage_path text,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint payments_invoice_fk foreign key (invoice_id, institution_id)
    references public.invoices(id, institution_id) on delete restrict,
  constraint payments_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (provider, provider_reference),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid references public.institutions(id) on delete restrict,
  recipient_user_id uuid not null references auth.users(id) on delete cascade,
  event_key text,
  channel text not null default 'in_app' check (channel in ('in_app', 'email', 'whatsapp')),
  subject text,
  body text not null,
  status text not null default 'queued' check (status in ('queued', 'accepted', 'failed', 'skipped', 'review')),
  attempts integer not null default 0 check (attempts >= 0),
  next_attempt_at timestamptz,
  provider_id text,
  last_error text,
  read_at timestamptz,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint notifications_body_not_blank check (btrim(body) <> ''),
  constraint notifications_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (event_key, recipient_user_id, channel),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  requester_user_id uuid not null references auth.users(id) on delete restrict,
  subject text not null,
  category text not null check (category in ('account', 'payment', 'classroom', 'technical', 'other')),
  status text not null default 'open' check (status in ('open', 'in_progress', 'resolved')),
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint support_tickets_subject_not_blank check (btrim(subject) <> ''),
  constraint support_tickets_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (id, institution_id),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.support_replies (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete restrict,
  ticket_id uuid not null,
  author_user_id uuid not null references auth.users(id) on delete restrict,
  body text not null,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint support_replies_ticket_fk foreign key (ticket_id, institution_id)
    references public.support_tickets(id, institution_id) on delete restrict,
  constraint support_replies_body_not_blank check (btrim(body) <> ''),
  constraint support_replies_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.audit_events (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid references public.institutions(id) on delete restrict,
  actor_user_id uuid references auth.users(id) on delete set null,
  event_type text not null,
  entity_type text not null,
  entity_id uuid,
  before_state jsonb,
  after_state jsonb,
  reason text,
  request_id uuid,
  legacy_source_site_id text,
  legacy_frappe_name text,
  created_at timestamptz not null default now(),
  constraint audit_events_event_not_blank check (btrim(event_type) <> ''),
  constraint audit_events_entity_not_blank check (btrim(entity_type) <> ''),
  constraint audit_events_legacy_pair check ((legacy_source_site_id is null) = (legacy_frappe_name is null)),
  unique (legacy_source_site_id, legacy_frappe_name)
);

create table public.outbox_events (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid references public.institutions(id) on delete restrict,
  topic text not null,
  aggregate_type text not null,
  aggregate_id uuid,
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  status text not null default 'pending' check (status in ('pending', 'processing', 'delivered', 'failed', 'review')),
  attempts integer not null default 0 check (attempts >= 0),
  available_at timestamptz not null default now(),
  locked_at timestamptz,
  locked_by text,
  delivered_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint outbox_events_topic_not_blank check (btrim(topic) <> ''),
  constraint outbox_events_aggregate_not_blank check (btrim(aggregate_type) <> '')
);

create index profiles_status_kind_idx on public.profiles (status, profile_kind);
create index platform_roles_active_idx on public.platform_roles (role, active, user_id);
create index institution_memberships_user_idx on public.institution_memberships (user_id, status);
create index institution_memberships_tenant_role_idx on public.institution_memberships (institution_id, role, status);
create index courses_tenant_status_idx on public.courses (institution_id, active, published);
create index courses_created_by_idx on public.courses (created_by);
create index course_modules_course_position_idx on public.course_modules (course_id, position);
create index lessons_module_position_idx on public.lessons (module_id, position);
create index programmes_tenant_status_idx on public.programmes (institution_id, active, published);
create index classes_tenant_status_idx on public.classes (institution_id, active, published);
create index classes_teacher_idx on public.classes (teacher_membership_id, teacher_assignment_active);
create index class_sessions_class_starts_idx on public.class_sessions (class_id, starts_at);
create index materials_class_idx on public.materials (class_id, class_session_id);
create index programme_modules_programme_idx on public.programme_modules (programme_id, position);
create index programme_enrollments_student_idx on public.programme_enrollments (student_membership_id, status);
create index enrollments_student_status_idx on public.enrollments (student_membership_id, status);
create index enrollments_class_status_idx on public.enrollments (class_id, status);
create index attendance_class_session_idx on public.attendance (class_id, class_session_id);
create index attendance_student_idx on public.attendance (student_membership_id, recorded_at desc);
create index assignments_class_status_idx on public.assignments (class_id, status, due_at);
create index assignment_submissions_student_idx on public.assignment_submissions (student_membership_id, status);
create index exams_class_status_idx on public.exams (class_id, status, opens_at);
create index exam_attempts_student_idx on public.exam_attempts (student_membership_id, status);
create index exam_results_student_idx on public.exam_results (student_membership_id, published_at);
create index announcements_class_created_idx on public.announcements (class_id, created_at desc);
create index feedback_session_idx on public.feedback (class_session_id, created_at desc);
create index news_tenant_dates_idx on public.news (institution_id, published, starts_on, ends_on);
create index invoices_student_status_idx on public.invoices (student_membership_id, status, due_date);
create index invoices_tenant_status_idx on public.invoices (institution_id, status, due_date);
create index payments_invoice_status_idx on public.payments (invoice_id, status);
create index notifications_recipient_idx on public.notifications (recipient_user_id, read_at, created_at desc);
create index notifications_dispatch_idx on public.notifications (status, next_attempt_at) where status in ('queued', 'failed');
create index support_tickets_tenant_status_idx on public.support_tickets (institution_id, status, updated_at desc);
create index support_replies_ticket_idx on public.support_replies (ticket_id, created_at);
create index audit_events_tenant_created_idx on public.audit_events (institution_id, created_at desc);
create index outbox_events_dispatch_idx on public.outbox_events (status, available_at, created_at) where status in ('pending', 'failed');

-- Every foreign key has a covering index so parent updates/deletes and tenant
-- joins do not require full child-table scans.
create index announcements_class_fk_idx on public.announcements (class_id, institution_id);
create index announcements_created_by_fkey_idx on public.announcements (created_by);
create index announcements_institution_id_fkey_idx on public.announcements (institution_id);
create index assignment_submissions_assignment_fk_idx on public.assignment_submissions (assignment_id, institution_id);
create index assignment_submissions_graded_by_fkey_idx on public.assignment_submissions (graded_by);
create index assignment_submissions_institution_id_fkey_idx on public.assignment_submissions (institution_id);
create index assignment_submissions_student_fk_idx on public.assignment_submissions (student_membership_id, institution_id);
create index assignments_class_fk_idx on public.assignments (class_id, institution_id);
create index assignments_institution_id_fkey_idx on public.assignments (institution_id);
create index assignments_published_by_fkey_idx on public.assignments (published_by);
create index attendance_class_fk_idx on public.attendance (class_id, institution_id);
create index attendance_institution_id_fkey_idx on public.attendance (institution_id);
create index attendance_recorded_by_fkey_idx on public.attendance (recorded_by);
create index attendance_session_fk_idx on public.attendance (class_session_id, institution_id);
create index attendance_student_fk_idx on public.attendance (student_membership_id, institution_id);
create index audit_events_actor_user_id_fkey_idx on public.audit_events (actor_user_id);
create index class_sessions_class_fk_idx on public.class_sessions (class_id, institution_id);
create index class_sessions_institution_id_fkey_idx on public.class_sessions (institution_id);
create index classes_course_fk_idx on public.classes (course_id, institution_id);
create index classes_owner_user_id_fkey_idx on public.classes (owner_user_id);
create index classes_programme_fk_idx on public.classes (programme_id, institution_id);
create index classes_public_provider_profile_id_fkey_idx on public.classes (public_provider_profile_id);
create index classes_teacher_fk_idx on public.classes (teacher_membership_id, institution_id);
create index course_modules_course_fk_idx on public.course_modules (course_id, institution_id);
create index course_modules_institution_id_fkey_idx on public.course_modules (institution_id);
create index enrollments_class_fk_idx on public.enrollments (class_id, institution_id);
create index enrollments_institution_id_fkey_idx on public.enrollments (institution_id);
create index enrollments_programme_fk_idx on public.enrollments (programme_enrollment_id, institution_id);
create index enrollments_student_fk_idx on public.enrollments (student_membership_id, institution_id);
create index exam_answers_attempt_fk_idx on public.exam_answers (attempt_id, institution_id);
create index exam_answers_institution_id_fkey_idx on public.exam_answers (institution_id);
create index exam_answers_question_fk_idx on public.exam_answers (question_id, institution_id);
create index exam_attempts_exam_fk_idx on public.exam_attempts (exam_id, institution_id);
create index exam_attempts_institution_id_fkey_idx on public.exam_attempts (institution_id);
create index exam_attempts_student_fk_idx on public.exam_attempts (student_membership_id, institution_id);
create index exam_questions_exam_fk_idx on public.exam_questions (exam_id, institution_id);
create index exam_questions_institution_id_fkey_idx on public.exam_questions (institution_id);
create index exam_results_attempt_fk_idx on public.exam_results (attempt_id, institution_id);
create index exam_results_exam_fk_idx on public.exam_results (exam_id, institution_id);
create index exam_results_graded_by_fkey_idx on public.exam_results (graded_by);
create index exam_results_institution_id_fkey_idx on public.exam_results (institution_id);
create index exam_results_student_fk_idx on public.exam_results (student_membership_id, institution_id);
create index exams_class_fk_idx on public.exams (class_id, institution_id);
create index exams_institution_id_fkey_idx on public.exams (institution_id);
create index exams_material_fk_idx on public.exams (material_id, institution_id);
create index exams_published_by_fkey_idx on public.exams (published_by);
create index feedback_class_fk_idx on public.feedback (class_id, institution_id);
create index feedback_institution_id_fkey_idx on public.feedback (institution_id);
create index feedback_session_fk_idx on public.feedback (class_session_id, institution_id);
create index feedback_student_fk_idx on public.feedback (student_membership_id, institution_id);
create index institution_memberships_approved_by_fkey_idx on public.institution_memberships (approved_by);
create index institutions_owner_user_id_fkey_idx on public.institutions (owner_user_id);
create index invoices_class_fk_idx on public.invoices (class_id, institution_id);
create index invoices_enrollment_fk_idx on public.invoices (enrollment_id, institution_id);
create index invoices_programme_enrollment_fk_idx on public.invoices (programme_enrollment_id, institution_id);
create index invoices_student_fk_idx on public.invoices (student_membership_id, institution_id);
create index lessons_institution_id_fkey_idx on public.lessons (institution_id);
create index lessons_module_fk_idx on public.lessons (module_id, institution_id);
create index materials_class_fk_idx on public.materials (class_id, institution_id);
create index materials_institution_id_fkey_idx on public.materials (institution_id);
create index materials_session_fk_idx on public.materials (class_session_id, institution_id);
create index news_author_fk_idx on public.news (author_membership_id, institution_id);
create index news_images_institution_id_fkey_idx on public.news_images (institution_id);
create index news_images_news_fk_idx on public.news_images (news_id, institution_id);
create index notifications_institution_id_fkey_idx on public.notifications (institution_id);
create index outbox_events_institution_id_fkey_idx on public.outbox_events (institution_id);
create index payments_institution_id_fkey_idx on public.payments (institution_id);
create index payments_invoice_fk_idx on public.payments (invoice_id, institution_id);
create index platform_roles_granted_by_fkey_idx on public.platform_roles (granted_by);
create index profiles_reviewed_by_fkey_idx on public.profiles (reviewed_by);
create index programme_enrollments_billing_enrollment_fk_idx on public.programme_enrollments (billing_enrollment_id, institution_id);
create index programme_enrollments_institution_id_fkey_idx on public.programme_enrollments (institution_id);
create index programme_enrollments_programme_fk_idx on public.programme_enrollments (programme_id, institution_id);
create index programme_enrollments_student_fk_idx on public.programme_enrollments (student_membership_id, institution_id);
create index programme_modules_class_fk_idx on public.programme_modules (class_id, institution_id);
create index programme_modules_institution_id_fkey_idx on public.programme_modules (institution_id);
create index programme_modules_programme_fk_idx on public.programme_modules (programme_id, institution_id);
create index programme_modules_teacher_fk_idx on public.programme_modules (teacher_membership_id, institution_id);
create index programmes_provider_profile_id_fkey_idx on public.programmes (provider_profile_id);
create index support_replies_author_user_id_fkey_idx on public.support_replies (author_user_id);
create index support_replies_institution_id_fkey_idx on public.support_replies (institution_id);
create index support_replies_ticket_fk_idx on public.support_replies (ticket_id, institution_id);
create index support_tickets_requester_user_id_fkey_idx on public.support_tickets (requester_user_id);

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'profiles', 'platform_roles', 'institutions', 'institution_memberships',
    'courses', 'course_modules', 'lessons', 'programmes', 'classes',
    'class_sessions', 'materials', 'programme_modules', 'programme_enrollments',
    'enrollments', 'attendance', 'assignments', 'assignment_submissions',
    'exams', 'exam_questions', 'exam_attempts', 'exam_answers', 'exam_results',
    'announcements', 'feedback', 'news', 'news_images', 'invoices', 'payments',
    'notifications', 'support_tickets', 'support_replies', 'outbox_events'
  ]
  loop
    execute format(
      'create trigger %I before update on public.%I for each row execute function private.set_updated_at()',
      table_name || '_set_updated_at', table_name
    );
  end loop;

  foreach table_name in array array['user_contacts', 'verified_phones']
  loop
    execute format(
      'create trigger %I before update on private.%I for each row execute function private.set_updated_at()',
      table_name || '_set_updated_at', table_name
    );
  end loop;
end;
$$;

create or replace function private.reject_audit_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'audit events are append-only' using errcode = '42501';
end;
$$;

create trigger audit_events_immutable
before update or delete on public.audit_events
for each row execute function private.reject_audit_mutation();

comment on table public.profiles is 'Public application identity linked one-to-one to Supabase Auth; authorization comes from memberships/platform_roles.';
comment on table public.institution_memberships is 'Authoritative tenant role mapping. Profile kind is not an authorization role.';
comment on table public.outbox_events is 'PostgreSQL-backed durable work queue; claim with FOR UPDATE SKIP LOCKED from a trusted worker.';
comment on column public.exam_questions.correct_answer is 'Server-only answer key; never grant this column to authenticated or anon clients.';

commit;
