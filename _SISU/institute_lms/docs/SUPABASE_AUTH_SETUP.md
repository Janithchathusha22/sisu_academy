# Supabase Auth and FastAPI session setup

The active portal now authenticates with Supabase and exchanges the Supabase
session once for an opaque FastAPI session cookie. The browser does not attach
bearer tokens to normal application requests. The server encrypts Supabase
session material and stores it in `public.app_sessions`; PostgREST calls still
use the user's JWT, so Row Level Security remains effective.

## Required setup

1. Rotate any database password or service key that was previously copied into
   a repository file. Do not reuse it.
2. Apply `supabase/migrations/202609300001_core.sql` if it is not already
   present, then apply `supabase/migrations/202610010001_auth_sessions.sql`.
   Inspect first; never reset the existing project.
3. Copy `backend/.env.example` to `backend/.env` and set the project URL,
   publishable key, rotated service-role key, database URL, frontend URL, and a
   random `SESSION_SECRET` of at least 32 characters.
4. Copy `frontend/.env.example` to `frontend/.env.local` and set only the
   project URL, publishable key, and FastAPI URL. Never put the service-role key
   or database password in a `VITE_` variable.
5. In Supabase Auth URL configuration, allow the exact frontend origin and its
   `/` callback. Enable Google only after configuring its provider credentials.

## Run and verify

```powershell
cd D:\new_LMS\LMS\_SISU\institute_lms\backend
python -m pip install -r requirements.txt
python verify_database.py
uvicorn app.main:app --reload --port 8000

cd D:\new_LMS\LMS\_SISU\institute_lms\frontend
npm ci
npm test
npm run dev
```

`verify_database.py` uses a read-only transaction and writes
`docs/SUPABASE_DATABASE_VERIFICATION.json`. It prints no credentials. A live
end-to-end result is valid only after the rotated credentials and both
migrations have been supplied.

## Current cutover boundary

The active Supabase workspace covers authentication, profile/session lookup,
courses, classes, students/teachers, and attendance. The legacy Frappe modules
remain in the repository for the remaining feature-by-feature migration; they
are not deleted by this milestone.
