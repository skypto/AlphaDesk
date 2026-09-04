# Hosted Supabase Free authentication setup

AlphaDesk uses hosted Supabase Free only for identity. Trading records and encrypted BYOK credentials stay in the AlphaDesk PostgreSQL database.

1. Create a Supabase Free project and enable email/password authentication.
2. In Authentication settings, disable **Allow new users to sign up**. AlphaDesk creates users
   only after its API validates an invitation code.
3. In Authentication URL Configuration, add local redirects for `http://localhost:3000/**` and the final HTTPS hostname.
4. Copy the project URL and publishable key into `.env.local` as `SUPABASE_URL`,
   `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
5. Create a modern Secret key (`sb_secret_...`) in Project Settings > API Keys and store it as
   `SUPABASE_SECRET_KEY`. It is used only by FastAPI for Auth administration. Never use a legacy
   service-role key in a `NEXT_PUBLIC_*` variable.
6. Keep `SUPABASE_JWT_AUDIENCE=authenticated` unless the project uses a custom audience.
7. Set `ALPHADESK_ADMIN_EMAILS` to a comma-separated protected list of administrator emails.
8. Since public signup is disabled, create each bootstrap administrator through Authentication >
   Users > Add user. The address must match `ALPHADESK_ADMIN_EMAILS`.
9. Rebuild the web image after changing any `NEXT_PUBLIC_*` value because Next.js embeds public variables at build time.

## Bootstrap administrator workspace

A Dashboard-created administrator initially has platform administration access but no Connected
Paper Workspace. After sign-in, AlphaDesk routes that identity to `/admin`, where **Create my Paper
Workspace** provisions its tenant-scoped `ONBOARDING` workspace and default watchlist. This
administrator-only action is idempotent, consumes no invitation, and reuses the existing Supabase
identity. Invitation codes remain reserved for new operator registration.

Administrators always see **Admin Console** and **Access & Invitations** in the authenticated
sidebar. Connected Paper navigation remains visibly inactive until workspace provisioning finishes.

```bash
docker compose --env-file .env.local up -d --build --force-recreate api worker web
curl -fsS http://localhost:8000/api/v1/auth/registration-status
```

When configuration is safe, the status response reports that the Supabase URL and server secret
are configured, public signup is disabled, Admin Auth is reachable, and registration is available.

The administrator creates a readable bearer code under **Access & Invitations** and sends either
the code or the prefilled registration link. AlphaDesk validates and consumes the code before its
server-side Supabase Admin adapter creates the identity and tenant workspace.

If Supabase creates an identity but AlphaDesk cannot persist the workspace, AlphaDesk attempts to
delete that identity immediately and records a critical redacted log if cleanup is uncertain.
Review such incidents in Supabase Authentication > Users; never delete existing identities merely
because they do not have a workspace without first confirming ownership.

Rotate `SUPABASE_SECRET_KEY` in the Supabase dashboard and restart only the API after a suspected
exposure. Existing sessions continue to use Supabase JWTs and do not require the secret key in the
browser or worker.

```bash
docker compose --env-file .env.local up -d --force-recreate api
```

The worker Compose environment deliberately overrides `SUPABASE_SECRET_KEY` with an empty value.
