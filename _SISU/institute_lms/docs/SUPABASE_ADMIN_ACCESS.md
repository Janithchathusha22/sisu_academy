# Connected administrator access

The connected app uses the normal login URL (`http://127.0.0.1:5178/`) and
existing Supabase Auth email/password credentials. The Admin selector only
highlights the form; it never sets a role. `?preview=1` and its sample password
are browser-only and do not access Supabase.

## Initial project owner (trusted one-time setup)

Only a person who controls this Supabase project should run this in its SQL
Editor or an equivalent trusted PostgreSQL session. Do not place this SQL in the
frontend, expose a service key, insert into `auth.users` manually, or rerun the
original CREATE TABLE migrations. Use a strong, unique password.

1. Register the intended owner through the connected app's normal signup, or
   create the user with the Supabase Auth dashboard. Confirm the email, then
   sign in once so the existing onboarding trigger/recovery can create a profile.
2. Check the identity and profile with this read-only query. Replace the email;
   inspect the returned UUID and status before any grant:

   ```sql
   select u.id, u.email, u.email_confirmed_at, p.profile_kind, p.status,
          pr.role, pr.active
   from auth.users u
   left join public.profiles p on p.id = u.id
   left join public.platform_roles pr on pr.user_id = u.id
   where lower(u.email) = lower('OWNER_EMAIL_HERE');
   ```

3. Only if this is the correct, email-confirmed owner with a `verified` profile,
   grant the existing platform role. This refuses missing, unconfirmed, pending,
   rejected, and suspended identities. Replace the email in this block too:

   ```sql
   do $$
   declare owner_id uuid;
   begin
     select u.id into owner_id
     from auth.users u
     join public.profiles p on p.id = u.id
     where lower(u.email) = lower('OWNER_EMAIL_HERE')
       and u.email_confirmed_at is not null
       and p.status = 'verified';
     if owner_id is null then
       raise exception 'Confirmed owner with verified profile not found';
     end if;
     insert into public.platform_roles (user_id, role, active)
     values (owner_id, 'super_admin', true)
     on conflict (user_id, role) do nothing;
   end $$;
   ```

   Run the read-only query again and verify `super_admin` is active. If an
   existing row is inactive, investigate why it was revoked; do not silently
   reactivate it. If the intended owner's profile is pending, resolve that
   separately through a trusted review of the recovered data rather than
   changing status based on Auth metadata.

4. Sign out and sign in at the normal URL with that owner's Supabase credentials.
   `/api/me` should report `role: "super_admin"` and the connected dashboard
   should show **People & approvals**. No default live admin password is shipped.

## Institute administrator

The intended owner signs up as **Institute** and confirms their email. This
creates a pending application, not immediate access. A platform Super Admin
creates or selects the institution, then approves the application in **People &
approvals**. The existing `review_application` RPC verifies the reviewer and
creates an active `institution_memberships` row with role `institute_admin`;
it also verifies the profile. After signing in again, `/api/me` routes that
user to **Institute management**. A Student/Teacher/Admin login-page choice,
user metadata, or an unapproved membership cannot grant this role.

Access to another institution requires its own authorized membership; the
backend and RLS both check the institution on protected operations.
