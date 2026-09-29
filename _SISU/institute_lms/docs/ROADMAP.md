# Delivery roadmap

## Current deliverable

Interactive Vue preview with 360 fictional learners and a custom Frappe companion app. Current checks: 36 JavaScript tests, 55 Python tests and a passing frontend build. New Study Space and Plans pages are lazy-loaded. The complete feature boundary is maintained in [Feature status](../FEATURE_STATUS.md).

## Release workstreams

| Priority | Workstream | Deliverable and release gate |
|---|---|---|
| P0 | Deployment foundation | Compatible Linux bench, pinned Frappe/LMS, installed/migrated app, backups and two-site isolation tests |
| P0 | Identity and permissions | Verified institute invitations, multi-institute teacher identity, provider memberships, revocation and server authorization for every read/write |
| P0 | Learning and access | Bridge paid classroom/course enrollment to native LMS permissions; complete academic result APIs and reviewed imports |
| P0 | Financial records | Approve commercial rules; versioned contracts, fee ledger, idempotent collection/refund reconciliation, provider-currency separation |
| P1 | Provider integrations | payments.lk sandbox acceptance, WhatsApp templates, Google channel OAuth/broadcast/chat tests and operational monitoring |
| P1 | Student subscriptions | Server-owned Study Plus/GPA plans, approved price, purchase/cancel/expiry/refund flow; keep essentials free |
| P1 | International release | Backend time zones, currencies/gateway routing, week starts, Arabic/RTL, complete translation catalogs and human language review |
| P1 | Discovery and marketing | Shared public directory, consent-aware engagement aggregation, keyword enforcement, abuse controls and campaign expiry jobs |
| P1 | Security and privacy | Independent review, upload validation, rate limits, data retention/erasure workflow, restore drill and youth-appropriate controls |
| P2 | AI Quiz | Explicit teacher entitlement, controlled generation input, teacher review, metered cost limits and evaluation; manual quiz path always available |
| P2 | Enterprise analytics | Fleet-wide aggregate reporting, contractual reports, approved currencies and data minimization |

## Study Space acceptance

Free countdown/stopwatch/break modes work without premium access. Timer time derives from timestamps so background throttling does not accumulate tick drift; a sleeping browser may delay its completion notice. Premium audio starts only from a user gesture and stops on pause, finish, page exit or expiry. The scene supports motion pause/reduced-motion preferences. The selected theme/wallpaper and recent session history are isolated by demo account. Reset discards the current unsaved session; Save and finish records elapsed focus time. Break time is not counted as study time.

For production, store subscription status and expiry on the server, revalidate entitlements, reconcile gateway events and provide clear cancel/renewal terms. Local preview activation is not proof of a payment. Audio consists of original synthesized loops; it does not fetch commercial music or use a third-party streaming account.

## Ready for release means

A feature needs working UI, authenticated backend, meaningful tests against the actual Frappe/database deployment, clear error/recovery paths, operational documentation and any required provider acceptance. A preview, a successful build or a paid-looking button alone is not a release gate.
