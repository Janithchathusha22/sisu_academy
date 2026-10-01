> **1 October migration update:** The active portal entry uses Supabase Auth and a FastAPI cookie session for the new core courses/attendance workspace. The detailed feature table below describes the retained preview/Frappe implementation; those remaining modules are not yet Supabase-native. This build is not production-accepted until live database and RLS verification passes.

# Feature status · 25 September 2026

**Latest commerce update (25 September):** [Wallet schema, APIs, workflow and launch boundaries](docs/WALLETS_AND_PAYOUTS.md) supersedes older descriptions of signup, discovery, student apps and class platform fees. The new UI is reviewable locally; live provider connections and full native onboarding remain unfinished.


**V2 update:** Read [V2 scope and remaining work](docs/V2_SCOPE.md) first. It supersedes older status descriptions for pricing, signup, Study Space and Coming soon features. Full production V2 services are not complete.

This is a local interactive preview plus custom Frappe app source. The downloaded upstream LMS remains unchanged. The Frappe extension has not been installed on a running site in this environment. A production build uses Frappe APIs; it never silently substitutes demo records.

## What can be reviewed now

| Feature | Local preview | Production boundary |
|---|---|---|
| Role dashboards | Institute Admin, Teacher, Student, Platform Owner; 360 synthetic students | Core institute APIs implemented; fleet-wide owner analytics need an authenticated aggregate service |
| Classrooms and scheduling | Sessions, materials, feedback, exams, creative Sinhala title fonts | Custom DocTypes/APIs implemented; real-site acceptance pending |
| Classroom documents | Teacher PDF/PPT/PPTX/DOC/DOCX upload; view-only or downloadable; paginated PDF and matching Office preview | Private local-file APIs with class/payment/policy checks implemented; actual Frappe private-file route, malware scanning and storage operations require staging review. No DRM guarantee |
| Payments and access | Full/installment invoices, simulated settlement, grace/overrides | payments.lk and optional PayHere adapters implemented; credentials, webhook and concurrent database tests pending |
| YouTube | Embedded recordings, teacher teasers, course videos; synthetic live chat | Google OAuth/live broadcast and read-only live-chat source implemented; requires teacher channel and API setup. Camera/encoder remains in Studio/OBS |
| Online video courses | Teacher/admin authoring, 1–30 lessons grouped into modules, free or paid enrollment, outline, progress, quizzes | New editor is demo-only. Native Frappe LMS courses remain linked in Learning hub. Native-course payment/enrollment bridge not completed |
| International workspace | Country and curriculum separately selected; currencies/time zones; Middle East presets; UAE example | Existing custom backend is still LKR/Asia-Colombo oriented. Full international scheduling, gateway routing and billing need backend implementation |
| Discovery | Search username/name/subject; interest suggestions and Most active sort; provider/class enrollment | Browser demo only. A directory/identity service and signed cross-site membership exchange are required |
| Teacher affiliations | Independent classes plus multiple institutes; invitation leads to Pending then admin verification; removal/leave | Cross-site verification/invitation service is not implemented. Site-local member/class removal APIs are implemented |
| Student home | All-providers view plus provider filters; distinct class/payment labels | Cross-site aggregation is demonstrated, not connected to separate live Frappe sites |
| Teacher promotion | Public details, teaser, social links, 5 keywords; institute profiles allow 15 | Marketplace profiles/campaigns and lead tracking are demo-only; classroom branding/news APIs are implemented |
| News retention | News/promotions disappear after 30 days from creation; edits do not reset age | News scheduled deletion implemented. Campaign deletion is local-demo only; shared image files are not automatically erased. Leads are retained separately |
| Bulk results | XLSX, CSV, selectable-text PDF; validation, review, atomic local publish | Academic results storage/import APIs are not implemented on Frappe. No source file is sent to AI. Scanned PDFs need external OCR/template conversion |
| GPA calculator | Optional simulated student purchase; credits/grade what-if tool; published results free | No real purchase. Uses illustrative 4.0 scale; approved institute/HND grading, repeats and classification rules still needed |
| AI Quiz | Optional simulated teacher purchase, lesson completion triggers illustrative quiz; manual MCQ/true-false remain free | No AI quiz provider, transcript processing or paid entitlement service connected. SOUL is a separate feature |
| Study Space & cozy appearance | Light/dark header toggle for every role; cozy daylight default, warm moonlight, student profile colors; countdown, stopwatch, breaks, original soundscapes, wallpapers and gentle quotes | Free Study Space is included in the production frontend; live-site acceptance pending. Study Plus activation is demo-only. Appearance is browser-local. Server subscription purchase/cancel/refund/expiry and profile synchronization remain to be implemented |
| Email & class calendar | Email code, separate opt-in, Google consent/disconnect simulation | Verified email outbox and Google secondary-calendar OAuth/sync source implemented; real Frappe SMTP/OAuth/provider checks pending. No Outlook/Apple sync or WhatsApp phone-ownership verification yet |
| Pricing & plans | Source documents reconciled; student add-on cards and separate provider/school/legacy calculators | Quote previews only; no approved student price, recurring collection or new fee ledger |
| SOUL | Animated sprout mascot, click-to-chat, drag, keyboard move, contextual help, pause/hide/reduced motion | Server-side OpenAI adapter exists; requires HTTPS Frappe deployment, key, model access and release review. Preview answers are prepared guide text |
| Language and flags | 40 searchable locales, regional flags, Unicode content, core navigation translations, RTL, custom locale tags | Full UI translation and linguistic review remain. Missing strings use English. Country flags indicate the offered locale variant, not exclusive ownership of a language |
| Account controls | Verification/removal flows; deletion requests with reasons/confirmation; password-reset guidance | Membership removal and deletion-request source implemented. Permanent erasure, retention policy execution and fleet deletion are not implemented. Email reset needs configured Frappe email |

## Discovery scoring

Suggested ranking combines 40% interest keyword overlap, 20% related joined-class subjects and 40% logarithmic recent activity. Without interests, activity and joined-class relevance still contribute. Most active sorts the activity count directly. Counts shown are synthetic active **class memberships**, not unique people or real measured engagement. Production needs server-side, consent-aware events, deduplication, bot/fraud controls and clear reporting windows before these figures can influence real placement. This is a rules-based directory ranking, not personalized learning paths.

Keywords are Unicode-normalized, trimmed and deduplicated. Each keyword allows 40 characters; teacher profiles allow 5, institutes 15, and student interests 20. Class subject/level and provider keywords participate in search/relevance.

## Result-import limits

Use columns `Student ID, Grade, Credits`. XLSX reads the first sheet; formula calculations are not performed. Up to 1,000 rows, 30 columns, 5 MB input and 30 MB expanded workbook content. PDFs must have selectable text, at most 20 pages, and rows in the same strict order. Unknown student IDs, unenrolled students, duplicate rows, unknown grades and invalid credits block publication. Replacing existing course/term results requires an explicit checkbox. Review every extracted row against the source before publishing.

## Verification

36 JavaScript tests and 55 Python tests cover domain, authorization/provider contracts and a demo workflow spanning invitation review, bulk result validation, course enrollment, completion and notification routing. These are local tests; provider calls are mocked and database isolation is not integration-tested.

Latest document checks: teacher PDF/PPTX/DOCX uploads; missing Office PDF rejected; student PDF/PowerPoint preview pagination and extracted text; view-only controls; downloaded Word bytes match the uploaded SHA-256; 390 px layout without horizontal overflow. Admin dark theme and student light/dark controls reviewed.

Latest browser checks: Study Plus preview activation; profile moonlight/Sage save; custom one-minute timer completion and automatic music-control stop; quote pause; wrong/correct email codes; separate email opt-in; simulated calendar connect/disconnect. No real email, Google connection or subscription charge was made.

Browser checks include creating a free sample video course, student enrollment, embedded playback of `YSul9yrAvN4`, saving lesson completion; XLSX import and bulk publishing; text-PDF extraction of two valid rows; changing interests and seeing matching providers move up; SOUL guide replies, click/drag/keyboard positioning; Arabic RTL and SOUL layout at 390-pixel width; language picker search/flags. The supplied video is a stock classroom clip, clearly labeled as playback demonstration rather than course content.

Frontend production build passes. npm dependency audit reports zero known vulnerabilities at the final local check. These checks do not establish production readiness or replace an independent security/accessibility review.

## Next production milestones

1. Start the compatible Linux Frappe bench, pin app versions, install/migrate this extension, and execute the two-site acceptance suite.
2. Implement the shared public directory and identity/membership service without weakening each institute site's data isolation. Do not share raw Frappe sessions across unrelated hosts.
3. Implement server-owned results, discovery events, multi-provider enrollments and add-on entitlements; bridge paid courses to native LMS permissions and revoke all relevant access on removal.
4. Connect gateway sandboxes, WhatsApp templates and test Google channels. Add reconciliation, refunds/disputes, worker monitoring and operational runbooks.
5. Finish international dates/currencies and translation catalogs; complete human language, accessibility and age-appropriate product review.
6. Review retention/erasure, consent, backup restore, rate limiting, malicious uploads, concurrency and cross-tenant authorization on the actual deployment. SOUL student AI stays off until the documented controls are verified.

See [INTEGRATIONS.md](INTEGRATIONS.md), [ACCEPTANCE.md](ACCEPTANCE.md), and [RESEARCH.md](RESEARCH.md).
