# AlphaDesk project status and resumption guide

Last updated: 2026-09-04

This file is the durable handoff for development and verification records, alongside the acceptance record in [`ACCEPTANCE.md`](./ACCEPTANCE.md).

## Current milestone

The dual-workspace architecture and the Catalyst Momentum connected-paper vertical slice are fully implemented and verified locally. Multi-operator tenant isolation has been confirmed against live Docker containers with zero cross-tenant data leakage between distinct Alpaca paper accounts. Public demo UX enhancements (persistent 7-step guided tour, scenario guidance cards, synthetic positions projections, and supervisory kill-switch guidance) are implemented and verified. Production deployment is active and verified live on AWS Lightsail (`ca-central-1a`) at `https://15.175.60.199.sslip.io`.

Current database migration head: `20260903_0009_connected_scan_runs.py`.

## Delivered capabilities

| Area | Current state |
|---|---|
| Foundation | FastAPI, worker, Next.js, PostgreSQL, Alembic, NATS JetStream, Compose health checks, structured logging, and fail-closed `PAPER_ONLY` settings are implemented. |
| Demo Workspace | Public signed demo sessions, deterministic Catalyst replays (`TRADE`, `NO_TRADE`, `VETOED`), persistent 7-step multi-page tour with `sessionStorage` memory, interactive scenario explanation cards, synthetic CQRS read models for positions/orders, session-scoped Guardian kill switch/recovery with detailed operator guidance, and Strategy Lab evidence are implemented. Demo code cannot construct a broker adapter. |
| Authentication | Hosted Supabase JWT login plus strict server-side invitation registration are implemented. Public Supabase signup is disabled. Verified live with admin and invited operator identities. |
| Administration | Protected Admin Console, invitation creation/disablement, pre-generated judge invitation codes, readable hashed bearer codes, and invitation-free provisioning for an existing administrator identity are implemented. |
| Tenant isolation | Workspaces scope credentials, broker state, projections, intents, events, Guardian state, opportunities, scan runs, AI runs, audit state, and NATS subjects. Browser-supplied tenant IDs are not trusted. Verified live across multiple operator accounts with zero data leakage. |
| Credential vault | Alpaca paper and OpenRouter secrets are write-only and encrypted with versioned tenant-bound AES-256-GCM. Test/save/replace/delete flows and audit events are implemented. |
| Alpaca state | The worker supervises each verified workspace independently, reconciles paper account state, and consumes trade updates. Unknown, stale, divergent, or unreconciled state blocks execution. Verified with $5k and $100k paper accounts. |
| Options and risk | Eight bounded-risk structures, payoff calculations, break-even, Greeks, liquidity filtering, deterministic risk policy, and undefined-risk rejection are implemented and tested. |
| Market Scanner | 25-symbol watchlists, manual and five-minute scheduled scans, real Alpaca evidence, live session open/close countdown timer, closed-market guidance banner, no synthetic fallback, and tenant-scoped scan-run history are implemented. |
| AI workflow | OpenRouter BYOK, arbitrary model IDs, capability probe, strict schema validation, citations, retries/timeouts, response healing, and safe AI-only degradation are implemented. Verified live with `anthropic/claude-sonnet-4.6`. AI has no execution tools. |
| Paper execution | Immutable review, explicit acknowledgement, fresh deterministic preflight, stable client-order ID, tenant-bound submission, and uncertainty reconciliation are implemented. Unattended execution is absent. |
| Guardian/UI | Tenant-specific halt/recovery, broker projections, dual green/blue interfaces, admin navigation, responsive market status, and scan history are implemented. |
| Deployment | `compose.lightsail.yml`, Caddy ingress with automated Let's Encrypt HTTPS, private PostgreSQL/NATS, health checks, restart policy, log rotation, and backup/restore instructions are live and active on AWS Lightsail (`ca-central-1a`). |

## Latest verification

### 2026-09-04 Live End-to-End & Production Verification
- **AWS Lightsail Live Deployment:** Active at `https://15.175.60.199.sslip.io` with automated HTTPS, PostgreSQL 16, NATS, FastAPI API, Worker, and Next.js 15.
- **Full Multi-Tenant Live Test Suite:**
  - **Public Demo:** Signed session creation, scenario replays for `approved` (`ORDER_INTENT_CREATED`), `no_trade` (`NO_TRADE`), and `risk_veto` (`RISK_REJECTED`) passed.
  - **Admin Operator:** Supabase JWT authentication, workspace provisioning (`a7818b60-...`), encrypted Alpaca paper credential verification, OpenRouter `anthropic/claude-sonnet-4.6` structured output verification, and worker reconciliation ($5,000.00 equity) verified.
  - **Regular Operator:** Invited registration with code `J8CBA-RBQGV-68F02-1ZC1P-TSV1A-4`, encrypted Alpaca paper credential verification, and worker reconciliation ($100,000.00 equity) verified.
  - **Tenant Isolation:** Operator 1 cannot see Operator 2's workspace, credentials, broker balance, or scan history, and vice versa. Zero cross-tenant data leakage confirmed.
  - **Out-of-Market Scan:** Accurately returned `UNAVAILABLE` with `no_eligible_option_chain`; zero fake data synthesized.
- **Frontend Quality Suite:**
  - TypeScript `tsc --noEmit` passed with 0 errors.
  - ESLint `eslint . --max-warnings=0` passed with 0 warnings.
  - Vitest: 5/5 test suites passed.
  - Next.js production build: 21/21 static routes generated successfully.
- **Pre-generated Judge Invitation Codes:** 5 single-use codes generated and verified active in PostgreSQL.

### 2026-09-03 Local Verification
- Ruff formatting/lint and strict mypy passed.
- Pytest: 73 passed, 5 skipped.
- Web TypeScript, ESLint, and Vitest passed; 5 web tests passed.
- Next.js production build passed.
- PostgreSQL scan-run integration test passed.
- API readiness, Compose service health, and Alembic head `0009` were verified.
- A real Alpaca paper market-clock request succeeded.
- A small live OpenRouter structured-output probe with `anthropic/claude-sonnet-4.6` succeeded.

See [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) to reproduce these checks.

## Important behavior and design decisions

- Public Demo and Connected Paper are separate products at the route, state, visual, and broker-construction boundaries.
- There is no global Alpaca account. Every real account is linked to one authenticated workspace.
- Bootstrap administrators do not receive a trading workspace automatically. They can explicitly provision one from Admin Console without consuming an invitation.
- Operators never place provider keys in `.env.local`; they add them through Connected Paper Credential Settings.
- Connected scans may run after hours, but the UI warns that option quotes may be stale. A lack of a trade is a valid outcome.
- Only scan runs created after migration `0009` appear in scan history. Older opportunity records were not assigned invented run groupings.
- OpenRouter output remains advisory. Malformed or unavailable AI output cannot change risk, pricing, quantity, intent, Guardian, or execution state.

## Remaining acceptance work

Priority order for the next development session:

1. ~~Run the full end-to-end flow with at least two invited operators and two different Alpaca paper accounts; prove no cross-tenant leakage.~~ **[COMPLETED 2026-09-04]**
2. During regular market hours, obtain fresh option evidence and explicitly confirm one bounded-risk Alpaca paper order. Capture submission, trade update, fill/partial-fill, projection, and audit evidence.
3. Add automated browser end-to-end coverage for admin provisioning, invitation registration, credential onboarding, two isolated demo sessions, scanning, AI degradation, confirmation, and Guardian recovery.
4. Replace the scheduled scanner's local weekday/time calculation with Alpaca's authoritative market calendar/clock so holidays and exceptional closures are handled correctly.
5. Exercise chaos cases against running services: worker death during submission, duplicated/reordered events, WebSocket loss, stale quotes, partial-fill cancellation, and recovery.
6. Conduct a security pass covering API authorization, log/exception redaction, encrypted-record inspection, rate limiting for registration/credential tests/scans, CSRF assumptions, and dependency/container scanning.
7. ~~Deploy to Lightsail only after a host and hostname are available; configure HTTPS/Supabase redirects, backups, restore drill, and external acceptance.~~ **[COMPLETED 2026-09-04 — live at https://15.175.60.199.sslip.io in ca-central-1a]**
8. Complete hackathon polish: final architecture graphic, judge script, deterministic replay captures, and backup demo assets.

## Known limitations and cautions

- Lightsail deployment is live and operational on AWS Lightsail (`ca-central-1a`) with automatic Let's Encrypt HTTPS, pre-seeded judge invitations, and private container networking.
- Real market-data results depend on Alpaca entitlements, market hours, contract availability, liquidity, and quote freshness. Connected mode intentionally has no fixture fallback.
- The worker's scheduled-scan market-hours gate currently handles weekdays and regular Eastern hours but not exchange holidays or early closes; manual scans use the displayed real Alpaca clock for operator context.
- A live paper-order execution during regular market hours remains follow-up validation. Multi-operator tenant isolation is verified and recorded.
- Preserve `ALPHADESK_CREDENTIAL_MASTER_KEYS` across restarts and backups. Losing a key version makes the corresponding encrypted BYOK records unrecoverable.

## Resume checklist

1. Read this file and `git status` if Git has since been initialized/restored.
2. Review `.env.example`; never print or commit `.env.local`.
3. Start the stack with `docker compose --env-file .env.local up -d --build`.
4. Confirm `/health/ready`, `/api/v1/auth/registration-status`, service health, and migration head.
5. Run the automated checks in `LOCAL_DEVELOPMENT.md` before changing behavior.
6. Select the highest remaining acceptance item above and update this file plus `ACCEPTANCE.md` when it is completed.

## High-value code entry points

- API composition: [`../apps/api/app.py`](../apps/api/app.py)
- Connected API: [`../apps/api/routes/desk.py`](../apps/api/routes/desk.py)
- Registration API: [`../apps/api/routes/auth.py`](../apps/api/routes/auth.py)
- Admin API: [`../apps/api/routes/admin.py`](../apps/api/routes/admin.py)
- Worker supervisors: [`../apps/worker/__main__.py`](../apps/worker/__main__.py)
- Database models: [`../packages/database/models.py`](../packages/database/models.py)
- Connected scanner: [`../packages/connected/opportunities.py`](../packages/connected/opportunities.py)
- OpenRouter/provider boundary: [`../packages/ai/provider.py`](../packages/ai/provider.py)
- Execution boundary: [`../packages/execution/engine.py`](../packages/execution/engine.py)
- Scanner UI: [`../apps/web/src/components/market-scanner.tsx`](../apps/web/src/components/market-scanner.tsx)
- Local Compose: [`../docker-compose.yml`](../docker-compose.yml)
- Production Compose: [`../compose.lightsail.yml`](../compose.lightsail.yml)
