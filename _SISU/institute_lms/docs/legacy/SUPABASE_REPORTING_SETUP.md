# SISU Academy â€” Supabase Reporting Connection

> **Legacy reference only.** Supabase is now the primary application database;
> do not configure this retired one-way reporting job.

This integration keeps Frappe/MariaDB as the authoritative application database and sends a small, one-way reporting snapshot to Supabase every five minutes.

It does **not** replace Frappe Auth, Frappe permissions, Redis, files, jobs or the application API. It does not add Supabase code to the browser.

## Data included

- Institute source ID, code, title, language and school-mode flag
- Member source ID, institute source ID, role and active flag
- Source creation/modification times and sync time

The sync intentionally excludes names of people, user/email addresses, phone numbers, physical addresses, contact preferences, consent/AI flags, files, tokens and financial fields.

## 1. Rotate disclosed credentials

Before continuing, revoke the secret key and change every password previously shared through chat. Enable MFA. Do not reuse an account password as a database or reporting-writer password.

The integration needs only a PostgreSQL connection for a restricted database role. It does not need a Supabase API secret key or the Supabase account password.

## 2. Create the private reporting schema

Open the Supabase SQL Editor with an administrator account and run:

```text
supabase/reporting_schema.sql
```

The script creates a private `reporting` schema, deny-by-default RLS and a `sisu_reporting_writer` role without login access. Keep `reporting` out of the Data API's exposed-schema list.

Generate a unique password in a password manager, then run this separately in the SQL Editor after replacing the placeholder locally:

```sql
alter role sisu_reporting_writer login password 'REPLACE_WITH_A_NEW_RANDOM_PASSWORD';
```

Never save that statement in the repository.

## 3. Create the ignored local connection file

From the project folder:

```powershell
Copy-Item .env.supabase.example .env.supabase.local
notepad .env.supabase.local
```

In the Supabase Dashboard, open **Connect** and copy the exact **Session pooler** host and project reference. For a custom role, the username is:

```text
sisu_reporting_writer.PROJECT_REF
```

Use port `5432`, database `postgres` and `sslmode=require`. Percent-encode special characters in the URL password. Then set:

```dotenv
SISU_SUPABASE_SYNC_ENABLED="1"
SISU_SUPABASE_DATABASE_URL="postgresql://..."
SISU_SUPABASE_SOURCE_SITE_ID="sisu-academy"
```

The local file is ignored by Git. Do not paste its value into chat or frontend variables.

## 4. Test a manual sync

After the updated app file has been deployed to the Frappe container, run:

```powershell
docker exec --env-file "D:\new_LMS\LMS\_SISU\institute_lms\.env.supabase.local" `
  -u frappe lms-frappe-1 bash -lc `
  'cd /home/frappe/frappe-bench && bench --site lms.localhost execute institute_lms.supabase_sync.run'
```

The expected initial result is one institute and one member. Running the command again must keep the same row count because the operation uses timestamp-protected PostgreSQL upserts.

## 5. Enable scheduled sync

The hook runs every five minutes but remains fail-closed unless `SISU_SUPABASE_SYNC_ENABLED=1` is present in the Frappe scheduler/worker environment.

For the current Docker stack, add the ignored env file to the `frappe` service and recreate the container. Do not add the secret values directly to `docker-compose.yml`.

```yaml
services:
  frappe:
    env_file:
      - path: D:/new_LMS/LMS/_SISU/institute_lms/.env.supabase.local
        required: false
```

Then validate and recreate only the Frappe service:

```powershell
cd D:\LMS\lms-develop\docker
docker compose config --quiet
docker compose up -d --force-recreate frappe
```

## 6. Acceptance checks

- A manual run returns `synced: true` with the expected counts.
- A second run does not create duplicates.
- An inactive member update appears after the next sync.
- Browser `anon` and `authenticated` roles cannot read or write the reporting tables.
- No personal/contact/payment fields exist in the reporting schema.
- Disconnecting Supabase does not prevent normal Frappe/MariaDB writes.
- Scheduler errors never print the database URL or record payloads.

## Important limitation

This is a one-way reporting copy. Changes made directly in Supabase are not written back into Frappe, and Supabase is not the transactional application database.
