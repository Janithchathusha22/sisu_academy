# Supabase Auth and FastAPI setup

The active portal signs users in directly with Supabase Auth. Vue sends the
Supabase access token as `Authorization: Bearer <token>` on API requests.
FastAPI validates that token with Supabase Auth, loads the user's profile and
active membership, and queries PostgREST with the same token so database RLS
is always applied.

## Environment

Use the repository root `.env` as the only local environment file:

```powershell
Copy-Item .env.example .env
```

Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, and
`VITE_API_BASE_URL`. `VITE_` values are public browser configuration. Never
put a database password or Supabase secret key in a `VITE_` variable.

`SUPABASE_DATABASE_URL` is optional and is used by the read-only database
verifier. `SUPABASE_SECRET_KEY` is optional and is used only by the live Auth
test to remove the temporary test users it creates. Keep both server-only.

## Local verification

```powershell
npx supabase start
npx supabase db reset

cd backend
python -m pip install -r requirements.txt
python -m pytest
uvicorn app.main:app --reload --port 8000

cd ..\frontend
npm ci
npm test
npm run build:deploy
```

Run `backend/verify_database.py` only after a database URL has been configured.
Run `backend/verify_live_auth.py` only against a test-safe project with a valid
server secret; it creates and then removes temporary student and teacher users.

Migrations must be reviewed and applied in filename order. Do not reset an
existing hosted project. The hosted schema must first be reconciled with the
repository migrations and backed up.
