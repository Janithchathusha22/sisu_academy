> **Migration in progress:** A new FastAPI/Supabase foundation exists, but the Vue workspace still calls the old Frappe API. It is not yet a working FastAPI/Supabase replacement. See [migration status and Windows commands](docs/FASTAPI_SUPABASE_MIGRATION.md) and the [legacy dependency inventory](docs/LEGACY_DEPENDENCY_INVENTORY.md). The browser-only Netlify preview is separate.

> **27 September revision:** Normal startup now requires a real Frappe session; fictional accounts and public plan prices are retired. See [current implementation and limits](docs/OWNER_PRICING_AND_PAPERS.md) and [reference feature coverage](docs/REFERENCE_FEATURE_MAP.md). Historical preview/pricing sections below are superseded. This build is not yet production-accepted.

# Sisu · Institute and independent-teacher portal for Frappe LMS

**Latest commerce update (25 September):** [Wallet schema, APIs, workflow and launch boundaries](docs/WALLETS_AND_PAYOUTS.md) supersedes older descriptions of signup, discovery, student apps and class platform fees. The new UI is reviewable locally; live provider connections and full native onboarding remain unfinished.


**V2 update:** Read [V2 scope and remaining work](docs/V2_SCOPE.md) first. It supersedes older status descriptions for pricing, signup, Study Space and Coming soon features. Full production V2 services are not complete.

An upgrade-friendly companion app for the downloaded **Frappe LMS / Frappe 17 development** source. It adds an institute portal at `/campus`, without editing upstream LMS files.

**Status: working local interactive preview and implemented Frappe extension source. Not installed on a live Frappe site or verified with provider credentials.** The Windows computer has Docker installed, but its Linux engine was not running during development. The preview is not a replacement for a live backend.

Read [FEATURE_STATUS.md](FEATURE_STATUS.md) for the current feature-by-feature boundary. International onboarding, multi-provider dashboards, bulk results, GPA purchases and the new video-course editor are preview workflows. AI Quiz remains Coming soon. Profiles & connections now provides a preview directory with Follow/Join, owner verification and a corresponding site-local API; live cross-site aggregation is not complete. SOUL has an implemented OpenAI server adapter, but no key has been supplied or tested. This deliverable has not received an independent security or accessibility certification.

## Review the interface

Start with [PROJECT_GUIDE.md](PROJECT_GUIDE.md) and [RELEASE_READINESS.md](RELEASE_READINESS.md) for project organization, pricing and the D: release package.

Use the sun/moon button in the header to switch between light and dark mode in any role. Teachers can open **My classrooms → Add material** to upload PDF, PowerPoint or Word and choose **View only** or **Downloadable**. Office view-only resources need a matching PDF preview.

Student **Settings** includes cozy daylight/moonlight, five accent colors (extra colors are a Study Plus demo benefit), email verification and notification preferences. External calendar synchronization is Coming soon. **Study Space** includes optional original music, wallpapers, timers and rotating encouragement. **Apps** separates premium Study Space, US$1/month To-do and US$1/month Journal, with a fictional card-qualified three-day trial. Dated tasks appear in the LMS calendar. Staff **Plans & billing** shows V2 regional subscriptions; no real subscription is sold in this preview. Study Space is now a premium app. Native subscription checkout and entitlement activation are not connected.

Open `http://127.0.0.1:5178/` while the development server is running. Use **View as** to explore Student, Teacher, Institute Admin and Platform Owner. Sample changes persist in browser local storage. Settings → Reset sample data restores the examples. The seed contains 360 fictional students, 12 teachers and 18 classrooms across scholarship, O/L, A/L, university and online courses. All identities, collections, progress and rankings are synthetic.

Open **Learning & teaching → Video courses** to publish a course with modules and YouTube lessons. Students can enroll, play the supplied sample, mark lessons complete and open lesson quizzes. Use **Profiles & connections** to search usernames, follow providers, request membership and review profiles as the owner. The earlier Discover prototype remains in source. **Education workspace** includes usernames, codes, curriculum, country, time zone, teaser video, social links and keyword limits. Click SOUL to chat with its local guide; drag the pet to reposition it.

To restart on Windows:

```powershell
cd path\to\institute_lms\frontend
npm ci
npm run dev
```

Alternatively run `Start-Preview.ps1`. The development server binds to loopback only. Demo payment buttons do not collect money; demo notifications do not send messages. Production builds disable demo mode and use authenticated Frappe APIs. Production never silently falls back to demo data when the backend fails.

## Implemented

- Responsive dashboard, classrooms, monthly calendar, payments, carousel news, notifications, people, branding and account preferences.
- Server-resolved student, teacher and administrator memberships. Native Frappe login/password reset; no custom password storage.
- Institute names, codes, uploaded logos and brand colours. IDs such as `ST-BC-00001` and `TC-BC-0001`, using Frappe's transactional naming series.
- Classroom title, profile image, cover, subject, description, font choice, exam countdown, and 30-visible-character motivation line.
- Unicode content, searchable language picker with 40 locale choices and small locally served flags, custom locale tags, translated core navigation and right-to-left layout. English remains the fallback; most forms and explanatory copy are not fully translated. This is not a complete translation into every language.
- Physical/online sessions with date, time, venue, description, cancellation, comment overrides, YouTube links, and update notifications.
- Private PDF/PPT/PPTX/DOC/DOCX uploads, 10 MB per file, per-material view/download policy, paginated PDF reader and matching Office PDF previews. Files stay outside the database; visible content is not copy protected.
- External materials and recorded YouTube video references; no large video binaries in Frappe.
- Post-session student feedback; server enforcement of payment access and classroom/session comment controls.
- News headline up to 80 visible characters, description up to 240, CTA label up to 24, 1–5 uploaded images, and publication dates.
- Classroom enrollment with full-payment or up to 24 scheduled installments; invoice status, receipt references and history.
- Payment-gated portal content, first-payment requirement, grace dates, explicit Open/Closed overrides, and audit records. Authorized teachers can override only when an administrator enables it for their classroom.
- payments.lk hosted checkout adapter and verified webhook settlement, with PayHere retained as an optional adapter. Amount, currency, invoice, checkout, mode and signature are checked; invoice rows are locked for settlement. Provider credentials and real-site acceptance tests are still required.
- Durable WhatsApp notification outbox, consent checks, per-language templates, rate-limit backoff, provider acceptance IDs, and uncertain-delivery review states.
- Teacher Google OAuth connection; YouTube broadcast creation, schedule synchronization and start/end transition APIs. Encoder setup and stream binding are completed in YouTube Studio. Private YouTube videos retain Google's invited-account restrictions.
- Monthly institute billing snapshots: base fee includes 500 distinct active student memberships; each additional student adds LKR 50. The base fee is configurable, not assumed from the example data. Institute subscription collection is currently manual; the integrated gateway checkout is for student invoices.
- Links to the installed native LMS course, assignment, quiz and profile certificate screens.
- Compressed raster image uploads, lazy image loading, paginated APIs, database indexes, bounded page sizes, and a tree-shaken Vue production bundle.

No AI Tutor, AI Course Creator, Instructor Copilot, Skills Engine or Personalized Learning Paths were added.

## Tenant architecture

Use **one Frappe site/database per institute**, with shared `frappe`, `lms`, `payments`, and `institute_lms` app code. Route each institute hostname to its own site, for example `bc.your-domain.lk`. This isolates native LMS users, courses, submissions, certificates, files and permissions as well as the new records.

An institute code identifies a tenant; it is not an authorization secret. Each site permits exactly one `IL Institute`. The fleet provisioning tool reserves codes in a shared registry with a file lock. All provisioning processes must use the same registry to guarantee code uniqueness across sites. Do not manually provision duplicate codes outside that registry.

The custom portal's normal roles do not receive generic DocType REST/Desk access. Explicit APIs enforce memberships, classroom ownership, enrollment and payment rules before reading/writing. `System Manager` and the Frappe `Administrator` are trusted site operators.

**Native LMS content has its existing LMS permissions.** Portal payment rules protect portal sessions, materials and feedback, not arbitrary upstream routes. Keep paid videos/materials in the gated portal; do not publish the same paid content through a public native LMS course. A complete payment-to-native-course-enrollment bridge is a separate integration task requiring tests against the chosen LMS release.

## Install in a Frappe bench

The downloaded source's `pyproject.toml` declares Frappe `>=17.0.0-dev,<18.0.0` and Python `>=3.14,<3.15`. Use a compatible **Linux** bench/container and pin the exact Frappe/LMS commits. This extension's Python domain tests ran locally on Python 3.12; this is not evidence of a completed Frappe 17 installation.

1. Install Frappe, payments and the downloaded LMS in a bench using their supported setup. Finish site setup and set strong operator credentials.
2. Copy this folder to `apps/institute_lms`. From the bench root:

```bash
./env/bin/pip install -e apps/institute_lms
# Register the app once in sites/apps.txt if bench did not do it.
# Prefer `bench get-app` from a Git repository after importing this deliverable.
cd apps/institute_lms/frontend
npm ci
npm run build
cd ../../..
```

3. Ensure `institute_lms` appears once in `sites/apps.txt`. Create the institute administrator as a User on the target site. Then use the fleet registry:

```bash
python apps/institute_lms/scripts/provision-institute.py \
  --site bc.your-domain.lk --code BC --title 'Your Institute' \
  --admin-email admin@your-domain.lk --base-fee 15000
bench --site bc.your-domain.lk migrate
bench build --app institute_lms
bench --site bc.your-domain.lk enable-scheduler
bench restart
```

`15000` above is an example only. Choose your commercial base fee. Initial setup sets the site timezone to `Asia/Colombo` and creates the first institute admin membership. Admins then add members and classrooms through the portal. User creation intentionally sends no welcome email; members can use the existing Frappe reset-password flow after your mail service is configured.

4. Visit `https://bc.your-domain.lk/campus`. Configure HTTPS, DNS, site routing, workers and backups as part of normal Frappe deployment.

To configure a single existing site without the fleet registry, the underlying bench-only method is `institute_lms.setup.configure(code, title, admin_email, base_fee)`. Use the fleet registry for commercial multi-institute provisioning.

## Provider setup

See [INTEGRATIONS.md](INTEGRATIONS.md) for required configuration and provider restrictions. Secrets belong in protected server configuration / Frappe Password fields; never enter them into frontend source or a repository.

## Testing

```bash
# In a Python environment with the extension dependencies installed:
python -m unittest discover -s tests -v
cd frontend
npm ci
npm test
npm run build
```

Current verification is recorded in [FEATURE_STATUS.md](FEATURE_STATUS.md). Python tests include access precedence, billing boundaries, Unicode limits, forged payment rejection, malicious URLs, SOUL moderation/authorization boundaries, and authorization contracts with a Frappe test double. They do not exercise a real MariaDB transaction or a live Frappe session.

Browser checks completed: student blocked-classroom flow, simulated payment unlock, teacher-only classroom list, creation of a Tamil-titled classroom, admin billing calculator, Sinhala navigation, responsive mobile layout at 390 pixels, and no browser console errors in those checks.

Before production, run the acceptance checks in [ACCEPTANCE.md](ACCEPTANCE.md) against two real test sites and provider sandboxes. No live deployment, real payment, WhatsApp delivery or YouTube broadcast was performed here.

## Project map

| Path | Purpose |
|---|---|
| `frontend/src/App.vue` | Responsive portal and role-specific workflows |
| `frontend/src/service.js` | Frappe API client and explicitly separate local demo adapter |
| `frontend/src/rules.js` | Preview access rules and Unicode/date formatting |
| `institute_lms/api.py` | Authenticated, scoped operations |
| `institute_lms/domain.py` | Pure access, billing, validation and signature rules |
| `institute_lms/payments.py`, `payments_lk.py` | Gateway dispatch, hosted checkout and verified callbacks |
| `institute_lms/soul.py`, `soul_contract.py` | OpenAI proxy, bounded context, moderation and quotas |
| `frontend/src/VideoCourses.vue` | Demonstration course authoring, enrollment and player |
| `frontend/src/BulkResults.vue`, `resultImport.js` | Reviewed Excel/CSV/text-PDF result imports |
| `institute_lms/notifications.py` | WhatsApp outbox worker |
| `institute_lms/youtube.py` | Google OAuth and broadcast management |
| `institute_lms/billing.py` | Invoice deadlines and subscription snapshots |
| `institute_lms/supabase_sync.py` | Optional one-way, privacy-minimised reporting sync |
| `institute_lms/institute_lms/doctype/` | App-owned DocTypes, including SOUL settings and account requests |
| `supabase/reporting_schema.sql` | Private Supabase reporting schema, RLS and writer permissions |
| `scripts/provision-institute.py` | Shared-registry tenant provisioning |

The user's written Frappe requirements take precedence over the supplied Next.js/Supabase reference plan. The original downloaded LMS directory remains intact. This app carries AGPL-3.0 licensing alongside the original LMS licence text.
