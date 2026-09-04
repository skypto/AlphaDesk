# Dual-workspace acceptance record

| Area | Implemented evidence | Status |
|---|---|---|
| Global exposure removal | Legacy broker routes removed; anonymous desk requests return 401; old unscoped projections purged | Pass |
| Authentication | Supabase JWT verifier, server-side user sync, admin bootstrap, invitation-gated workspace creation | Pass; live hosted Supabase auth & invitation-gated registration verified |
| Isolation | Workspace-scoped broker, intent, Guardian, credentials, opportunities, audit, AI, outbox and NATS subject helpers; signed demo sessions | Pass; multi-tenant live isolation strictly verified with zero cross-tenant leakage |
| Encrypted BYOK | AES-256-GCM, unique nonce, workspace/provider AAD, key version, write-only status responses, test/save/delete audit | Pass |
| Connection supervision | Per-enabled-workspace adapter and stream, reconciliation, backoff, suspension state, connection cap | Pass; verified live with multiple Alpaca paper accounts ($5k, $100k) and worker reconciliation |
| Real opportunities | 25-symbol watchlist, direct/periodic scans, Alpaca stock/news/options/quote/Greek evidence, live session countdown, closed-market guidance, no fixture fallback | Implemented; market entitlement dependent |
| Scan operations | Tenant-scoped manual/scheduled scan runs, per-run history, real Alpaca market clock, Eastern-time guidance, and no inferred legacy grouping | Pass; authoritative holiday scheduling remains follow-up work |
| OpenRouter | Arbitrary model ID, schema probe, encrypted key, strict JSON/citations, response healing, no tools or execution access | Pass; live structured-output probe with `anthropic/claude-sonnet-4.6` verified |
| Confirmed execution | Immutable review, explicit acknowledgement, fresh deterministic preflight, stable client-order ID uncertainty reconciliation | Pass with deterministic and adapter tests |
| Dual UI | Green public demo with persistent 7-step tour, scenario explainer cards, synthetic positions/orders, supervisory guidance cards, blue authenticated desk, landing chooser, onboarding/settings/scanner/review/admin/Guardian views | Pass; build, typecheck, lint, and UI tests pass |
| Lightsail | Private PostgreSQL/NATS, Caddy-only ingress, HTTPS, restart/health/log rotation, backup/restore runbook | Pass; Live deployment active on AWS Lightsail ca-central-1a with automatic Let's Encrypt HTTPS at https://15.175.60.199.sslip.io |

## Verified live on 2026-09-04

- **AWS Lightsail Production Deployment (`ca-central-1a`):**
  - Provisioned Ubuntu 24.04 LTS instance with 2 GB RAM, 2 vCPUs, and 2 GB swap space.
  - Attached permanent static IP `15.175.60.199`.
  - Caddy automated TLS/SSL certificate issuance verified via Let's Encrypt (`CN=15.175.60.199.sslip.io`).
  - Container health checks verified: PostgreSQL 16, NATS JetStream, FastAPI API, Worker, and Next.js 15 all healthy.
  - Live public endpoints verified (`/`, `/health/ready`, `/demo`, `/register`).
  - Pre-seeded 3 Hackathon Judge Invitation Codes (100 users / 60 days validity) active in PostgreSQL.

- **Live Multi-Tenant E2E Suite:**
  - Public demo signed session and 3 deterministic scenario replays (`approved`, `no_trade`, `risk_veto`) verified.
  - Admin operator Supabase JWT login, workspace provisioning, encrypted Alpaca paper credential verification, OpenRouter `anthropic/claude-sonnet-4.6` structured-output probe, and worker reconciliation ($5,000.00 equity) verified.
  - Regular operator invitation registration with single-use code `J8CBA-RBQGV-68F02-1ZC1P-TSV1A-4`, encrypted Alpaca paper credential verification, and worker reconciliation ($100,000.00 equity) verified.
  - Cross-tenant isolation strictly verified: Operator 1 and Operator 2 workspaces, credentials, equity, and scan histories completely isolated with zero data leakage.
  - Out-of-market scan verified: accurately returned `UNAVAILABLE` with `no_eligible_option_chain`; zero fake data synthesized.
- **Frontend Verification:**
  - TypeScript `tsc --noEmit` passed with 0 errors.
  - ESLint `eslint . --max-warnings=0` passed with 0 warnings.
  - Vitest: 5/5 test files passed.
  - Next.js production build: 21/21 static routes generated.
  - Live HTTP endpoints (`/demo`, `/demo/opportunities`, `/demo/positions`, `/demo/audit`) return 200 OK.
  - Demo Guardian lifecycle (Init $\rightarrow$ Halt $\rightarrow$ Recover) verified with session cookies.

## Verified locally on 2026-09-03

- Python Ruff, mypy, and pytest pass.
- PostgreSQL integration tests for tenant projections and atomic idempotency pass.
- Next.js typecheck, lint, tests, and production build pass.
- Compose services are healthy.
- `/api/v1/broker/status` returns 404, unauthenticated `/api/v1/desk/broker/status` returns 401, and isolated demo endpoints return 200.
- Database migration is at `20260903_0009`; global broker account and credential rows are empty after the required purge.
- Pytest completed with 73 passed and 5 skipped; all Python lint/type checks passed.
- Five web tests, ESLint, TypeScript, and the production Next.js build passed.
- A live Alpaca paper market-clock request and a small OpenRouter structured-output probe succeeded.

## External acceptance still required

- ~~Validate at least two invited users against separate Alpaca paper accounts and record isolation evidence.~~ **[COMPLETED 2026-09-04]**
- Exercise a real-source scan during market availability and explicitly confirm one bounded-risk Alpaca paper order.
- Add automated browser end-to-end coverage and exercise the documented chaos scenarios.
- Replace the scheduled scanner's weekday/time check with Alpaca calendar/clock handling for holidays and early closes.
- Deploy `compose.lightsail.yml` only when a Lightsail host and hostname are supplied.

The prioritized continuation plan is maintained in [`PROJECT_STATUS.md`](./PROJECT_STATUS.md).
