**Later user instructions:** See [Commerce update](WALLETS_AND_PAYOUTS.md). Apps are separate, the trial is three days with verified card setup, and class payments add US$1 each recurrence. Earlier conflicting Coming soon/navigation descriptions below are historical.

# V2 implementation and launch boundaries · 25 September 2026

The direct user requests govern this work. The supplied V2 Word document is the current product reference; it does not authorize deployment, charges or sending messages. Earlier commercial proposals remain historical alternatives. This package is a working preview and extension source, **not a completed production implementation of every V2 requirement**.

## Review now

- Student → Study Space: full-window focus view, native fullscreen where supported, 16 unique supplied video backgrounds, one muted stream at a time, still-scene pause, selected-scene persistence, failure fallback, light/dark/cute appearance, timer, music and encouragement. The duplicate supplied URL appears once. Files stay on CloudFront, outside Frappe storage.
- Study Space → Unlock me: Study Plus preview, To-do **US$1/month**, Journal **US$1/month**. Optional 30-day preview activation creates no charge or renewal. To-do dates appear in My schedule and export as an ICS file. Journal entries support editing, archive and restore. Data is browser-local; production subscriptions and private cross-device storage remain pending.
- A shorter role-aware sidebar groups videos, quizzes, results and native Frappe tools under Learning & teaching. Student plans live inside Study Space. Platform Owner has Overview, Control room and Plans & billing.
- Sign up / sign in: separate Institute, Individual Teacher and Student fields. Institute captures authorized person/recovery contact details; student requires an invitation code. The owner preview accepts only **danusgalagoda@gmail.com**. Demo code **123456** expires in ten minutes with five attempts. No email is sent and no real account is created.
- Native registration source uses random email codes, HMAC-protected cache entries, expiry, bounded attempts, per-IP/email throttling and exact server owner allowlisting. Successful verification creates an **IL Registration Request / Pending review**, never a User, elevated role or authenticated session. Real provisioning, invitation verification, institute business/recovery review and Frappe 2FA remain operator/integration work.
- Owner Control room demonstrates the exact A–E subscription tables, 100-student free limit, tenant/country/plan defaults and platform locks, dated overrides, limits, branding requests, billing policy, optional service prices, exam/reward configuration and reasoned before/after history. These settings are local preview data for one sample tenant, not a server configuration database or immutable audit.

## V2 coverage map

| Requirement family | Current delivery | Remaining work before production |
|---|---|---|
| Sections 1–5: global product, pricing and customization principles | International preview, explicit regional prices and separate legacy contracts | Approved country mapping/currency/tax rules; billing migration and contract versioning |
| Section 6: configurable capabilities and limits | Searchable feature catalog, effective-setting rules, limits/branding/billing controls | Database-backed per-tenant configuration, every API's enforcement, complete configurable templates and service limits |
| Sections 7–9: paid customization, owner screen and data model | Owner UI and audited browser draft; pure precedence tests | Request/approval/quote lifecycle, immutable server audit, custom domains/DNS/TLS, full DocTypes and tenant cache invalidation |
| Sections 10–14: packaging and roadmap | Core Frappe tools retained; phase-two features marked Coming soon | Full plan entitlement mapping, release acceptance on real infrastructure |
| Section 15: earlier commercial continuity | Previous proposals preserved as separate contract alternatives | Explicit migration/approval; never stack legacy overage and new subscription silently |
| Section 16: public role entry | Three role signup tabs and owner entry | Complete public marketing site, legal/support content and SEO |
| Sections 17–19: institute, teacher, student onboarding | Dynamic forms, verified pending-registration source | Business evidence review, backup-contact verification, real invitation lookup, 2FA setup and transactional account/workspace provisioning |
| Section 20: month-end/card/PAYG billing | Policy/pricing UI, invalid-policy checks; existing classroom gateway source | Provider tokenization, mandate/consent, usage ledger, monthly invoices, recurring charges, retries, refunds, tax, reconciliation and billing notifications |
| Section 21: student ranges/regional prices | Exact Free–Enterprise A–E quote tables and boundary tests | Trusted active-student snapshots, plan transitions and contract-aware invoices |
| Section 22: exams | Existing manual MCQ/true-false preview and native Frappe tools; new configuration UI | Full essay/matching/fill/short-answer workflows, question banks, timed/random/negative scoring, scheduling, attempts, review/release and analytics enforcement |
| Section 23: rewards/games | Existing sample monthly competition; reward switches, sticker examples, planned game catalog | Actual reward ledger/rules, teacher assignment/moderation and six playable game templates |
| Sections 24–27: owner expansion and acceptance | Owner analytics demo/control UI and this coverage record | Production services, database schema expansion and real staging acceptance; all checklist items are not yet complete |

AI tools, public marketplace, external Google/Outlook calendar sync, native mobile apps and parent portal are Coming soon in the V2 preview. Older prototype/source files remain for future work; they are not promises of active V2 functionality. SOUL remains optional product help; prohibited AI Tutor/Course Creator/Copilot/Skills Engine/personalized-path products are not introduced.

## Security and storage boundaries

Preview role switching and entitlements are intentionally synthetic and are excluded from production authorization. Browser-local owner settings and journals are not secure server records. A frontend feature gate is presentation, not backend authorization. Existing site-local membership/payment/private-resource API checks still require testing against an installed Frappe site and separate tenants.

The 15 MB assignment limit is currently a V2 configuration default; it is not connected to native assignment enforcement. Classroom documents retain their separately implemented upload policy. Unlisted video URLs do not provide DRM. External media can disappear or have usage restrictions. Only the selected background is loaded, and reduced-motion/scene-pause controls are supported.

## Local verification

40 JavaScript tests and 62 Python tests pass, with production frontend build and Python compilation. Registration/provider tests mock Frappe boundaries; no real Frappe database, SMTP delivery, payment or cross-site authorization was exercised. Browser checks cover role forms, owner rejection/wrong-code handling, config persistence/audit, task-calendar linkage, journal saving, selected video playback, fullscreen fallback and mobile/dark layouts.

Before launch, follow RELEASE_READINESS.md and complete the pending services above. Do not publish the development server as the LMS.
