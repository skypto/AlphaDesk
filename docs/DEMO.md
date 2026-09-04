# AlphaDesk dual-workspace demo runbook

Start the local stack:

```bash
docker compose --env-file .env.local up -d --build
docker compose --env-file .env.local ps
curl -fsS http://localhost:8000/health/ready
```

Open <http://localhost:3000>. The landing page makes the workspace boundary explicit.

## Public Demo Workspace — green

No login or credentials are required.

1. Enter **Public Demo Workspace** and point out `DEMO · SYNTHETIC DATA` and `EXECUTION: DISABLED`.
2. Click **Start Interactive Tour** on the Command Center banner. The persistent 7-step guided tour stays active across route transitions, remembers state in `sessionStorage`, and can be minimized to a floating pill.
3. In **Opportunities** (`/demo/opportunities`), use the tabbed scenario switcher to explore `TRADE (Approved)`, `NO TRADE (Disciplined Pass)`, and `VETOED (Risk Rejection)`. Notice the live **Scenario Explainer Card** describing the catalyst confidence, capital preservation discipline, and portfolio concentration rules behind each disposition.
4. Inspect the bounded spread math (NVDA Bull Call Debit Spread), Greeks, and stable `ad-…` client-order ID. Emphasize that this code path cannot construct a broker adapter.
5. In **Positions & Orders** (`/demo/positions`), review the simulated CQRS read model featuring realistic \$104k equity, aggregated portfolio Greeks ($\Delta$, $\Theta$, $\text{Vega}$), an active NVDA 120/125C Bull Call Spread, an AAPL Long Call, and active working orders.
6. In **Audit & Demo Guardian** (`/demo/audit`), review the educational cards explaining the Kill Switch and Reset Demo operations. Click **Activate demo kill switch** to simulate a `MANUAL_KILL_SWITCH` fail-closed state, then click **Reset demo session** to demonstrate recovery. Note that this state belongs exclusively to that signed browser session (`alphadesk_demo`).
7. In **Strategy Lab** (`/demo/strategy-lab`), show the point-in-time firewall (`SimulationClock`), walk-forward validation, and SHA-256 data fingerprint contracts.

## Connected Paper Workspace — blue

Supabase and a valid invitation are required.

1. Sign in and show that every route is labeled `CONNECTED PAPER · REAL DATA / SIMULATED FUNDS`.
2. In **Credential Settings**, test and save Alpaca paper and OpenRouter credentials. Values are write-only, encrypted with tenant-bound AES-256-GCM, and disappear from the form after encryption.
3. In **Market Scanner**, observe the real-time market clock with live countdown to session open/close (e.g., `Opens in 35m` or `Closes in 6h 15m`). If outside market hours, point out the closed-market educational banner explaining why options quotes are stale or unavailable.
4. Click **Scan now**. Connected results must say `ALPACA_REAL`; unavailable data produces no synthetic substitute. Run it again and show that scan history keeps each run separate.
5. Review an opportunity and run the read-only OpenRouter analysis. AI degradation must not change the deterministic disposition or execution controls.
6. If the scanner produces a fresh approved opportunity, point out quote expiry, payoff, risk checks, and stable client-order ID.
7. Check the acknowledgement and click **Submit Paper Order** only when you intentionally want an Alpaca paper transaction. The API reruns freshness, risk, Guardian, broker reconciliation, account status, and idempotency checks.
8. In **Positions & Orders**, show broker-confirmed projections. In **Audit & Guardian**, halt only this tenant and demonstrate reconciliation-gated recovery.

`NO_TRADE` and `UNAVAILABLE` are valid connected outcomes. Do not force a paper order for the demo; use the public deterministic `TRADE` replay when the market does not provide an eligible live candidate.

> AlphaDesk is for research and education. Alpaca paper funds are simulated. Live-money trading is absent.

For the complete setup and validation procedure, see [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md).
