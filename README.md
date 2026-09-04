# AlphaDesk

**Institutional-Grade Bounded-Risk AI Options Trading Desk with Fail-Closed Supervisory Control**

> **Built for the [Alpaca AI Trading Agents Hackathon](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon)**  
> 🌐 **Live Deployment:** [https://15.175.60.199.sslip.io](https://15.175.60.199.sslip.io) *(Hosted on AWS Lightsail `ca-central-1a`)*  
> 🎟️ **Judge & Evaluator Invitation Codes [100 Users / 60 Days Access]:**  
> - `J8CBA-RBQGV-68F02-1ZC1P-TSV1A-4`  
> - `P599J-VPRTV-6W649-E2D2V-95ECH-E`  
> - `NNCPX-MQ2W3-3Q9F6-YQH4K-3362M-Q`  

AlphaDesk is a paper-only options research and execution desk engineered to eliminate catastrophic autonomous AI agent failures. By enforcing a mathematical separation of concerns, quantitative risk rules and options pricing math govern all decisions, while LLMs (via OpenRouter) serve strictly as read-only qualitative analysts.

AlphaDesk provides two strictly isolated experiences:

- **Demo Workspace — green:** public, anonymous, deterministic synthetic evidence, and technically incapable of constructing broker adapters.
- **Connected Paper Workspace — blue:** invite-only, Supabase-authenticated, tenant-isolated real Alpaca data, encrypted operator-owned credentials (AES-256-GCM), and explicit confirmation for every paper order.

Live-money trading is not supported. Alpaca paper funds are simulated.

## Project Brief & Core Value Proposition

1. **Deterministic 5-Stage Pipeline:** `Quant Signal → Trade Idea → Structure Candidate → Risk Decision → Order Intent`.
2. **Mathematical Risk Bounding:** Every option idea is structured as a defined-risk spread (Bull Call Spread) with strict max loss limits, break-even validation, and Greeks calculation.
3. **Advisory AI with Strict Schema:** LLMs evaluate catalysts and macro sentiment with strict Pydantic JSON schemas and required citations. The AI is read-only and has zero broker execution authority.
4. **Guardian Supervisory Engine:** An automated fail-closed watchdog that monitors broker state drift, stale quotes, and provides a one-click manual emergency kill switch. Trading cannot resume without cryptographic broker reconciliation.
5. **Multi-Tenant BYOK Vault:** Operator API keys (Alpaca Paper & OpenRouter) are encrypted with tenant-bound AES-256-GCM envelope encryption and never logged or leaked.

## For Hackathon Judges: Evaluation Guide

AlphaDesk provides two isolated evaluation paths tailored for different judging workflows:

### Path A: Instant Evaluation via Public Demo Workspace (Recommended)

**Zero credentials, zero registration, and zero market-hours dependency.**

1. Open the web interface and click **Public Demo Workspace** (or `/demo`).
2. Click **Start Interactive Tour** on the green command center banner. A persistent, 7-step multi-page interactive guide walks you through:
   - **Step 1 — Sandbox Isolation (`/demo`):** Why this workspace is mathematically barred from constructing broker adapters.
   - **Step 2 — Deterministic 5-Stage Pipeline (`/demo`):** Quant Signal → Trade Idea → Structure Candidate → Risk Decision → Order Intent.
   - **Step 3 — Scenario Variety (`/demo/opportunities`):** Interactive switcher between `TRADE (Approved)`, disciplined `NO TRADE (Disciplined Pass)`, and `VETOED (Risk Rejection)` outcomes with live explanatory guidance.
   - **Step 4 — Bounded Options Math (`/demo/opportunities`):** Defined-risk vertical spreads (Bull Call Spreads) with mathematically bounded max loss, payoff diagrams, and Greeks.
   - **Step 5 — Positions & Orders (`/demo/positions`):** Simulated CQRS read models showing active multi-leg positions (NVDA Bull Call Spread), Greeks, and working orders queue.
   - **Step 6 — Guardian Kill Switch (`/demo/audit`):** Trigger simulated emergency halts (`MANUAL_KILL_SWITCH`), inspect fail-closed gate enforcement, and test recovery.
   - **Step 7 — Strategy Lab (`/demo/strategy-lab`):** Bitemporal firewall (`SimulationClock`), data fingerprinting, and cost-adjusted paper returns.

### Path B: Live Hands-On Testing via Connected Paper Workspace

**For evaluators testing with real Alpaca paper keys and OpenRouter models.**

1. Navigate to `/register` and enter one of the judge invitation codes:
   - `J8CBA-RBQGV-68F02-1ZC1P-TSV1A-4`
   - `P599J-VPRTV-6W649-E2D2V-95ECH-E`
   - `NNCPX-MQ2W3-3Q9F6-YQH4K-3362M-Q`
2. After sign-in, enter your Alpaca Paper API keys and OpenRouter API key in **Credential Settings**. Credentials are write-only and encrypted with tenant-bound AES-256-GCM.
3. Open **Market Scanner**:
   - Observe the real-time market clock with live countdown to session open/close.
   - Click **Scan now** to fetch real Alpaca bars, news catalysts, and options chains.
   - *Note on Market Hours:* Options market data is active during regular U.S. trading hours (9:30 AM – 4:00 PM ET). Outside regular hours, quotes are stale or illiquid, so candidates report `UNAVAILABLE` or `NO_TRADE` (no fake data is ever synthesized in connected mode).
4. Review an opportunity, run the read-only OpenRouter AI analysis, acknowledge the risk checks, and explicitly submit a paper order to Alpaca Paper Trading.
5. In **Positions & Orders**, observe broker-reconciled account equity and open positions.

## Quick start

Requirements: Docker Desktop with Docker Compose v2. Native quality checks additionally require Python 3.12, `uv`, Node.js, and `pnpm` through Corepack.

```bash
cd /Users/kesse/Desktop/codex/AlphaDesk
cp .env.example .env.local
```

Complete the platform values in `.env.local`. Do not put operator Alpaca or OpenRouter credentials there; operators enter those in **Connected Paper → Credential Settings**.

Start or rebuild the complete stack:

```bash
docker compose --env-file .env.local up -d --build
docker compose --env-file .env.local ps
curl -fsS http://localhost:8000/health/ready
```

Open <http://localhost:3000>.

The API automatically runs `alembic upgrade head` when its container starts. See [`docs/LOCAL_DEVELOPMENT.md`](./docs/LOCAL_DEVELOPMENT.md) for initial configuration, Supabase bootstrap, restart rules, logs, full test commands, and manual acceptance checks.

## Common commands

```bash
# Follow application logs
docker compose --env-file .env.local logs -f api worker web

# Rebuild application containers after code changes
docker compose --env-file .env.local up -d --build --force-recreate api worker web

# Stop the stack while preserving PostgreSQL and NATS volumes
docker compose --env-file .env.local down

# Run all native checks
make check
```

Changing `NEXT_PUBLIC_*` values requires rebuilding `web`. Changing API or worker environment values requires recreating the affected containers. Saving tenant Alpaca or OpenRouter credentials in the UI does not require a restart; the worker discovers verified Alpaca credentials automatically.

## Security boundaries

- Every runtime is hard-locked to `PAPER_ONLY`; live endpoints and mode switches are absent.
- Anonymous routes expose demo and non-sensitive health/registration status only.
- Connected routes require a verified Supabase JWT and derive workspace ownership server-side.
- Supabase public signup is disabled; AlphaDesk validates an invitation before creating an identity through server-only Admin Auth.
- Alpaca/OpenRouter secrets are write-only, encrypted with tenant-bound AES-256-GCM, and never returned to the browser.
- The worker is explicitly denied `SUPABASE_SECRET_KEY`.
- Connected scans use Alpaca provenance or return unavailable/`NO_TRADE`; synthetic fallback is prohibited.
- Only the tenant execution engine can submit an order, after explicit confirmation and fresh risk, Guardian, broker-state, account, quote, and idempotency checks.

## Documentation

- [Local development and testing](./docs/LOCAL_DEVELOPMENT.md)
- [Current project status and resumption guide](./docs/PROJECT_STATUS.md)
- [Architecture and trust boundaries](./docs/architecture.md)
- [Hosted Supabase setup](./docs/SUPABASE.md)
- [Demo and connected-workspace walkthrough](./docs/DEMO.md)
- [Acceptance record](./docs/ACCEPTANCE.md)
- [Lightsail deployment and restore](./docs/LIGHTSAIL.md)
