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

Never infer that local migration success means the hosted schema already
matches. Back up and compare the hosted project before applying migrations;
do not run `db reset` against a hosted project.
