> **27 September revision:** Normal startup now requires a real Frappe session; fictional accounts and public plan prices are retired. See [current implementation and limits](docs/OWNER_PRICING_AND_PAPERS.md) and [reference feature coverage](docs/REFERENCE_FEATURE_MAP.md). Historical preview/pricing sections below are superseded. This build is not yet production-accepted.

# Sisu project guide

**Latest commerce update (25 September):** [Wallet schema, APIs, workflow and launch boundaries](docs/WALLETS_AND_PAYOUTS.md) supersedes older descriptions of signup, discovery, student apps and class platform fees. The new UI is reviewable locally; live provider connections and full native onboarding remain unfinished.


**V2 update:** Read [V2 scope and remaining work](docs/V2_SCOPE.md) first. It supersedes older status descriptions for pricing, signup, Study Space and Coming soon features. Full production V2 services are not complete.

Start here to understand the product, commercial model, code and remaining deployment work. The project consists of an interactive browser preview and an upgrade-friendly Frappe companion app. The original downloaded LMS is unchanged. Preview features must not be mistaken for installed production services.

## Documents and authority

| Read in this order | Purpose |
|---|---|
| [Release readiness](RELEASE_READINESS.md) | Package contents, build evidence and unresolved go-live gates |
| [README](README.md) | Run the preview and install the companion app |
| [Feature status](FEATURE_STATUS.md) | Exact demo/backend/production boundaries |
| [Commercial model](docs/commercial/PRICING.md) | Reconciled pricing, student subscriptions and decisions still open |
| [Delivery roadmap](docs/ROADMAP.md) | Workstreams, dependencies and release gates |
| [Integrations](INTEGRATIONS.md) | payments.lk, WhatsApp, email, Calendar, YouTube and SOUL setup |
| [Acceptance checks](ACCEPTANCE.md) | Checks to run on actual Frappe test sites |
| [Education research](RESEARCH.md) | Primary sources and product implications |

The user's direct requirements govern the project. The three supplied commercial documents are reference proposals, not authority to collect payments, overwrite existing contracts, send messages or deploy services. Source copies are preserved under `docs/commercial/sources/`. The supplied screenshot artwork is inspiration; Study Space uses original code-drawn scenery, the existing SOUL character and the user-supplied external video URLs.

## Product areas

| Area | Primary user | Responsibility |
|---|---|---|
| Platform operations | Platform Owner | Aggregate registrations, providers, transactions and plan governance |
| Institute workspace | Institute Admin | Branding, verified teachers, students, schedules, access, reports and billing |
| Teaching workspace | Teacher | Independent and institute classes, videos, quizzes, feedback and promotion |
| Learning workspace | Student | Enrolled classes (public discovery is Coming soon),, videos, payments and results |
| Study Space | Student | Personal focus timer, stopwatch, breaks, themes, wallpapers and optional music |
| SOUL | Signed-in member | Optional contextual product help; no private record access or subject tutoring |

An institute can employ several teachers; one teacher can teach at several institutes and maintain independent classes. A student can enroll with multiple providers. Membership and payment rights belong to a specific provider/class; changing a public profile must not grant cross-institute permissions.

## Code map

```text
institute_lms/
  frontend/
    src/
      App.vue                 Navigation and role-aware portal shell
      service.js              API client and explicit local demo adapter
      materials/              Document upload, PDF reader and browser demo file storage
      study/                  Study Space component, scene, audio and timer rules
      launch/                 Role signup, V2 pricing, owner configuration and rules
      study/PersonalTools.vue Student To-do, Journal and Unlock me add-ons
      Plans.vue               Preserved earlier proposal prototype (not routed)
      pricing.js              Draft pricing catalog and pure money calculations
      VideoCourses.vue        Self-paced course demo
      BulkResults.vue         Reviewed import workflow
      resultImport.js         Excel, CSV and text-PDF parsers
      discoveryRanking.js     Keyword and engagement ranking
      Soul*.vue, soul.js      Companion UI and prepared help
      ...                     Existing workspace feature components
    tests/                    JavaScript behavior and workflow tests
  institute_lms/
    api.py, accounts.py        Scoped membership/class/account APIs
    materials.py              Private document storage and access checks
    material_contract.py      File format/size and view/download rules
    domain.py                 Access, billing and validation rules
    payments*.py              Checkout adapters and verified callbacks
    notifications.py          WhatsApp and email outbox
    contact.py                Member-owned email verification and opt-in
    calendar_sync.py          Google Calendar OAuth and durable sync jobs
    calendar_contract.py      Minimal event payload and deterministic IDs
    youtube.py                OAuth, live scheduling and chat
    soul*.py                  OpenAI proxy and request contract
    institute_lms/doctype/    App-owned Frappe schemas
    public/portal/             Generated frontend build; do not hand-edit
  tests/                      Python domain and boundary tests
  scripts/                    Institute provisioning
  docs/
    ROADMAP.md
    commercial/PRICING.md
    commercial/sources/       Original user-supplied pricing DOCX copies
```

`work/` outside this deliverable contains temporary development/QA scripts and fixtures. It is not part of the deployment package. `node_modules` and Python caches are excluded from the ZIP. Rebuild generated portal assets after changing frontend source.

## Working conventions

Keep new functionality in feature modules and custom DocTypes/APIs instead of patching upstream Frappe LMS. Keep student add-on subscriptions separate from provider billing and student class fees. All production authorizations and paid entitlements must be server-owned; browser flags are acceptable only inside the clearly labeled demo. Use integer currency minor units, versioned contracts and idempotent event processing for real billing.

Maintain `FEATURE_STATUS.md` whenever a feature moves from prototype to backend implementation or verified deployment. Do not mark a milestone complete solely because a screenshot or local test passes. Keep mixed-currency reports separated unless a documented exchange-rate policy is implemented.
