# SISU Academy — Supabase Migration Assessment

> **Historical assessment (pre-refactor).** Its no-cutover decision described
> the former Frappe runtime. The approved replacement is documented in
> `docs/FRAPPE_TO_SUPABASE_MIGRATION.md`; Supabase is now the primary target.

**Assessment date:** 29 September 2026  
**Audience:** Project Manager, Product Owner and Technical Lead  
**Decision:** Do not perform a production database cutover yet

## 1. Executive Summary

The current application cannot be moved from MariaDB to Supabase by adding environment variables.

SISU Academy is a Vue/Vite frontend connected to a Frappe 17 backend. Frappe currently owns the database schema, API endpoints, login sessions, roles and permissions, file access, background jobs, email queue, Redis locks and realtime events. Supabase uses a different PostgreSQL, Auth, JWT, Row Level Security and Realtime architecture.

The existing local database was inspected in read-only mode. It contains the full Frappe/LMS framework schema, but almost no SISU business data. There are 369 tables in total and 42 custom `IL` tables. Only two custom business records currently exist: one institute and one institute member. The other 40 custom tables are empty.

The safe short-term decision is to keep Frappe and MariaDB as the source of truth, repair and verify the real backend, and use managed MariaDB for production hosting. Supabase may be introduced later as a separate reporting database. Making Supabase the primary database requires a planned PostgreSQL compatibility project or a full backend redesign.

No Supabase credentials were used, no database was changed and no data was migrated during this assessment.

### Safe work completed during the assessment

- The stopped local Frappe container was started again.
- The live Frappe ping endpoint returned a successful response.
- A new Frappe backup was created inside the site's private Docker volume at `20260929_154254`.
- The backup contains the database, site configuration, public files and private files.
- The database gzip and both file archives passed integrity checks.
- A full restore drill has not yet been performed, so restore capability is not yet formally proven.
- A one-way, privacy-minimised Supabase reporting sync has been implemented and deployed to the local Frappe container.
- Its schema, RLS rules, idempotent upserts, stale-update protection and restricted writer permissions passed isolated PostgreSQL 16 validation.
- The integration remains disabled until rotated credentials and a fresh restricted PostgreSQL connection URL are configured locally.
- No connection or write has been made to the real Supabase project.

## 2. Security Action Required First

Privileged credentials were shared in a chat message. They must be treated as compromised even if the message is later deleted.

Before any connection work:

1. Revoke and replace the exposed Supabase secret key.
2. Change the Supabase account password and enable multi-factor authentication.
3. Reset the project's PostgreSQL database password.
4. Store replacement secrets only in a local ignored environment file or an approved secret manager. Do not send them through chat, commit them to Git, or place them in frontend code.

A Supabase publishable key is not a database password. A secret key is also not a PostgreSQL password. A direct database connection requires a separate database connection string/password from the Supabase Connect panel.

## 3. What Is Actually in This Project

| Area | Verified implementation |
|---|---|
| Frontend | Vue 3 and Vite |
| Backend | Frappe 17 Python application |
| Installed applications | Frappe, Frappe LMS, Payments and `institute_lms` |
| Current database | MariaDB 10.8 |
| Supporting service | Redis |
| Browser API pattern | Frappe `/api/method/...` RPC calls |
| Authentication | Frappe sessions, users, roles, CSRF and permissions |
| Supabase client | Not installed or used |
| Next.js | Not used |

The supplied `NEXT_PUBLIC_SUPABASE_*` variables belong to a Next.js application. This frontend is not Next.js, so those variables have no effect. The current Vite configuration reads `SISU_FRAPPE_URL` and forwards requests to the Frappe backend.

## 4. Local Database Audit

The local MariaDB database is approximately 20 MB including indexes.

| Finding | Result |
|---|---:|
| Total database tables | 369 |
| Custom SISU `IL` tables | 42 |
| Custom DocType definitions | 44 |
| Custom declared fields | 405 |
| Logical Frappe Link fields | 108 |
| Child-table fields | 2 |
| Password fields requiring special protection | 4 |
| Custom business records | 2 |

Exact custom business row counts:

| Table | Rows |
|---|---:|
| `IL Institute` | 1 |
| `IL Member` | 1 |
| Remaining 40 custom tables | 0 |

The empty tables include classrooms, sessions, enrolments, programmes, invoices, attendance, profiles, wallets, papers and notifications. Therefore, there is currently very little real business data to migrate. Copying the empty schema to Supabase would not make the application functional.

The database has no physical foreign-key constraints for the custom tables. Frappe manages relationships through Link metadata and application validation. Important relationships include links to Frappe `User`, Frappe `File` and native LMS records. These do not automatically map to Supabase Auth, Storage or new PostgreSQL tables.

## 5. Backend Compatibility Audit

The backend is deeply coupled to Frappe:

- 74 Python files import or call Frappe.
- 125 server methods are exposed through `@frappe.whitelist`.
- 44 custom controllers inherit from Frappe's Document model.
- 35 raw SQL calls exist across 17 source files.
- The frontend uses Frappe session cookies, CSRF handling and Frappe file uploads.
- Payment and wallet operations depend on transactions, row locks, unique indexes and Redis locks.
- Email, scheduling, private files and realtime events depend on Frappe services.

All 35 raw SQL calls use MariaDB/MySQL-style backtick table identifiers. They have not been implemented with Frappe's database-specific `multisql` support. They must be converted and integration-tested before the custom application can be considered PostgreSQL-compatible.

The current Docker bootstrap is also MariaDB-specific: it configures a MariaDB host and creates a MariaDB-backed Frappe site. It is not configured to create or connect to a PostgreSQL Frappe site.

## 6. Why a Direct Supabase Switch Would Fail

Changing environment variables would leave the following unresolved:

1. The existing MariaDB schema and data cannot be restored directly into PostgreSQL.
2. Frappe site creation expects database/user/schema privileges that must be tested against Supabase's managed PostgreSQL restrictions.
3. MariaDB-specific SQL in the custom application will fail on PostgreSQL until ported.
4. Frappe users and sessions are not Supabase Auth users or JWTs.
5. Frappe DocType permissions are not Supabase Row Level Security policies.
6. Frappe files are not automatically Supabase Storage objects.
7. Frappe Redis/Socket.IO realtime is not Supabase Realtime.
8. Frappe background jobs, email and scheduler tasks are not replaced by a database connection.
9. Exposing Frappe tables through Supabase's browser-facing Data API could bypass Frappe business rules and permissions.
10. Existing application API errors would still exist after changing the database platform.

## 7. Architecture Options

### Option A — Keep Frappe and MariaDB as Primary (Recommended)

Use a production-grade managed MariaDB service or Frappe-compatible hosting. Keep this flow:

```text
Vue frontend -> Frappe API -> MariaDB
                         -> Redis/jobs/realtime/files
```

This is the lowest-risk route because it matches the architecture already implemented and tested by the project.

### Option B — Use Supabase for Reporting Only

Keep MariaDB authoritative and copy an approved subset of non-sensitive data to a separate Supabase `reporting` schema through a server-side, one-way ETL process.

Start with the two existing business entities as a proof of concept. Do not copy Frappe users, password fields, OAuth tokens, payment secrets, private contacts or private files. Apply deny-by-default Row Level Security and validate tenant separation before browser access.

This option provides Supabase reporting features without creating a second transactional source of truth.

### Option C — New Frappe Site on PostgreSQL/Supabase

Treat this as a separate migration project:

1. Create an isolated non-production PostgreSQL site.
2. Port all database-specific SQL.
3. Test Frappe, LMS, Payments and the custom app on PostgreSQL.
4. Confirm Supabase privileges, extensions, SSL and connection mode.
5. Use direct connections for long-running workers, or the session pooler where IPv4 requires it. Do not use transaction pooling without a proven compatibility test.
6. Migrate through controlled application-level ETL, not a MariaDB dump restore.
7. Reconcile all records, permissions and financial totals.
8. Complete backup/restore, load, concurrency and rollback testing before cutover.

This still uses Frappe APIs and Frappe Auth. It does not automatically convert the application into a Supabase-native backend.

### Option D — Replace Frappe with Supabase

This is a major rewrite. It requires PostgreSQL migrations for 44 DocTypes, RLS policies, a new identity mapping, replacement server endpoints for approximately 125 API operations, new file and email workflows, and frontend changes for auth, uploads and every API call.

It should be estimated and approved as a new backend programme, not described as database setup.

## 8. Safe Migration Sequence If PostgreSQL Is Mandatory

1. Rotate all disclosed credentials.
2. Back up MariaDB and prove that the backup can be restored.
3. Pin exact Frappe, LMS, Payments and custom-app versions.
4. Restore the Frappe backend and validate its core APIs against MariaDB.
5. Build a local PostgreSQL compatibility environment first.
6. Replace raw SQL with portable Query Builder code or explicit MariaDB/PostgreSQL `multisql` variants.
7. Run live integration, transaction, locking and permission tests.
8. Create a separate non-production Supabase target and verify required privileges and connectivity.
9. Define data mappings, including Frappe names, Links, child tables, Singles, files and users.
10. Export and import in dependency order, resolving cyclic links in a second pass.
11. Validate row counts, orphan links, hashes, financial totals, date ranges and tenant isolation.
12. Dual-run and reconcile before any approved cutover.
13. Keep MariaDB intact and rollback-ready until formal acceptance.

## 9. Current Go/No-Go Decision

| Activity | Decision |
|---|---|
| Use the exposed credentials | **No-go** |
| Add the supplied Next.js variables | **No-go — wrong framework** |
| Point the current application directly at Supabase | **No-go** |
| Restore and validate the existing Frappe/MariaDB backend | **Go** |
| Plan a curated reporting proof of concept | **Go after credential rotation and approval** |
| Begin a PostgreSQL compatibility spike | **Go after scope, staging and rollback approval** |
| Production database cutover | **No-go** |

## 10. Required Management Decision

Choose one approved direction before implementation continues:

- **Recommended:** keep Frappe/MariaDB primary and optionally add Supabase reporting; or
- approve a separately estimated Frappe/PostgreSQL migration; or
- approve a full Supabase-native backend rewrite.

Database credentials should be configured locally after rotation and must not be pasted into chat.

## 11. Reference Documentation

- [Frappe: create a new site and select PostgreSQL](https://docs.frappe.io/framework/user/en/bench/reference/new-site)
- [Frappe: database API and engine-specific SQL](https://docs.frappe.io/framework/user/en/api/database)
- [Frappe: site migration command](https://docs.frappe.io/framework/user/en/bench/reference/migrate)
- [Supabase: database connection methods](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase: database password and connection information](https://supabase.com/docs/guides/database/connecting-to-postgres#database-password)
- [Supabase: API key security](https://supabase.com/docs/guides/api/api-keys)
- [Supabase: secure the Data API with grants and RLS](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase: Auth architecture](https://supabase.com/docs/guides/auth/architecture)
