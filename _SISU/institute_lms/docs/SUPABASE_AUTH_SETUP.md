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

Set `VITE_SUPABASE_PROJECT_REF`, `VITE_SUPABASE_URL`,
`VITE_SUPABASE_PUBLISHABLE_KEY`, and `VITE_API_BASE_URL`. The SISU values are
pinned to project `yfdettlsvgsslzjjhoxo` and URL
`https://yfdettlsvgsslzjjhoxo.supabase.co`; startup and browser configuration
fail closed if a stale project is selected. `VITE_` values are public browser
configuration. Never put a database password or Supabase secret key in a
`VITE_` variable.

The backend reads the root `.env` explicitly. Operating-system environment
variables take precedence, so remove stale values before restarting a local
shell:

```powershell
Remove-Item Env:SUPABASE_PROJECT_REF, Env:SUPABASE_URL, Env:VITE_SUPABASE_PROJECT_REF, Env:VITE_SUPABASE_URL -ErrorAction SilentlyContinue
```

The expected token issuer is
`https://yfdettlsvgsslzjjhoxo.supabase.co/auth/v1`, and signing keys are read
from
`https://yfdettlsvgsslzjjhoxo.supabase.co/auth/v1/.well-known/jwks.json`.
Tokens must use a supported asymmetric signing algorithm, carry a matching key
ID, use audience `authenticated`, have a UUID subject, and be unexpired.
The backend also validates the JWT `iat` and `nbf` timestamps against system
UTC. When a token is rejected as not-yet-valid, safe diagnostics log the server
UTC time and how far either claim is ahead; they do not log the token or user
ID. On Windows, compare that UTC time with `Get-Date -AsUTC`. If the Windows
Time service is stopped or the offset is nonzero, run these commands in an
elevated PowerShell session, then restart FastAPI and sign in again:

```powershell
Set-Service -Name W32Time -StartupType Automatic
Start-Service -Name W32Time
w32tm /resync /force
w32tm /query /status
Get-Date -AsUTC
```

Do not disable signature, `iat`, `nbf`, or expiry validation to work around
clock skew.

`GET /api/me` keeps the public `profile_kind` separate from the server-resolved
`application_role`. An active `platform_roles.super_admin` grant takes priority
over a student public profile, while an inactive grant, profile metadata, or a
login-screen choice grants nothing. The frontend routes its workspace, sidebar,
and role label from `application_role` only. Returning to the tab or refreshing
the Supabase token re-reads `/api/me`, so a newly issued or revoked grant does
not remain hidden behind the earlier browser state.

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

After changing an environment value, stop and restart both `uvicorn` and Vite;
both processes cache configuration. A backend restart also discards any cached
JWKS client. The validator keeps its JWKS cache below Supabase's edge-cache
window and retries once with a fresh client when a signing key cannot be found.

If an API request receives `401`, the browser now removes only its local
Supabase session before returning to sign-in. After deploying this change,
reload the new frontend bundle and sign in again. This prevents a token from an
older project or signing-key generation from being replayed from browser
storage.

`GET http://127.0.0.1:8000/api/health` reports only public diagnostics: the
configured project ref, host, issuer and JWKS URL. Authentication rejection
logs contain only allow-listed JWT metadata (algorithm, key ID, claim-match
booleans and expiry); they never contain the token, authorization header,
password, subject, or a secret key.

Run `backend/verify_database.py` only after a database URL has been configured.
Run `backend/verify_live_auth.py` only against a test-safe project with a valid
server secret; it creates and then removes temporary student and teacher users.

Migrations must be reviewed and applied in filename order. Do not reset an
existing hosted project. The hosted schema must first be reconciled with the
repository migrations and backed up.
