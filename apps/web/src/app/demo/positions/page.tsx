import { CheckCircle2, Clock, Layers, ShieldCheck } from "lucide-react";
import { StateCard, WorkspaceShell } from "@/components/workspace-shell";

export default function DemoPositions() {
  return (
    <WorkspaceShell
      mode="demo"
      title="Synthetic Positions & Orders"
      description="A realistic demonstration projection of active options spreads and reconciled order lifecycle."
    >
      <div className="mode-banner">
        <ShieldCheck />
        <div>
          <strong>Simulated Read Model · Internal CQRS Projections</strong>
          <span>
            In connected mode, these read models are built from immutable internal events and synchronized continuously with Alpaca trade updates.
          </span>
        </div>
      </div>

      <div className="state-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <StateCard
          title="SIMULATED EQUITY"
          value="$104,250.00"
          detail="+$4,250.00 (+4.25% today)"
          tone="good"
        />
        <StateCard
          title="ACTIVE POSITIONS"
          value="2 Structures"
          detail="Within 8-structure policy cap"
          tone="good"
        />
        <StateCard
          title="WORKING ORDERS"
          value="1 Pending"
          detail="1 Filled today"
          tone="good"
        />
        <StateCard
          title="PORTFOLIO GREEKS"
          value="Δ +142.5"
          detail="Γ +12.4 · Θ -$28.40 · ν +86.0"
          tone="good"
        />
      </div>

      <div className="positions-section-header">
        <div>
          <small>PORTFOLIO EXPOSURE</small>
          <h2>Open Option Structures</h2>
        </div>
        <span className="status-pill good">ALL STRUCTURES BOUNDED RISK</span>
      </div>

      <section className="data-table">
        <header style={{ gridTemplateColumns: "1.4fr 1.3fr .8fr 1fr 1fr 1fr .8fr" }}>
          <span>STRUCTURE</span>
          <span>LEGS & EXPIRY</span>
          <span>QTY</span>
          <span>DEBIT / MARK</span>
          <span>UNREALIZED P/L</span>
          <span>MAX LOSS BOUND</span>
          <span>STATE</span>
        </header>

        <div className="data-row" style={{ gridTemplateColumns: "1.4fr 1.3fr .8fr 1fr 1fr 1fr .8fr" }}>
          <div>
            <strong>NVDA Bull Call Spread</strong>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Catalyst Momentum</small>
          </div>
          <div>
            <span>Long 120C / Short 125C</span>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Exp: 2026-09-25 (21 DTE)</small>
          </div>
          <span>2 contracts</span>
          <div>
            <span>Entry: $2.10</span>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Mark: $3.45 ($690 total)</small>
          </div>
          <div>
            <strong style={{ color: "#2f7a1f" }}>+$270.00</strong>
            <small style={{ color: "#2f7a1f", fontSize: "9px", display: "block" }}>+64.3% on risk</small>
          </div>
          <div>
            <strong>$420.00</strong>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Max Profit: $580.00</small>
          </div>
          <span className="status-pill good">RECONCILED</span>
        </div>

        <div className="data-row" style={{ gridTemplateColumns: "1.4fr 1.3fr .8fr 1fr 1fr 1fr .8fr" }}>
          <div>
            <strong>AAPL Long Call</strong>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Directional Catalyst</small>
          </div>
          <div>
            <span>Long 220C</span>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Exp: 2026-10-16 (42 DTE)</small>
          </div>
          <span>1 contract</span>
          <div>
            <span>Entry: $4.80</span>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Mark: $4.20 ($420 total)</small>
          </div>
          <div>
            <strong style={{ color: "#a8372c" }}>-$60.00</strong>
            <small style={{ color: "#a8372c", fontSize: "9px", display: "block" }}>-12.5% on risk</small>
          </div>
          <div>
            <strong>$480.00</strong>
            <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>Defined debit limit</small>
          </div>
          <span className="status-pill good">RECONCILED</span>
        </div>
      </section>

      <div className="positions-section-header" style={{ marginTop: "24px" }}>
        <div>
          <small>IMMUTABLE EXECUTION IDENTITY</small>
          <h2>Orders & Submission Lifecycle</h2>
        </div>
        <span className="status-pill">IDEMPOTENCY ENFORCED</span>
      </div>

      <section className="data-table">
        <header style={{ gridTemplateColumns: "1.3fr 1.5fr .9fr .9fr .8fr 1fr" }}>
          <span>CLIENT ORDER ID</span>
          <span>STRUCTURE</span>
          <span>LIMIT PRICE</span>
          <span>FILLED / TOTAL</span>
          <span>TIF</span>
          <span>STATUS</span>
        </header>

        <div className="data-row" style={{ gridTemplateColumns: "1.3fr 1.5fr .9fr .9fr .8fr 1fr" }}>
          <code style={{ fontSize: "9px", background: "#f0f4f2", padding: "3px 6px", borderRadius: "4px" }}>
            ad-26e3f029b5e3...
          </code>
          <strong>NVDA 120/125 Bull Call Spread</strong>
          <span>$2.10 debit</span>
          <span>2 / 2 filled</span>
          <span>DAY</span>
          <span className="status-pill good">
            <CheckCircle2 style={{ width: 12, height: 12, display: "inline", marginRight: 4 }} />
            FILLED
          </span>
        </div>

        <div className="data-row" style={{ gridTemplateColumns: "1.3fr 1.5fr .9fr .9fr .8fr 1fr" }}>
          <code style={{ fontSize: "9px", background: "#f0f4f2", padding: "3px 6px", borderRadius: "4px" }}>
            ad-8c19fb02410a...
          </code>
          <strong>MSFT 440/450 Bull Call Spread</strong>
          <span>$3.15 debit</span>
          <span>0 / 1 filled</span>
          <span>DAY</span>
          <span className="status-pill">
            <Clock style={{ width: 12, height: 12, display: "inline", marginRight: 4 }} />
            PENDING (ACCEPTED)
          </span>
        </div>
      </section>

      <div className="panel-grid" style={{ marginTop: "20px" }}>
        <section className="control-panel">
          <Layers style={{ color: "var(--demo)" }} />
          <h3>CQRS Projection Model</h3>
          <p>
            Positions and order states are completely disposable and rebuildable from the immutable event log. Broker reconciliation runs periodically to assert that local projections match broker reality.
          </p>
        </section>

        <section className="control-panel">
          <ShieldCheck style={{ color: "var(--demo)" }} />
          <h3>Reconciliation Priority</h3>
          <p>
            On any divergence between internal intent and external broker state, the broker state always wins. The Guardian detects discrepancy, pauses new orders, and forces reconciliation.
          </p>
        </section>
      </div>
    </WorkspaceShell>
  );
}
