# Local interface preview

Run `npm install` and `npm run dev -- --port 5178` from `frontend`, then open
http://127.0.0.1:5178/?preview=1.

| Workspace | Preview email | Password |
|---|---|---|
| Student | student@admin.com | 1234 |
| Teacher | teacher@admin.com | 1234 |
| Institute Admin | institute@admin.com | 1234 |
| Super Admin | superadmin@admin.com | 1234 |

These are local interface selectors, not real accounts or security credentials.
They are available only on loopback hosts under the Vite development server.
The preview login, adapter and role switcher are excluded from production builds.
Real sign-in continues to use Frappe sessions and server-side permissions.

Use **View as** to change role and **Open screen** to explore implemented screens.
The Super Admin workspace has its own Overview, Pricing, Verification and Payouts
navigation. Records start empty. Locally created classes, sessions, papers,
profiles, price assignments and support tickets persist in this tab's session
storage. No old synthetic enrollment dataset or fixed public prices are restored.
Study Space is unlocked for visual preview only.

The preview does not send email/WhatsApp messages, upload files, generate AI papers,
settle payouts or charge cards. Those operations require the connected Frappe site
and its configured providers. External media can still load from its media host.
See REFERENCE_FEATURE_MAP.md for the incomplete reference feature groups.

Validation: frontend production build; 45 frontend tests including the local paper
lifecycle and owner-only preview price assignment; manual browser checks of four
roles, Papers, Super Admin pricing, and Study Space. This does not replace real
Frappe migration, authorization or integration acceptance testing.

## Classroom deletion
Classroom details now include Delete classroom for managers. Type the exact title to confirm. This is recoverable removal using the existing active field: student access and active schedules are hidden, while linked financial and learning records remain. My classrooms > Deleted classrooms provides paginated restore controls. Restoring reinstates saved schedules/access rules; deletion does not issue refunds or cancel external broadcasts. The POST API set_classroom_deleted enforces institute and teacher ownership and records a Frappe timeline comment. No schema migration is required for this feature.
Validated with 100 backend tests, 46 frontend tests, a production build, and a browser delete/restore round-trip using a disposable local classroom. Real Frappe integration acceptance is still required.
