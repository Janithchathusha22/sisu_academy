# Integration and operations notes

No provider credentials were entered during this build. The following describes implemented adapter source, not a verified live deployment. Feature boundaries are listed in [FEATURE_STATUS.md](FEATURE_STATUS.md).

## Supabase reporting database (optional)

The backend includes a disabled-by-default, server-only reporting sync for a private Supabase PostgreSQL schema. MariaDB/Frappe remains authoritative. The job copies only a minimal institute/member summary and excludes personal, contact, payment, consent and token fields. It uses a dedicated database role, deny-by-default RLS and timestamp-protected upserts; it never uses a browser key.

No connection has been made to the real Supabase project because previously disclosed credentials must first be rotated. Follow [docs/SUPABASE_REPORTING_SETUP.md](docs/SUPABASE_REPORTING_SETUP.md) after creating a fresh restricted database credential. Do not expose the `reporting` schema through the Supabase Data API.

## payments.lk (default student-invoice adapter)

Protected per-site configuration:

```json
{
  "il_payment_provider": "payments_lk",
  "il_payments_lk_secret_key": "sk_test_REPLACE_ON_SERVER",
  "il_payments_lk_webhook_secret": "whsec_REPLACE_ON_SERVER",
  "il_payments_lk_mode": "test"
}
```

Use your own sandbox merchant values, an HTTPS site URL and this POST webhook:

`https://YOUR-INSTITUTE-HOST/api/method/institute_lms.payments_lk.notify`

The server creates hosted checkouts using exact integer LKR cents and an invoice reference. It persists the request/idempotency key before the external call. Ambiguous attempts remain recorded; after 23 hours they require reconciliation rather than automatic recreation. The adapter verifies raw-body `Payments-Signature` HMAC, a five-minute timestamp window, mode, currency, amount, invoice and checkout identity. Settlement uses an invoice row lock. A browser success redirect cannot mark an invoice paid. Keep Frappe CSRF protection on browser mutations and test the session-free provider callback through your actual reverse proxy.

This adapter is LKR-only and supports one full payment for each installment invoice. It does not implement automatic recurring debits, refunds, disputes, fleet billing collection, exchange rates or international gateways. Do not route the preview's AED/GBP catalog prices to this LKR adapter. Test mode, cancellation, forged/replayed/concurrent callbacks and reconciliation must pass before switching the merchant configuration to live.

Reference: [payments.lk API documentation](https://payments.lk/developers/api).

## SOUL / OpenAI

SOUL's animated character, drag position and prepared navigation help work without a key. It does not read student grades, balances, private records, camera, emotions or other applications. The local preview never sends OpenAI requests and disables the API-key field.

On a deployed HTTPS Frappe site, migrate the app, sign in as the institute Admin and open **Settings → SOUL**. Paste a project-scoped OpenAI API key in the password field, choose a model your project can use, save and explicitly test the connection. The default identifier is `gpt-4.1-mini`; availability and project limits must be checked in your account. Testing can incur a small provider charge. Removing the key deletes its encrypted password value and disables chat. No key is stored in browser local storage, returned by status APIs or embedded in the build.

Keys are per-site in the `IL SOUL Settings` Single DocType's Frappe Password field. Keep Frappe's encryption key and backups protected. Do not log HTTP request bodies/authorization headers at proxies or application instrumentation. Ordinary teacher/student roles cannot configure credentials; trusted System Managers still have operator powers.

The server authenticates membership, requires the user-facing transmission notice, bounds message/history length, moderates input, calls the fixed OpenAI Responses endpoint with `store:false`, then moderates output. Failed moderation blocks the reply. No function tools or private record retrieval are enabled. Vue renders replies as text. Limits are six messages per minute and 50 per UTC day per user, plus 500 per day per site; failed calls still count. These are request limits, not exact monetary budgets. Set provider-side project budgets/alerts and monitor usage.

Chat history stays in browser memory and clears on reload/account switch. Only the typed messages, recent chat, authenticated role, language and coarse page name go to OpenAI; students can still type personal information, so product notices and deployment safeguards remain necessary. `store:false` does **not** establish Zero Data Retention. Review OpenAI data handling and youth requirements for the actual audience.

Student AI is disabled by default. An operator must verify appropriate age/consent controls and data handling, then set both protected flags `il_soul_student_ai_reviewed` and `il_soul_zdr_verified`, and explicitly enable `soul_ai_enabled` on each permitted member. These flags record an operator's completed review; they do not provision ZDR or obtain consent. Prepared guide help remains available when AI is disabled. This implementation intentionally requires verified ZDR for all student AI accounts; it must not be bypassed merely to make a preview button work.

SOUL is an LMS navigation helper. AI Tutor, AI Course Creator, Instructor Copilot, Skills Engine and Personalized Learning Paths are not included. The separately requested paid AI Quiz demo has no AI provider or purchase integration yet.

References: [OpenAI under-18 API guidance](https://developers.openai.com/api/docs/guides/safety-checks/under-18-api-guidance), [moderation](https://developers.openai.com/api/docs/guides/moderation), [Responses/text generation](https://developers.openai.com/api/docs/guides/text).

## PayHere (optional)

Set `il_payment_provider` to `payhere` only when selecting this adapter instead of payments.lk.

Server configuration keys:

```json
{
  "il_payhere_merchant_id": "YOUR_MERCHANT_ID",
  "il_payhere_secret": "YOUR_DOMAIN_MERCHANT_SECRET",
  "il_payhere_sandbox": true
}
```

Keep values in the site's protected configuration. Register the exact HTTPS domain with PayHere. The notify endpoint is:

`https://YOUR-INSTITUTE-HOST/api/method/institute_lms.payments.notify`

PayHere callbacks are unauthenticated server-to-server requests carrying a provider checksum. Preserve Frappe's CSRF protection for all browser mutations. Verify the callback on the deployed Frappe version without globally disabling CSRF; configure the reverse proxy so callback requests are not injected with session cookies.

Checkout uses server-generated hashes; the browser never receives the merchant secret. The redirect back from PayHere is not proof of payment. A verified callback must arrive before an invoice settles and access changes. Replayed success callbacks return success without adding another settlement; late unsuccessful callbacks cannot undo a settled invoice. Refunds, disputes, manual reconciliation and unexpected duplicate charges require operator handling in this first release.

Invoice currency is LKR. An installment is a separate invoice, paid in full. Partial payments within one installment are not supported. Automatically recurring card debits are not implemented. Monthly institute bills are recorded for manual collection; they are not automatically debited through the student PayHere merchant account.

Reference: [PayHere Checkout API](https://support.payhere.lk/api-&-mobile-sdk/checkout-api).

## WhatsApp Cloud API

```json
{
  "il_whatsapp_phone_id": "YOUR_PHONE_NUMBER_ID",
  "il_whatsapp_token": "YOUR_SERVER_SIDE_TOKEN",
  "il_whatsapp_graph_version": "YOUR_SUPPORTED_GRAPH_VERSION",
  "il_whatsapp_templates": {
    "en": {"name": "YOUR_APPROVED_TEMPLATE", "language": "en_US"},
    "si": {"name": "YOUR_APPROVED_TEMPLATE", "language": "YOUR_APPROVED_LANGUAGE_CODE"},
    "ta": {"name": "YOUR_APPROVED_TEMPLATE", "language": "YOUR_APPROVED_LANGUAGE_CODE"}
  }
}
```

Choose a supported Graph API version at deployment. Each configured approved template must accept one body text parameter. Confirm language availability and template approval in your Meta account; do not assume a locale code is accepted simply because portal content supports that language. Students opt in themselves through Settings. Their current consent and active membership are checked again before sending.

The worker runs every five minutes, in batches of 20. No configuration means notifications remain Queued. Missing consent means Skipped. Provider HTTP success means Accepted, not delivered. Rate limiting backs off with a bounded retry count. Ambiguous network results or worker interruptions remain Review, requiring reconciliation before resending. The first release does not ingest delivery/read webhooks.

Monitor `IL Notification` in Desk as a System Manager. Configure worker/scheduler monitoring and retention for old notification records. A sustained workload beyond 20 requests per five minutes requires tuning batch size/schedule within Meta rate limits, and testing provider latency before increasing concurrency.

References: [Meta Cloud API examples](https://github.com/fbsamples/whatsapp-api-examples), [Meta's Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).

## YouTube

```json
{
  "il_youtube_client_id": "YOUR_GOOGLE_OAUTH_CLIENT_ID",
  "il_youtube_client_secret": "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
}
```

Enable the YouTube Data API for your Google project. Register:

`https://YOUR-INSTITUTE-HOST/api/method/institute_lms.youtube.callback`

Teachers connect their own Google account in Settings. OAuth state is random, user-bound, expires after ten minutes and is consumed once. Refresh tokens are stored in a Frappe Password field, never sent to students. Google may require consent-screen verification for production use of the requested scope. Testing-mode token lifetimes and channel live eligibility must be checked in your project.

Create a session in the LMS, then choose **Create YouTube Live**. Use YouTube Studio to bind/start the encoder stream. The portal can synchronize the broadcast schedule and request live/complete transitions once YouTube allows those transitions. It does not capture or relay the teacher's camera feed, issue stream keys, or replace OBS/YouTube Studio. If a creation request times out ambiguously, check YouTube Studio for the broadcast and attach its URL before retrying to avoid duplicates.

Unlisted videos are accessible to anyone who receives the link. They do not provide DRM. Private videos require a Google account that the channel has invited; an LMS membership/payment cannot override YouTube's restrictions. Embedded playback may require opening YouTube directly to authenticate, and some channels/videos disallow embedding. Students are informed of these constraints in the classroom. For strict content protection, use a separate signed-stream provider rather than treating unlisted YouTube URLs as secure video storage.

References: [YouTube broadcast creation](https://developers.google.com/youtube/v3/live/docs/liveBroadcasts/insert), [broadcast lifecycle](https://developers.google.com/youtube/v3/live/life-of-a-broadcast), [broadcast transitions](https://developers.google.com/youtube/v3/live/docs/liveBroadcasts/transition).

Teachers can read live comments through the LMS's live-chat adapter, scoped to the teacher's own classroom. The server respects YouTube's polling interval, keeps at most 200 recent messages in short-lived cache, and does not write chat messages to the database. The local preview displays synthetic comments only. Actual chat availability depends on the broadcast and YouTube restrictions; the adapter does not add chat to broadcasts where YouTube disables it. Reference: [liveChatMessages.list](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list).

## Results, accounts and international operation

Bulk results are currently parsed in-browser and saved only in the local demo. Production requires role-scoped result/import DocTypes and APIs, transactionally validated enrollment, an audit/version history and institute-approved grading rules. Do not deploy the demo grade store for real student records.

Account deletion buttons submit review requests. They do not erase all student records, backups or an institute database. Build and approve the applicable retention/erasure workflow before exposing a claim of permanent deletion. Removing a teacher's affiliation must preserve their independent workspace and other institute memberships; cross-site removal is still a demo. Password reset uses Frappe's existing email flow after email delivery is configured.

The marketplace preview includes Middle East countries, separate curricula, IANA time zones, currencies, Arabic and RTL layout. Existing native scheduling and invoice rules remain Sri Lanka-oriented. Before international launch, make the site time zone, week start, date rendering, due-date boundaries and currency/gateway selection consistent across backend APIs, jobs, notifications and reports. Region selection alone does not localize those services. Translations currently cover core navigation with English fallback; full form/help/error translation needs human review.

## Storage, access and performance

- A Frappe site/database and its private files belong to one institute. Provision separate object-store prefixes/buckets and credentials if using external private storage.
- Branding and news images are public promotional content, compressed to WebP by the browser, at most 1600 pixels on the longest side. Input files must be PNG/JPEG/WebP, at most 2 MB. Images remain filesystem/object-store files, not database blobs.
- Lesson material entries store HTTPS URLs and metadata. Resource URLs must use the provider's own authorization if they contain confidential content; knowing an external URL may bypass portal gating if the provider serves it publicly.
- Videos store YouTube IDs, titles and schedule metadata only. Video binaries never enter this app's database.
- Authenticated portal responses are not public-cacheable. Cache versioned static assets at the proxy/CDN. Each site's database/cache namespace stays separate.
- Paginate list APIs and export only the loaded invoices from the current UI. Add background report exports for institute-wide historical exports larger than interactive lists.
- Fonts use Google Fonts with system fallbacks, including Gemunu Libre for creative Sinhala headings and readable Noto fallbacks. For offline/private deployments, self-host the selected licensed font files and replace the CSS import. Verify readability of mixed scripts on target devices. Small flag SVGs are served locally with their license.
- Active students are distinct `IL Member` Student records with `active=1`. This definition is explicit; it is not a 30-day-login metric. Monthly bills are immutable usage snapshots by convention; restrict Desk access to trusted operators.

Reference: [Frappe hooks and extensions](https://docs.frappe.io/framework/user/en/python-api/hooks).

## Verified schedule email and Google Calendar

Configure a working outgoing Frappe Email Account and HTTPS first. Settings → Email & calendar connection uses a six-digit code that expires after 10 minutes; only its member/email-bound HMAC is cached. Requests are limited to one per minute and five per hour per member; five incorrect attempts exhaust a code. Verification changes a notification contact only, never the login email. Class-email opt-in is separate and starts disabled. Changing a verified contact disconnects the previous calendar.

Class schedules/changes, materials, announcements and successful invoice settlement create separate WhatsApp/email outbox records for enrolled recipients. The email worker rechecks verified contact, active membership and consent before adding mail to Frappe Email Queue. Accepted means queued for email sending, or accepted by WhatsApp; it does not claim delivery. Configure and monitor Frappe Email Queue delivery/bounces. WhatsApp requires approved templates and separate opt-in; phone ownership is not yet OTP-verified.

Enable Google Calendar API and configure a web OAuth client. Keep `il_calendar_client_id` and `il_calendar_client_secret` in protected server configuration. Register this exact HTTPS redirect for the institute host:

`https://YOUR-INSTITUTE-HOST/api/method/institute_lms.calendar_sync.callback`

The student verifies the Google account email and explicitly consents. Requested scopes are `openid email` and `https://www.googleapis.com/auth/calendar.app.created`. Sisu creates a separate secondary calendar rather than requesting access to all calendars. OAuth state is single-use, session/member/site/email-bound and expires after 10 minutes; PKCE is used. Google account verification must match the verified contact. Refresh tokens use Frappe Password encryption. Complete Google's consent-screen publication/verification requirements for your deployment.

Five-minute background jobs synchronize enrolled class times, title, venue and a portal link, without media URLs, grades, payment amounts or an attendee roster. Stable event IDs allow an uncertain insert to be retried and updated instead of duplicated. Cancellations/removals delete the copied event. Calendar creation uncertainty enters Review because blind creation retries could create duplicates. Operators must reconcile that record before reconnecting. Worker retries are bounded and failures enter Review.

Disconnect deletes the locally stored refresh token and stops future sync. Existing copied events remain in the student's Google Calendar; disconnect does not revoke the entire Google account grant. Students can remove the Sisu calendar and revoke the app separately in Google Account settings. Outlook/Apple synchronization is not implemented. Test reconnect, revoked tokens, canceled/restored sessions and enrollment removal on staging before enabling this connector.

Source references: [Google Calendar scopes](https://developers.google.com/workspace/calendar/api/auth), [Google server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server), [Calendar event contract](https://developers.google.com/workspace/calendar/api/v3/reference/events), [Frappe encrypted passwords](https://github.com/frappe/frappe/blob/develop/frappe/utils/password.py), [Frappe email queue](https://github.com/frappe/frappe/blob/develop/frappe/email/doctype/email_queue/email_queue.py).

## Classroom documents

Teachers open a classroom, choose **Add material**, select **Document**, and upload PDF, PPT/PPTX or DOC/DOCX (10 MB maximum). **View only** is the default. PowerPoint/Word view-only materials require a matching PDF exported by the teacher; Sisu does not send private files to Microsoft or Google viewer services. Downloadable Office files may omit the PDF preview. The reader provides page navigation and selectable extracted page text; scanned documents still require an accessible teacher-provided text version.

Production stores files in private site storage and only file references/metadata in DocTypes. Each view/download checks active classroom membership, current payment/access policy and the material's institute. Student download requests fail closed unless explicitly Downloadable. Classroom managers may download originals. View-only is an interface/access policy, not DRM: browsers receive PDF bytes and visible content can be copied or captured.

File validation restricts names, types, sizes and expanded OOXML complexity and rejects OOXML macros/encryption/path traversal. It is not antivirus; legacy Office signatures cannot establish the absence of macros. Before launch, add malware scanning/quarantine, reverse-proxy body limits, site storage quotas, private-file backup/restore and abandoned-upload cleanup. Verify both API routes and direct `/private/files/` access under the actual Frappe proxy and permission setup; never expose this directory as an unrestricted static path. Preview files should be reviewed against the original by the teacher. Demo documents persist only in this browser's IndexedDB.


## V2 registration and sole owner

See `scripts/registration-config.example.json`. The designated owner is `danusgalagoda@gmail.com`; both activation flags ship false. This file is documentation, not an automatically applied site configuration. No email has been sent to this address during preview work.

Native requests require HTTPS, an encryption key, outgoing Frappe Email Account and the explicit `il_registration_enabled` site flag. Never copy the preview code 123456 into production configuration. Production codes use secure randomness, HMAC, cache expiry, rate limits and bounded attempts. `IL Registration Request` stores verified pending requests only; it does not create users or assign privileges.

Before activation the operator must verify invitations and business evidence, verify institute recovery contacts, configure native Frappe login/2FA and provision accounts through a reviewed workflow. Restrict any future owner APIs using the configured email AND authenticated identity; the `il_owner_provisioned` flag alone is not authentication or 2FA. The fleet-wide owner control/analytics screens remain demo-only. Review request retention, abuse protection and actual mail delivery on staging before enabling public registration.

V2 external Google/Outlook calendar sync and AI products are Coming soon. Earlier integration source is retained, not activated by this release. LMS calendar dates and optional task ICS export do not link an external calendar account.
