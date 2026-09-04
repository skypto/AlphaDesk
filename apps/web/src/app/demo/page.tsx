import { ArrowRight, Database, GitBranch, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { StateCard, WorkspaceShell } from "@/components/workspace-shell";

export default function DemoCommandCenter() {
  return (
    <WorkspaceShell
      mode="demo"
      title="Demo Synthetic Command Center"
      description="Replay deterministic scenarios without accessing connected-market data."
    >
      <div className="mode-banner">
        <ShieldCheck />
        <div>
          <strong>This workspace is synthetic and execution-incapable.</strong>
          <span>Its signed demo session, Guardian state, and replay selection are isolated from every other visitor.</span>
        </div>
      </div>

      <div className="state-grid">
        <StateCard title="DATA MODE" value="SYNTHETIC" detail="Versioned Catalyst fixtures" tone="good" />
        <StateCard title="BROKER ACCESS" value="IMPOSSIBLE" detail="Demo code has no adapter path" tone="good" />
        <StateCard title="EXECUTION" value="DISABLED" detail="Evidence only" tone="good" />
      </div>

      <section className="control-panel">
        <div className="panel-title">
          <div>
            <small>CATALYST MOMENTUM</small>
            <h2>Completed deterministic chain</h2>
          </div>
          <Link className="text-action" href="/demo/opportunities">
            Open replay <ArrowRight />
          </Link>
        </div>
        <div className="process-chain">
          {["Signal", "Trade Idea", "Candidate", "Risk Decision", "Order Intent"].map((step, index) => (
            <div key={step}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
              <small>Recorded</small>
            </div>
          ))}
        </div>
      </section>

      <div className="panel-grid">
        <section className="control-panel">
          <Database />
          <h3>Bitemporal evidence</h3>
          <p>Replay reads respect observed and available time. Future-known information stays inaccessible.</p>
        </section>
        <section className="control-panel">
          <GitBranch />
          <h3>Immutable audit chain</h3>
          <p>Correlation, causation, risk decisions, and stable client-order IDs remain inspectable.</p>
        </section>
      </div>
    </WorkspaceShell>
  );
}

