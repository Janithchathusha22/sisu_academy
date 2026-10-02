# Supabase database verification

There are two verification levels:

- Local: `npx supabase db reset`, the SQL smoke test in
  `supabase/tests/001_primary_schema_rls_smoke.sql`, `supabase db lint`, and
  the backend/frontend test suites.
- Hosted: `python backend/verify_database.py` with a server-only
  `SUPABASE_DATABASE_URL`, followed by `python backend/verify_live_auth.py`
  with a valid `SUPABASE_SECRET_KEY` in a test-safe project.

The database verifier is read-only and prints a JSON report without credentials
or row contents. The live Auth verifier creates temporary users and requires a
server secret so it can always clean them up.

The verifier requires the
`profiles_verified_students_platform_select` policy. Its additive definition is
in `supabase/migrations/202610020002_platform_student_profile_visibility.sql`;
the SQL smoke test confirms that a verified platform administrator can see
verified student profiles while an ordinary student cannot list other student
profiles.

Never infer that local migration success means the hosted schema already
matches. Back up and compare the hosted project before applying migrations;
review the hosted migration history and apply pending migrations to a staging
project first. Do not reset or overwrite an existing hosted database.
