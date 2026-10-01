# Sisu Academy

> **Migration in progress (1 October 2026):** The active runtime uses FastAPI-managed HttpOnly sessions, Supabase Auth, and a core Supabase workspace for courses and attendance. Remaining feature modules still contain legacy Frappe contracts and are not part of the active runtime. Live database verification is blocked until rotated credentials and the exact pooler host are supplied. See [Auth setup](docs/SUPABASE_AUTH_SETUP.md), [database verification status](docs/SUPABASE_DATABASE_VERIFICATION.md), and [migration status](docs/FASTAPI_SUPABASE_MIGRATION.md). The browser-only preview is separate.

Sisu Academy is being migrated to a Supabase-native LMS architecture:

```text
Vue 3 -> FastAPI HttpOnly session -> Supabase Auth / PostgreSQL
```

Supabase PostgreSQL is the authoritative application database. The active
runtime does not require Frappe, Bench, MariaDB or Redis and does not fall back
to the former backend when FastAPI is unavailable.

## Project layout

| Path | Purpose |
|---|---|
| `frontend/` | Existing Vue UI and same-origin FastAPI transport |
| `backend/` | Python FastAPI application and server-only Supabase client |
| `supabase/migrations/` | Primary PostgreSQL schema, constraints, RLS and Storage policies |
| `supabase/tests/` | SQL/RLS verification scaffolding |
| `docs/FRAPPE_TO_SUPABASE_MIGRATION.md` | Audited migration and cutover procedure |
| `institute_lms/` | Temporarily retained legacy Frappe source; not an active runtime |

The browser preview remains available without a backend at
`http://127.0.0.1:5178/?preview=1`. It contains fictional local data and is not
a production database.

## 1. Prepare Supabase

Create a fresh/staging Supabase project and apply the SQL files in
`supabase/migrations/` in filename order. Use the Supabase CLI when linked to a
staging project, or paste one migration at a time into the SQL Editor.

Configure Auth providers and add both development redirect URLs:

```text
http://127.0.0.1:5178
http://localhost:5178
```

Never place a Supabase secret/service key in `frontend/` or a `VITE_*`
variable.

## 2. Configure the FastAPI backend

```powershell
cd "C:\Users\Delta\Desktop\sisu_acadamy\sisu_academy\_SISU\institute_lms\backend"
Copy-Item .env.example .env
notepad .env

py -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend `.env` needs the project URL, publishable key, server-only service
role key, database URL, and a random session secret of at least 32 characters.
Authentication requests fail closed when required values are missing. Check
`http://127.0.0.1:8000/api/health` after startup.

## 3. Configure the Vue frontend

Open a second PowerShell window:

```powershell
cd "C:\Users\Delta\Desktop\sisu_acadamy\sisu_academy\_SISU\institute_lms\frontend"
Copy-Item .env.example .env.local
notepad .env.local

npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5178/`. The frontend `.env.local` contains only the
Supabase URL, publishable key and `VITE_API_BASE_URL=http://127.0.0.1:8000`.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest

cd ..\frontend
npm.cmd test
npm.cmd run build
```

Database policy tests require a disposable/local Supabase database. Do not run
destructive migration tests against production.

## Existing data

The latest repository assessment recorded only one institute and one member in
the old custom database; the remaining custom tables were empty. The large
student/class dataset in the preview is fictional browser data.

Do not delete the old database or files based only on that assessment. Restore
and export them, create Supabase Auth users, build an explicit identity map,
transform the CSV/JSON exports, import to staging and reconcile counts/hashes.
The full procedure and cutover gates are in
[`docs/FRAPPE_TO_SUPABASE_MIGRATION.md`](docs/FRAPPE_TO_SUPABASE_MIGRATION.md).

The helper `scripts/transform-frappe-export.py` transforms reviewed
`IL Institute.csv` and `IL Member.csv` exports into staging JSON without
opening either database or copying passwords.

## Migration status

The schema, authentication boundary, core LMS REST resources and frontend
transport are the first cutover slice. Advanced integrations—live payment
settlement, WhatsApp/email workers, Calendar/YouTube OAuth, SOUL and wallet
payout operations—remain disabled until their FastAPI ports and provider
sandbox tests are complete. They must never silently call the legacy Frappe
backend.
