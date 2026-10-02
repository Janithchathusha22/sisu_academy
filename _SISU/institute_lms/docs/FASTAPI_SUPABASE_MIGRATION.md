# FastAPI / Supabase migration

## Active architecture

The connected portal uses Supabase Auth in Vue and sends the access token to
FastAPI as a bearer token. FastAPI verifies the user and performs Supabase
queries with that same token, preserving Row Level Security. Profiles,
institution memberships, courses, classes, students/teachers, schedules,
enrollments, and attendance use the normalized schema under
`supabase/migrations/`.

The repository root `.env` is the single local configuration source. Start by
copying `.env.example`; public browser values use the `VITE_` prefix and secret
or database values remain server-only.

## Migration order

1. Create a fresh local Supabase database and run the migrations in filename
   order with `npx supabase db reset`.
2. Run the RLS smoke test and both application test suites.
3. Export and back up any existing hosted/Frappe data. Map legacy names to UUID
   foreign keys and import parent tables before child tables.
4. Compare the hosted schema with the repository. Apply an additive,
   reviewed reconciliation plan; never reset a hosted database.
5. Run the read-only hosted verifier and the temporary-user Auth test before
   production cutover.

Legacy Frappe modules remain for features that have not yet been migrated.
They must not be treated as proof that a separate Frappe site contains no real
data. Assignments, exams, finance, storage, and external integrations require
their own end-to-end cutover checks before retiring the legacy runtime.
