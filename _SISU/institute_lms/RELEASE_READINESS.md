> **27 September revision:** Normal startup now requires a real Frappe session; fictional accounts and public plan prices are retired. See [current implementation and limits](docs/OWNER_PRICING_AND_PAPERS.md) and [reference feature coverage](docs/REFERENCE_FEATURE_MAP.md). Historical preview/pricing sections below are superseded. This build is not yet production-accepted.

# Release bundle · 25 September 2026

**Latest commerce update (25 September):** [Wallet schema, APIs, workflow and launch boundaries](docs/WALLETS_AND_PAYOUTS.md) supersedes older descriptions of signup, discovery, student apps and class platform fees. The new UI is reviewable locally; live provider connections and full native onboarding remain unfinished.


**V2 update:** Read [V2 scope and remaining work](docs/V2_SCOPE.md) first. It supersedes older status descriptions for pricing, signup, Study Space and Coming soon features. Full production V2 services are not complete.

**Build complete; production deployment is not certified or completed.** This is the local preview, custom Frappe app source and compiled production frontend. It is not a standalone Windows LMS installer. Several product areas remain explicit demos; consult the feature matrix before a launch.

## Package and destination

The final copy is saved under `D:\LMS\_SISU`: the `institute_lms` source folder, `Sisu-Institute-LMS.zip`, and SHA-256 manifests. An identical ZIP is retained in the original task's outputs folder. The package excludes dependencies, Python caches, real credentials and browser-local demo data. It includes all three original commercial/product DOCX references and licensing. The downloaded upstream LMS is unchanged and is not duplicated into this extension ZIP.

Generated frontend: `institute_lms/public/portal/`; Frappe route entry: `institute_lms/www/campus.html`. A production build disables the local demo adapter and requires a real authenticated Frappe backend. Do not expose the development preview as a production service.

## Latest changes

- Light/dark toggle for all dashboard roles; cozy appearance by default, warm moonlight mode and profile accent selection; a first-use dashboard prompt opens profile setup.
- Study Space with an original illustrated desk, SOUL, countdown/stopwatch/break modes, optional synthesized music, scene pause, wallpapers and rotating gentle encouragement with pause/hide controls.
- Optional Study Plus preview with 30-day expiry, no payment or automatic renewal. Free timers and basic light/dark appearance remain available. Real student pricing is deliberately unconfigured.
- Teacher PDF, PowerPoint and Word uploads with view-only/downloadable policy, private classroom access and a paginated PDF reader with extracted page text. Office previews use a teacher-supplied PDF.
- Email verification and separate notification consent; source for dual-channel class updates and scoped Google Calendar synchronization. External calendar connection is now Coming soon under V2; the older source is preserved for later activation.
- Commercial proposals organized into provider revenue-share, institution per-active-student pricing, student add-ons and a preserved legacy 500-included/LKR-50-overage model. These are separate quote modes, never silently stacked.

## Verified locally

43 JavaScript tests and 79 Python tests pass. Frontend production build and Python compilation pass. Provider/security tests use mocked Frappe/provider boundaries; they are not real database concurrency or deployment tests. Browser review covers the latest timer/theme/verification interactions plus the workflows listed in `FEATURE_STATUS.md`. npm audit reports no known vulnerabilities at the packaging check; this does not establish overall security.

## Required before accepting real users or money

1. Install and migrate on the compatible Linux Frappe 17 development/Python 3.14 stack required by the downloaded LMS, pin commits, and run the two-site authorization/access suite. Local Python 3.12 tests do not validate that runtime.
2. Complete production services for marketplace identities, multi-provider dashboards, the new video-course editor/enrollment bridge, academic results, discovery activity and paid add-ons. These screens remain demo-only. Free Study Space is included in the production frontend, with subscriptions unavailable until a real entitlement service is connected. Profile style currently persists in the browser, not across devices.
3. Approve Study Plus/GPA prices and contract rules; To-do and Journal have requested US$1/month prices. AI Quiz is Coming soon. Implement server-owned entitlements, renewal/cancel/refund handling and gateway reconciliation. Browser demo activation must never grant a paid production entitlement.
4. Configure HTTPS, outgoing email, YouTube and WhatsApp credentials/templates. Test real delivery, authorization revocation, canceled/rescheduled events, enrollment removal, retries and account changes. Complete WhatsApp phone-ownership verification. No live message, calendar event or charge was created during this build.
5. Validate payments.lk's merchant contract and sandbox behavior, financial reconciliation and worker/database concurrency on the real stack. Add monitoring, backup/restore and incident runbooks.
6. Validate direct private-file URL denial, malware scanning/quarantine (especially legacy Office documents), site storage quotas, orphan-upload cleanup and file backup/restore. Format validation is implemented; antivirus is not.
7. Complete international backend time zones/currencies, all-language translations, accessibility and security review, age-appropriate consent and retention/erasure operations. SOUL student AI remains off until its documented review gates are satisfied.

## Deployment sequence

Follow `README.md` to install the app into a compatible bench, then `INTEGRATIONS.md` for provider configuration. Run every relevant item in `ACCEPTANCE.md` on staging, record evidence and sign off the unresolved features above before public launch. Complete the V2 pending-registration provisioning, database configuration, subscription ledger, advanced exams and game templates listed in docs/V2_SCOPE.md. Copying these files to D: does not install Frappe, configure DNS or start a production server.
