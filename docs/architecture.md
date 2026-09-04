# AlphaDesk dual-workspace architecture

```mermaid
flowchart TB
  Visitor[Anonymous visitor] --> DemoSession[Signed expiring demo session]
  DemoSession --> Fixtures[Versioned synthetic replay fixtures]
  DemoSession --> DemoGuardian[Session-scoped Demo Guardian]
  Fixtures --> DemoUI[Green Demo Workspace]

  Operator[Invited operator] --> Supabase[Hosted Supabase Free Auth]
  Supabase --> JWT[Verified JWT identity]
  JWT --> Tenant[Server-derived connected workspace]
  Tenant --> Vault[AES-256-GCM BYOK vault]
  Vault --> Supervisor[Per-workspace connection supervisor]
  Supervisor --> Alpaca[Alpaca Paper only]
  Alpaca --> Projections[Tenant broker projections]
  Tenant --> Scanner[Real-source scanner]
  Alpaca --> MarketClock[Paper market clock]
  MarketClock --> Scanner
  Scanner --> ScanRuns[Tenant-scoped scan history]
  Scanner --> Intent[Immutable OrderIntent]
  Intent --> Confirm[Explicit operator confirmation]
  Confirm --> Safety[Freshness + Risk + Guardian + Idempotency]
  Safety --> Execution[Execution Engine]
  Execution --> Alpaca
  Projections --> DeskUI[Blue Connected Paper Workspace]

  Tenant --> Postgres[(Lightsail PostgreSQL)]
  DemoSession --> Postgres
  Tenant --> NATS[NATS subjects namespaced by workspace]
```

## Security boundaries

- Demo routes cannot construct a broker adapter and never fall back to connected data.
- Connected routes require a valid Supabase JWT. The API derives the workspace from the authenticated subject and never accepts a tenant ID from the browser.
- Operator Alpaca and OpenRouter secrets are write-only, encrypted with unique nonces and tenant-bound associated data, and stored only in AlphaDesk PostgreSQL.
- Supabase's server secret is available only to the API. The worker receives an explicit empty override and the browser receives only public Supabase configuration.
- The worker decrypts a credential only in memory and supervises each workspace independently.
- Manual and scheduled scans create workspace-scoped scan-run records. Opportunity rows retain real-source timestamps and provenance; older ungrouped rows are not assigned fabricated history.
- Only the Execution Engine submits orders. Every paper order requires a fresh explicit confirmation and is reconciled by stable client-order ID.
- PostgreSQL and NATS have no published ports in the Lightsail Compose file. Caddy is the only public ingress.
