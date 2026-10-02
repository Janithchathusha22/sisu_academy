# Supabase database verification status

Date: 2026-10-01

## Passed locally

- Repository migration contains the 19 core application tables, foreign keys,
  indexes, and RLS definitions.
- The additive `202610010001_auth_and_rls.sql` migration creates the profile provisioning trigger,
  provider applications, opaque application sessions, restricted grants, and
  an own-application read policy.
- The verification program opens a read-only transaction and does not contain
  destructive SQL.
- Credentials are not printed by the verification program.

## Live verification not completed

No claim is made that the live database has the repository migrations. The
available direct database host did not resolve, and the saved pooler setting is
still a placeholder rather than a real Supabase pooler hostname. Therefore no
live schema query or data mutation was performed.

## Required before production

1. Rotate the previously exposed database credential and service-role key.
2. Put the exact Supabase session-pooler URL in backend
   `SUPABASE_DATABASE_URL` and the rotated service-role key in
   `SUPABASE_SERVICE_ROLE_KEY`.
3. Inspect and apply missing migrations in order without resetting the project.
4. Run `python verify_database.py` from `backend/`.
5. Review `SUPABASE_DATABASE_VERIFICATION.json`; all `missing` and
   `mismatches` entries must be empty.
6. Run the live registration, profile, course, attendance, cross-tenant RLS,
   expiry, CSRF, and logout test matrix before production cutover.
