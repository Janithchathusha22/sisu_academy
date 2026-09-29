# Reference LMS comparison — 28 September 2026

The reference administration site was inspected through its UI with the owner's
authorization. No records, settings, messages, payments or files were changed or
exported. No student data or reference credentials are included in this project.

This is a feature inventory, **not a claim of complete parity**. Authentication,
database migrations and integrations still require a running Frappe site for
end-to-end acceptance. The local Vite preview is a frontend, not that site.

## Consolidated navigation

| Reference capability | Sisu destination | Current implementation |
|---|---|---|
| Dashboard, student/teacher counts, revenue | Institute dashboard / separate Super Admin | Existing institute API; new owner metrics read real records. Cross-site aggregation remains outstanding. |
| Grades, subjects, classes, timetable | Classrooms / Schedule | Existing classroom categories, subjects, teacher ownership and sessions; separate reusable syllabus taxonomy remains outstanding. |
| Notes, recordings, live lessons | Classroom materials / Live studio | Existing private files, view/download policy, YouTube links and OAuth integration code. Production credentials and integration tests required. |
| Manual papers, answer uploads, marks | Learning & teaching → Papers | New draft/review/publish/archive lifecycle, MCQ, true/false, written questions, attached classroom documents, private PDF answers, marks and feedback. PDF limit is 10 MB, not reference site's 30 MB. |
| Timed MCQ exams | Papers | Server start/deadline, one attempt per student, immutable published questions, automatic objective marking. Image/audio question choices and exam leaderboards remain outstanding. |
| Premium AI Papers (new request) | Papers → AI Papers | Active server entitlement + configured OpenAI required. Structured output, rate limits, moderation, teacher-reviewed draft only. Not tested with a live API key. |
| Physical attendance | Campus desk → Attendance | Teacher-scoped register, current enrollments, status/note, pagination, CSV export. QR scanner/token workflow remains outstanding. |
| Automatic online attendance | Session join API | Idempotent authorized join event within session window. Browser player integration and per-class enable/disable setting remain outstanding. Join is not proof of viewing duration. |
| Support inbox | Campus desk → Support | Private requester/admin threads, status management and paginated lists. Notification delivery still uses deployment configuration. |
| Announcements, marketing, articles | Keep Me Update / classroom announcements | Existing announcements and expiring provider updates. Full public article/CMS editor remains outstanding. |
| Public profile / social links | Profiles & connections | Verified usernames, membership/follow requests, social links; cover/avatar upload, tagline/qualifications, site-local approved teaching teams and published classroom browsing. See PDF_CHANGES_2026_09_28.md. |
| Fee clearance, payment checks, free months | Class fees / classroom access | Existing invoices, paid/overdue state, manual override and grace. New owner-controlled classroom price + per-student recurring platform assignment. Monthly waiver register and bank-slip review parity remain outstanding. |
| Finance / teacher payouts | Wallet & payouts / Super Admin | Existing balance/ledger, approved payout methods, reservations, local/international queues, CSV export. Real bank settlement is external. |
| Course management, quizzes, assignments, certificates | Frappe Learning | Existing upstream functionality is retained. Separate course-grants and aggregate course-quiz-results reports need integration. |
| Learning games, Battle Quiz, Map Master, map exams | Future assessment extensions | Inspected reference controls; not implemented. Includes 18 game switches, 1v1/team rooms, grade scopes, system opponent and separate leaderboard. |
| Printed-material dispatch | Future operations extension | Not implemented: paid-month eligibility, dispatch batches, delivery fees and sent/received tracking. |
| Tute store / orders / inventory | Future operations extension | Not implemented. No placeholder purchase buttons or fabricated orders. |
| Seminars, expenses, staff assignment | Future operations extension | Not implemented as dedicated modules. Existing class/session/member APIs cover only part of these flows. |
| Website manager, pages, appearance, launch settings | Future website extension | Profile branding exists. Full CMS, navigation editor and launch-management parity not implemented. |
| Student feature controls / data audit | Super Admin and Frappe operator tools | Pricing/entitlements and existing audit records implemented. Reference-wide feature switchboard and complete audit UI remain outstanding. |
| Payment gateway / Zoom settings | Integrations | Existing payments.lk adapter boundary + YouTube. Zoom integration and live payment-provider acceptance remain outstanding. |

## Observed reference details

Paper controls include title, grade/subject, marks, due date, PDF, view-only,
lock/unlock, allow answers, active state, grading and leaderboard. MCQ controls
include draft/published exams, duration, question groups and up to five choices.
Browser view-only controls cannot prevent screen capture or guarantee DRM.

The reference's dispatch flow groups paid students by grade and month. Its store
has stock, price, delivery charge, cover and orders. These are distinct commerce
flows and must not be presented as completed by adding navigation labels.

## Acceptance order

1. Connect a real Frappe site; migrate all custom DocTypes and configure the
   allowlisted owner, HTTPS, email, SMS and Google sign-in.
2. Exercise Student/Teacher/Institute/Super Admin isolation with real sessions.
3. Test price revision, invoice split, payment replay and wallet reconciliation.
4. Test papers end to end, simultaneous starts/submits, uploads and cross-class
   access, plus AI draft failures using a configured provider.
5. Implement and accept the outstanding feature groups above before calling the
   result complete or production-ready.
