# FastAPI / Supabase migration

## Repository assessment

The application currently contains Frappe endpoint modules, 40+ Frappe DocTypes,
and a Vue UI that calls Frappe-style methods through `frontend/src/native/client.js`.
`supabase/reporting_schema.sql` is a separate, reporting-only schema and is not
the new application's primary data model. The new primary tables are in
`supabase/migrations/202609300001_core.sql`.

See [LEGACY_DEPENDENCY_INVENTORY.md](LEGACY_DEPENDENCY_INVENTORY.md) for every
matching source, test, and documentation file found in the initial audit.

## Migration order

1. Preserve the existing Frappe application in Git history. Apply the new SQL
   migration in a fresh Supabase project. Do not run the old reporting schema
   as the new application schema.
2. Create the first Supabase Auth user. As a trusted operator in SQL Editor,
   insert that user's `auth.users.id` into `public.profiles` with role
   `super_admin`. Assign an institution as appropriate. Browser users cannot
   assign or change their own roles.
3. Set the backend and frontend environment files from their examples. The
   secret key stays only in backend configuration. Launch FastAPI and test
   `/api/health`, authentication, and RLS with real accounts.
4. Migrate the Frappe method contracts used by Vue, screen by screen. Replace
   `frontend/src/native/client.js`, `frontend/src/service.js`, and legacy URL
   links with the new Supabase Auth / FastAPI clients. Keep all UI components.
5. Export any real Frappe records before cutover, transform old record names
   into UUID foreign-key mappings, import parents before children, compare
   counts and financial totals, then retire Frappe, Bench, and reporting sync.

The repo README says the Frappe extension has not been installed on a live
site. It contains synthetic preview data. This is **not proof** that a separate
Frappe site has no real data; inspect that site before deleting anything.

## Data export and transform

On an existing Frappe site, export `IL Institute`, `IL Member`, `IL Classroom`,
`IL Enrollment`, `IL Session`, `IL Attendance`, `IL Invoice`, `IL Material`,
`IL Programme`, `IL Paper`, `IL Paper Attempt`, and related DocTypes to CSV or
JSON. Export native LMS users and courses separately. Keep a protected copy of
private files. Transform `IL Member.user` to Supabase Auth user IDs, map every
old `name` to a UUID, and translate Frappe role strings to
`super_admin`, `institute_admin`, `teacher`, or `student`. Map classrooms to
`classes`, programmes to `courses`, invoices to `payments`, and paper attempts
to `exam_results`; review differences before import. Use Supabase Storage for
files and store object paths in the application tables. Reconcile record counts,
access rules, and amounts before changing DNS.

## Current implementation boundary

The active portal entry uses Supabase email/password or Google authentication,
then exchanges that session once for a FastAPI-managed HttpOnly cookie. The
core Supabase workspace supports profile/session lookup, courses, classes,
students/teachers, and attendance. Access tokens are not attached by Vue to
normal API requests; FastAPI retains encrypted session material so its
PostgREST calls continue to execute with the user's RLS identity.

The remaining feature modules still have Frappe method contracts and are kept
for staged migration. Assignments, exams, invoices, payments, storage,
provider review operations, and external integrations are not yet fully
migrated. Do not use this milestone as a production replacement until the
database verification and live end-to-end matrix pass. See
`SUPABASE_AUTH_SETUP.md`.

## Windows PowerShell

```powershell
cd D:\new_LMS\LMS\_SISU\institute_lms\backend
Copy-Item .env.example .env
# Edit .env with your project URL and keys (never commit .env)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd D:\new_LMS\LMS\_SISU\institute_lms\frontend
Copy-Item .env.example .env.local
# Edit .env.local with your project URL, publishable key, and API URL
npm ci
npm run dev
```

The current Vue `dev` command still starts the legacy UI. The frontend Auth/API
clients require further integration before a signed-in LMS workspace can load
from FastAPI. The health route works once backend credentials are set.
