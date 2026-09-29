# SISU Institute LMS — Technical Status and Production Readiness Report

**Report date:** 28 September 2026  
**Audience:** Project Manager, Product Owner, Technical Lead  
**Assessment type:** Functional, integration, QA and business-readiness review

## 1. Executive Summary

The SISU Institute LMS currently presents two different experiences:

1. A frontend preview that works with fictional data stored in the browser.
2. A real Frappe backend version that connects to MariaDB but is not working as a complete application.

The full-looking version seen in the browser is mainly the dummy-data preview. It contains fictional students, teachers, classrooms, payments, results and other sample records. These records are not coming from the real database.

The Frappe backend, Redis and MariaDB services can be started. The custom database tables have also been created. However, the real application cannot currently complete its main dashboard loading process because important API calls fail. The real database also contains almost no business data.

The project must therefore be classified as **not production-ready**. It should not be launched with real students, institutes, payments or confidential information in its current state.

## 2. Overall Status

| Area | Current status | Explanation |
|---|---|---|
| Frontend dummy preview | Working | Runs with fictional browser data |
| Frontend production build | Builds successfully | Vite can create production assets |
| Frappe service | Running | Responds on port 8000 |
| MariaDB and Redis | Running | Containers and database connections are available |
| Custom database schema | Installed | 42 custom `IL` tables were found |
| Real business data | Almost empty | Only one institute and one administrator membership exist |
| Frontend-to-backend integration | Partial and failing | Some APIs work, but critical APIs fail |
| Main real dashboard | Not working | Dashboard initialization stops on an API error |
| Authentication and onboarding | Incomplete | Required provider, owner, email, Google and phone setup is missing |
| External integrations | Not configured | Payments, WhatsApp, email, Google, YouTube and AI are unavailable |
| Production readiness | Failed | The application is not safe or complete enough to launch |

## 3. Project Structure

The source code is divided into frontend and backend areas:

```text
institute_lms/
├── frontend/                         Vue/Vite frontend source
│   ├── src/
│   ├── public/
│   ├── tests/
│   └── vite.config.js
│
├── institute_lms/                    Python/Frappe backend package
│   ├── api.py
│   ├── teaching.py
│   ├── profiles.py
│   ├── payments.py
│   ├── hooks.py
│   ├── public/portal/                Compiled frontend assets
│   ├── www/campus.html               Frappe `/campus` entry page
│   └── institute_lms/doctype/        Frappe database schemas
│
├── tests/                            Python unit and contract tests
├── pyproject.toml
└── README.md
```

The repeated path `institute_lms/institute_lms/doctype` is normal for a Frappe application and is not itself a defect.

However, the Docker environment is located separately at:

```text
D:\LMS\lms-develop\docker
```

The project source folder does not contain its own complete Docker setup. The custom application was copied into a Docker volume rather than mounted directly from the working source folder. This means a developer can edit the source in VS Code without those changes automatically reaching the running backend.

## 4. The Dummy-Data Frontend

### 4.1 How to identify it

The dummy preview is available through:

```text
http://127.0.0.1:5178/?preview=1
```

It is explicitly enabled only when all of the following are true:

- The frontend is running in Vite development mode.
- The hostname is `localhost`, `127.0.0.1` or `[::1]`.
- The URL contains `?preview=1`.

### 4.2 What the preview contains

The preview contains fictional examples such as:

- Synthetic students and teachers
- Example classrooms and schedules
- Simulated invoices and payments
- Sample profiles and memberships
- Sample academic results
- Demo wallet and payout activity
- Demo course and paper workflows
- Simulated email, WhatsApp and provider actions

The preview source itself labels these records as fictional. The sample records are held in browser `sessionStorage` or other local browser storage. They are not loaded from MariaDB.

### 4.3 What the preview does not do

The dummy preview does not:

- Create real Frappe users
- Save its main sample data to MariaDB
- Collect real payments
- Send real email or WhatsApp messages
- Connect a real Google account
- Create real YouTube broadcasts
- Perform real payouts
- Prove that the production backend works

Therefore, a working dummy preview must not be treated as evidence that the real system is complete.

## 5. Frontend-to-Backend Connection

### 5.1 Port 5178

The frontend running on port 5178 is a Vite development server.

During testing, this URL was called:

```text
http://127.0.0.1:5178/api/method/institute_lms.portal_session.current
```

It returned the frontend HTML page instead of a JSON API response. This proves that the currently running port 5178 frontend is not connected to the Frappe backend.

The Vite configuration supports a backend proxy, but only when `SISU_FRAPPE_URL` is provided before the Vite server starts. That proxy was not active in the tested process.

### 5.2 Port 8000

The following URL is served directly by Frappe:

```text
http://127.0.0.1:8000/campus
```

This version does make real calls to endpoints such as:

```text
/api/method/institute_lms.api.bootstrap
/api/method/institute_lms.api.dashboard_summary
/api/method/institute_lms.api.classrooms
```

Therefore, it would be inaccurate to say that no frontend-to-backend connection exists anywhere. The technically correct conclusion is:

> Port 5178 is currently disconnected from the backend. Port 8000 serves a frontend that is connected to the backend, but the integrated application still fails because critical APIs and required configuration are incomplete.

## 6. Backend and Database Status

### 6.1 What is working

The following Docker services were successfully started:

- Frappe
- MariaDB
- Redis

The following routes returned HTTP 200 responses:

- Frappe home page
- Native LMS page
- SISU `/campus` page
- Portal session API
- Bootstrap API
- Classroom list API
- Schedule API
- News API
- Invoice API
- Notification API
- Programme API
- Operations and support API
- Papers API
- Wallet dashboard API

The database contained 42 custom SISU tables. This confirms that the backend service and database infrastructure are not completely absent or completely dead.

### 6.2 What is not working

The backend is not operational as a complete business system. The database currently contains:

| Record type | Count |
|---|---:|
| Institutes | 1 |
| Institute members | 1 |
| Classrooms | 0 |
| Sessions | 0 |
| Invoices | 0 |
| Public profiles | 0 |
| Verified phones | 0 |
| Wallets | 0 |
| Registration requests | 0 |

This means the real site has no meaningful student, teacher, classroom, lesson or payment data.

## 7. Critical Runtime Errors

### 7.1 Main dashboard API failure

The authenticated dashboard loading sequence produced:

```text
api.bootstrap          -> HTTP 200
api.dashboard_summary  -> HTTP 417
```

The server error was:

```text
SQL functions are not allowed as strings in SELECT:
sum(amount) as total
```

The backend uses aggregate expressions as strings in a Frappe query. The installed Frappe 17 version rejects this form.

This is a critical defect because the frontend calls `dashboard_summary` near the start of its refresh process. When that call fails, the remaining dashboard initialization stops. As a result, the real application cannot load normally even though the server process is running.

### 7.2 Missing verified institute profile

The following APIs failed:

```text
api.teachers       -> HTTP 417
teaching.overview  -> HTTP 417
```

Server response:

```text
Verify the institute profile first
```

The provisioning process created an institute record and an administrator membership, but it did not create and verify the public institute profile required by the teacher and provider dashboard APIs.

This creates a broken first-use workflow: the institute exists, but important administrator screens cannot operate because a separate required profile has not been prepared.

### 7.3 Administrator identity mismatch

Two server endpoints returned different identities for the same logged-in user.

Portal session response:

```json
{
  "name": "AD-SISU-0001",
  "role": "Admin",
  "user": "Administrator"
}
```

Bootstrap response:

```json
{
  "name": null,
  "role": "Admin",
  "user": "Administrator"
}
```

The backend treats the Frappe `Administrator` account as a special technical operator and replaces its real membership with an unnamed administrator identity in some APIs.

This caused the contact settings API to fail with:

```text
HTTP 403: Use a named institute member account
```

The current local environment therefore does not represent a correctly provisioned institute administrator account.

### 7.4 Profile and directory access failure

The profile search API returned:

```text
HTTP 403: Complete your profile and verification first
```

No verified public profile currently exists in the database. The profile directory and related membership workflows cannot be treated as operational.

## 8. External Integrations

The current Frappe site has no active configuration for:

- Outgoing email
- Google login
- Google Calendar OAuth
- SMS or mobile verification
- WhatsApp Cloud API
- payments.lk
- PayHere
- YouTube OAuth and live broadcasts
- OpenAI/SOUL
- Platform owner provisioning
- Payout exchange rates and financial operations

The database inspection found:

```text
Outgoing email accounts: 0
Enabled Google login keys: 0
Verified phone records: 0
```

Therefore, source code for an integration may exist, but the integration itself is not usable in this environment.

## 9. Build and Test Results

### 9.1 Passing checks

The following checks passed when run using working commands:

```text
Python unit/contract tests: 134 passed
Frontend tests:             53 passed
Vite production build:      passed
```

These results show that many isolated rules and preview workflows have tests.

### 9.2 Important testing limitations

Most Python tests use test doubles or mocked Frappe/provider boundaries. They do not prove that the same code works against a live Frappe 17 database.

This limitation was demonstrated by the real `dashboard_summary` API failure. All Python tests passed, but the live API still failed.

There is no completed evidence for:

- Full real student journey
- Full real teacher journey
- Full real institute administrator journey
- Two-site tenant isolation
- Real payment and webhook processing
- Real email or WhatsApp delivery
- Real Google authentication
- Real YouTube broadcasting
- Database rollback and concurrency behaviour
- Backup and restore
- Security and accessibility certification

### 9.3 Windows test-script defect

The standard command:

```text
npm test
```

failed on Windows because the package script uses a wildcard that is not expanded correctly:

```text
node --test tests/*.test.mjs
```

The tests passed only after running Node's test runner against the test directory directly. The project documentation and package script therefore do not currently provide a reliable cross-platform test command.

### 9.4 Frappe build integration failure

The standalone Vite build passed. However, the standard Frappe command:

```text
bench build --app institute_lms
```

failed with:

```text
TypeError: The "paths[0]" argument must be of type string.
Received undefined.
```

The compiled assets already present in the project can be served, but a clean standard Frappe rebuild is not currently reliable.

## 10. Business Impact

If the current system were presented as a completed product, stakeholders could incorrectly assume that:

- The visible students and teachers are stored in the real database.
- Payments shown in the preview are real or tested.
- Email and WhatsApp messages are being delivered.
- Real users can complete registration and verification.
- The main dashboard is connected and operational.
- The system has passed production acceptance.

Those assumptions would be incorrect.

The current working preview is useful for reviewing design, navigation and proposed workflows. It is not proof of a completed operational LMS.

## 11. Production Readiness Decision

The release decision is:

```text
Frontend design preview:          PASS
Dummy-data workflows:             PASS
Backend service startup:          PARTIAL PASS
Database schema installation:     PASS
Real frontend/backend operation:  FAIL
Core dashboard:                   FAIL
Real onboarding:                  FAIL
External integrations:            FAIL
Security/operations readiness:    FAIL
Overall production readiness:     FAIL
```

### Final decision

**Do not launch this project with real users, real payments or confidential data in its current state.**

## 12. Recommended Delivery Sequence

The recommended order of work is:

1. Repair the live dashboard API and verify the complete dashboard loading sequence against Frappe 17.
2. Define and implement one complete institute provisioning flow, including a named administrator, verified institute profile and owner approval responsibilities.
3. Establish a reliable development structure where the working source and Docker backend use the same application files.
4. Make the standard Frappe build and Windows test commands reliable.
5. Create real test accounts for Student, Teacher, Institute Admin and Platform Owner.
6. Run end-to-end tests against the real MariaDB database for every core role.
7. Configure and test integrations one at a time using provider sandboxes.
8. Complete payment reconciliation, refunds, security review, tenant isolation, backup/restore and operational monitoring.
9. Update the documentation so preview features and production features are clearly separated.
10. Perform formal staging acceptance before approving any production release.

## 13. Plain-Language Conclusion

The project currently has a convincing frontend demonstration. That demonstration works mainly because it uses prepared fictional data inside the browser.

There is also a real backend and a real database, but they do not currently support the full demonstrated experience. Some API calls work, while critical calls fail. The real database is almost empty, onboarding is incomplete and third-party services are not configured.

In simple terms:

> The demo shows what the product is intended to look like. It does not prove that the real product is working.

> The backend and database can start, but the complete business application is not operational.

> The frontend and backend have a partial technical connection on port 8000, but they are not successfully integrated into a working end-to-end system.

