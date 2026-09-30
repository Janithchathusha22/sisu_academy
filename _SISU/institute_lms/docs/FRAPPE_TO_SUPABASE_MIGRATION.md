# Frappe to Supabase primary-database migration

## Decision

The active SISU architecture is now:

```text
Vue 3 browser app
  -> Supabase Auth (login, refresh, logout)
  -> FastAPI (Bearer access token, business authorization)
  -> Supabase PostgreSQL (authoritative application data)
  -> Supabase Storage (public media and authorized private files)
```

Frappe, Bench, MariaDB, Redis, Frappe sessions, DocTypes and the old reporting
sync are not part of the new runtime. The old source remains temporarily in
`institute_lms/` as a read-only migration reference. Do not deploy it beside the
new API or treat it as a fallback database.

## Audited source

The repository audit found:

- 44 custom DocTypes (40 physical tables, two Singles and two child tables)
- 405 fields and 108 logical Link fields
- 125 whitelisted Frappe RPC methods
- 35 MariaDB-specific raw SQL calls in 17 files
- Frappe-managed authentication, files, jobs, email and Redis locks
- browser-only preview data containing fictional users and classes

The latest historical database assessment records only one `IL Institute` and
one `IL Member`; the other 40 custom business tables were empty. That document
is not a current database backup. Verify and restore-test the original backup
before retiring the old environment.

Generic courses, modules, lessons, assignments and exam results were not custom
DocTypes. Some of them were upstream Frappe LMS records or preview-only data.
Their new PostgreSQL tables are therefore a new native SISU model, not evidence
that upstream LMS data has already been migrated.

## Authorization model

Authorization is database-backed and never accepted from browser form data or
user-editable Auth metadata.

- `profiles` holds the identity linked to `auth.users(id)`.
- `institution_memberships` holds the active per-institution role:
  `student`, `teacher` or `institute_admin`.
- `platform_roles` holds the separately managed `super_admin` role.
- Classroom ownership and assigned-teacher permissions remain separate from an
  institution role.
- Student content access is determined by enrollment, free/paid state, grace
  periods and explicit access overrides.

FastAPI repeats the authorization check before any service-role operation. RLS
provides a second boundary for calls made with a user access token.

## Data mapping

| Frappe source | Supabase destination |
|---|---|
| `User` | `auth.users` plus `profiles` |
| `IL Institute` | `institutions` |
| `IL Member` | `institution_memberships` |
| `IL Classroom` | `classes` |
| `IL Session` | `class_sessions` |
| `IL Enrollment` | `enrollments` |
| `IL Attendance` | `attendance` |
| `IL Material` / `File` | `materials` plus Storage object keys |
| `IL Programme` / child modules | `programmes`, `programme_modules` |
| `IL Paper` / attempts | `exams`, `exam_questions`, `exam_results` |
| `IL Invoice` | `invoices` |
| gateway settlement fields | `payments` |
| `IL Notification` | `notifications` |
| `IL News` / child images | `news`, `news_images` |
| native LMS course content | `courses`, `course_modules`, `lessons` after a separate upstream export |

Imported tables retain nullable `legacy_source_site_id` and
`legacy_frappe_name` identifiers for reconciliation. Application foreign keys
use UUIDs.

## Safe migration procedure

1. Freeze writes to the old site for the final export window.
2. Copy the old database and file backup out of its Docker/private volume.
3. Restore it into an isolated Frappe/MariaDB environment and record hashes.
4. Export `User` and each `IL *` table as UTF-8 CSV or JSON. Export upstream LMS
   course/lesson/assignment tables separately if they contain real data.
5. Produce a file manifest containing the old File name, privacy flag, path,
   size and SHA-256 digest. Do not upload token/password fields as plain data.
6. Create Supabase Auth users through invitations or password-reset flows. Do
   not copy password hashes, OAuth refresh tokens or active sessions.
7. Build an identity map: old Frappe User name/email -> Supabase Auth UUID.
8. Transform records in dependency order:
   institutions, profiles, memberships, courses, classes, sessions,
   enrollments, materials, attendance, assessments, invoices and payments.
9. Upload files into the matching Storage bucket and replace legacy file URLs
   with object keys.
10. Import into staging, then verify counts, orphaned foreign keys, duplicate
    legacy IDs, financial totals, hashes and tenant isolation.
11. Run authenticated allow/deny tests for every role and two institutions.
12. Cut the Vue API base URL to FastAPI only after the parity checks pass.
13. Keep the restored old system read-only until formal acceptance and a
    tested rollback window have elapsed.

## Secret handling

- Only `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` may enter the
  browser build.
- `SUPABASE_SECRET_KEY` is backend-only and bypasses RLS. Use it only after an
  explicit FastAPI permission check.
- Calendar/YouTube refresh tokens, payout details and provider API keys belong
  in a non-exposed schema or an approved secret manager, encrypted at rest.
- Previously disclosed keys/passwords must be rotated; never paste them into
  source, migration CSV files or chat.

## Cutover gates

The old runtime can be archived only when all of these are true:

- the Supabase migrations apply cleanly to a fresh project;
- RLS allow and deny cases pass for all roles;
- login, logout and token refresh work through Supabase Auth;
- FastAPI rejects missing/expired tokens with 401;
- the connected UI loads core LMS data without `/api/method`, `/login`, `/me`
  or `/lms` requests;
- private downloads require authorization or a short-lived signed URL;
- no production process requires MariaDB, Redis or Bench;
- migrated row counts, IDs, files and money totals reconcile;
- the old backup has passed a restore drill.

## Known incremental boundary

The new schema and core API establish Supabase as the only active database.
Advanced provider integrations (payments.lk/PayHere settlement, WhatsApp,
Google Calendar, YouTube, SOUL, wallet payouts and scheduled outbox workers)
must be ported and acceptance-tested before those controls are enabled in
production. No old Frappe endpoint should be used as a hidden fallback.
