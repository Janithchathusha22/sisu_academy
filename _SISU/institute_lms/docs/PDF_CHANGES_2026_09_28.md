# PDF revision: profiles, signup and Study Room

## Implemented source and preview changes

- The signup introduction asks learner or teacher, then independent teacher or institute.
- Student signup uses the configured Google OAuth provider. A server session marker and login hook reject password-based student access; selecting a frontend tile grants no permissions.
- Providers apply manually, verify email, receive owner review, then set their password, verify their phone, and submit their profile. Owner profile verification issues a code and activates the approved role. Institute administration requires an explicit workspace record ID.
- Super Admin → Signup & privacy has an initially empty published-policy URL and version. Provider applications remain disabled until these are supplied and enabled. Signup shows a reserved-policy notice, not a fictional agreement. No policy text or URL was invented.
- Applications retain accepted policy URL/version and consent timestamp. Verification rechecks the policy before accepting a pending request.
- Profile banners/avatars, tagline, qualifications and HTTPS social links appear with verified name/username/code. Institute profiles show approved teachers; teacher profiles list published classrooms with timetable summaries and free/paid labels.
- Teacher/admin classroom editing now controls directory publication. Students can enroll themselves from the catalogue; payment-gated access remains separate from following or membership. Enrollment requests lock the student record to avoid double creation.
- Free class means zero teaching fee; an explicitly assigned platform fee can still apply. Existing invoices are not rewritten by editing a classroom.
- Apps and Plans navigation aliases lead to Study Room. The public Apps catalogue is removed from the active portal; Study Room has its own assigned-price checkout quote. No new public price or fake trial was introduced.

## Required deployment acceptance

Run bench migrate on a backed-up staging site. New schema includes IL Portal Settings plus profile workspace/tagline/qualifications, classroom publication/timetable/fee mode, and application review fields. Configure Google Social Login Key, SMTP, SMS, the existing registration switch and owner allowlist before enabling applications. Existing student sessions must sign in again with Google after this update.

The local preview deliberately does not send verification codes, create real accounts, take payments or upload profile files. It has an explicit Preview signup button and owner settings interaction. Test data is not seeded into the running portal.

Real Frappe migrations, OAuth callback persistence, email/password setup, phone verification, transactions and cross-role authorization still require integration acceptance. The current architecture is one institute per Frappe site; the directory is site-local. A trusted cross-site directory bridge is outstanding. Classroom settlement currently uses institute LKR wallets; international/independent class checkout needs further integration. Subscription quotes are available but live payment activation remains unconfigured.

## Reference comparison

Teen Academy's authenticated navigation was rechecked read-only on 28 September. The complete outstanding inventory is in REFERENCE_FEATURE_MAP.md. This revision does not implement all reference modules: games/maps, store/inventory/dispatch, CMS, seminars/expenses/staff and several reporting/integration workflows remain outstanding. No claim of full parity or production readiness is made.

## Validation recorded

110 Python rule/service-boundary tests and 47 frontend tests passed. Python compilation, DocType JSON validation and the production asset build passed. Browser checks covered blank owner policy settings, saved-setting feedback, learner/provider/institute signup choices, disabled consent submission without policy, student Study Room navigation and teacher classroom publication controls. No real Frappe database or external integration pass is claimed.
