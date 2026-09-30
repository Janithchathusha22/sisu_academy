# Legacy Frappe source

The directory `../../institute_lms/`, its DocTypes, Frappe controllers,
`scripts/provision-institute.py`, the old reporting sync and the historical
deployment documents are retained temporarily for migration comparison only.

They are **not** part of the active runtime. The supported application starts
from `backend/app/main.py` and `frontend/` and stores authoritative data in
Supabase PostgreSQL.

Why the source remains:

- useful validation and money/access rules still need parity tests;
- the old database/file backup must be restored and exported before deletion;
- advanced provider integrations still need explicit FastAPI ports;
- Git history plus this source provides a rollback/reference point during the
  staged cutover.

Do not add new product behavior to the legacy code. Do not configure Vue to
fall back to a Frappe URL when FastAPI is unavailable. Archive this directory
only after the cutover gates in `../FRAPPE_TO_SUPABASE_MIGRATION.md` pass.
