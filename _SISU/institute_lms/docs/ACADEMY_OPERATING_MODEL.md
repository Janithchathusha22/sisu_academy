# Institute programmes and independent teaching — 28 September 2026

This revision follows the user's Teen Academy examples and clarification: SISU settles institute-owned tuition to the institute. The institute compensates its teachers separately. An assigned instructor never becomes the beneficiary merely because they teach the class.

## Reference observations

The supplied Sakya guide describes subject enrollment, monthly access to lessons, live timetables, recordings, PDFs, attendance and results. The [Sakya signup portal](https://signup.sakya.edu.lk/?source=website) organizes entry by branch, subject, intake and teaching medium, with guardian details. The [Sakya dashboard](https://dash.sakya.edu.lk/auth/login) separates intakes. [Sakya AAT courses](https://aat.sakya.edu.lk/courses/) and its [online classes guide](https://aat.sakya.edu.lk/sakya-online-classes/) illustrate course/month selection and payment workflows.

These are observed product patterns, not a claim that every Sri Lankan institute uses the same model. The reference's password/SMS patterns were not copied. No Sakya student records or staff photographs were imported. All preview people and original SVG portraits are fictional.

## Ownership and fees

| Offering | Tuition | Beneficiary | Access |
| --- | --- | --- | --- |
| Teen Master Business | LKR 135,000 once | Teen Academy | One enrollment purchase and one invoice unlock all 12 module classrooms |
| Edexcel subject | LKR 8,000 per selected class/month | Teen Academy | Current month's invoice must be settled, unless an authorized override/grace applies |
| Independent mathematics | Teacher's configured monthly fee | Independent teacher | Its own enrollment and monthly invoice |

The programme contains 12 distinct classrooms, each assigned to a different teacher for two weeks; six months is the advertised overall duration. Actual start/end dates can account for breaks. Programme tuition is not duplicated into 12 separate charges. Enrolled programme structure/price is locked; new intakes should use a new programme. Monthly price changes apply to newly issued invoices only.

Platform fees remain separate, Super Admin assigned and frozen on invoices. The preview's sample invoices use zero platform fee to illustrate tuition ownership; this is not a production price assignment. Production checkout fails closed without the required student price agreement and exactly one matching enabled settlement wallet. Institution wallet selection ignores the assigned instructor. Independent wallet selection requires the immutable classroom owner user. Refund and payout mechanisms use the invoice's frozen wallet and amount split.

## People and permissions

- Teachers sign up themselves, complete verification, then request institute membership.
- Institute administrators accept or decline requests and assign approved teachers to institute classes.
- Teaching only: sessions, lesson resources, announcements and teaching workflows. No deletion, class branding/fee edits or reassignment.
- Full control: class editing, tuition edits and recoverable deletion. Only the institute administrator reassigns the teacher.
- Removal/leaving revokes institute class assignments without deleting the teacher account or personal classes. Rejoining does not silently reactivate old class assignments; the institute reassigns them.
- Users edit their own profile. Username stays immutable; name/country/account identity changes require review. Bio, qualifications and social edits preserve existing verification.
- SOUL is the platform navigation guide. Institute settings contain no OpenAI key/model configuration. Configure/test endpoints require the provisioned platform owner.

## Schema and API

New DocTypes: `IL Programme`, child `IL Programme Module`, `IL Programme Enrollment`. Programme enrollment links all included `IL Enrollment` records to one billing enrollment. Unique programme/student enrollment and per-enrollment/month invoice keys prevent duplicate requests.

Classroom additions: `owner_type`, `owner_user`, `teacher_access`, `teacher_assignment_active`, `billing_type`, `programme`. Session additions: `meeting_provider`, `meeting_url`. Invoice additions: `billing_month`, unique `billing_key`.

All URLs below are Frappe methods under `/api/method/institute_lms.`. Roles are resolved on the server; browser role selectors exist only in the DEV preview.

| Method | Purpose | Role |
| --- | --- | --- |
| `teaching.overview` | Scoped counts, fees, membership requests and programmes | Institute / teacher |
| `teaching.programmes` | List programme/module structure | Authenticated members |
| `teaching.save_programme` POST | Create a bundle from distinct institute classrooms | Institute |
| `teaching.enroll_programme` POST | Create one invoice and all module enrollments | Student |
| `teaching.month_invoice` POST | Idempotent invoice for selected class/month | Enrolled student |
| `teaching.membership` POST | Accept, reject, remove, leave | Institute / own teacher |
| `teaching.leave_class` POST | Leave institute assignment | Assigned teacher |
| `api.save_classroom` POST | Provider-owned tuition and delegated permissions | Institute / full-control teacher |
| `api.save_session` POST | YouTube, Zoom or Meet link and schedule | Assigned teacher / institute |
| `profiles.save_profile` POST | Edit own profile | Verified account identity |

Meeting URLs require HTTPS and a hostname matching the chosen provider. Public timetable endpoints do not return meeting links; classroom content is gated by enrollment/payment access. Zoom/Meet URL support is a join-link integration, not automated meeting creation or OAuth management. YouTube embedding still follows YouTube's own privacy rules.

## Preview and validation

Local preview: `http://127.0.0.1:5178/?preview=1#dashboard`.

- Institute: `institute@admin.com` / `1234`
- Teacher: `teacher@admin.com` / `1234`
- Student: `student@admin.com` / `1234`
- Owner: `superadmin@admin.com` / `1234`

320 fictional student records; 12 approved member teachers, two pending requests, 12 programme modules, three monthly institute subjects and one independent class. The new scenario stores the previous tab preview data in `sisu-preview-before-academy` before initializing. Original SVG banners/portraits have no real teacher affiliation. These credentials, role switching and records are DEV-only and absent from the production JavaScript bundle.

Validation covers ownership-based settlement, full-control/teaching-only permissions, revoked assignments, current-month access, shared programme invoices, safe meeting hostnames, duplicate preview invoice requests and programme structure. Browser verification checks the institute overview, module plan, teaching-only controls, profiles and student fee selection.

## Deployment boundary

This is source plus a compiled portal build, not a production certification. No Frappe site/database is running in this Windows preview: run `bench --site <site> migrate` and staging integration tests before deployment. Payment gateways, Google authentication, messages and real wallet transfers remain unconfigured here. The existing architecture still isolates institutes by Frappe site; a seamless cross-site teacher workspace and central directory require further orchestration. This revision does not claim complete feature parity with Teen Academy or Sakya. Monthly access currently gates the classroom using the current month's invoice; an archive browsing selector for historically paid lesson months is not yet implemented.

Verification result: 119 Python unit/boundary tests and 49 frontend tests passed. Vite production build passed. Production JavaScript was checked for the local demo credentials and scenario identifiers; none were present. No real database or gateway was exercised.
