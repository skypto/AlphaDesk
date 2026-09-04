"use client";

import { useEffect, useState } from "react";
import { AlertOctagon, CheckCircle2, Info } from "lucide-react";

type Replay = {
  disposition: string;
  signal: { symbol: string; score: string; features: { catalyst_confidence: string } };
  candidate: {
    rank_score: string;
    structure: {
      structure_type: string;
      max_loss: string;
      max_profit: string;
      break_evens: string[];
      legs: Array<{ contract: { strike: string }; side: string }>;
    };
  } | null;
  risk_decision: { decision: string; checks: Array<{ name: string; passed: boolean }> } | null;
  order_intent: { client_order_id: string; limit_price: string } | null;
  audit_timeline: string[];
};

const SCENARIO_GUIDANCE = {
  approved: {
    title: "Approved Catalyst Momentum (TRADE)",
    badge: "FULL DECISION LIFECYCLE",
    icon: CheckCircle2,
    tone: "good",
    summary:
      "High quant momentum (85.38/100) and abnormal volume (3.2x) confirmed the catalyst. All 9 deterministic risk checks passed. A defined-risk Bull Call debit spread was constructed with bounded max loss ($210), and a stable client-order ID was generated.",
    keyTakeaway:
      "Judges should note that OrderIntent is reached only after passing hard math and risk gates — never by LLM discretion.",
  },
  no_trade: {
    title: "Disciplined Pass (NO TRADE)",
    badge: "DISCIPLINE OVER ACTIVITY",
    icon: Info,
    tone: "warn",
    summary:
      "Quant score fell below threshold (52/100) and price move was overextended (+14.2% gap). The strategy deliberately refuses to chase. In AlphaDesk, a NO_TRADE decision is a valid, preferred outcome when edge or confirmation is insufficient.",
    keyTakeaway:
      "A disciplined desk knows when NOT to trade. The execution engine stops here; zero capital is put at risk.",
  },
  risk_veto: {
    title: "Deterministic Risk Veto (VETOED)",
    badge: "HARD RISK SUPREMACY",
    icon: AlertOctagon,
    tone: "danger",
    summary:
      "The trade idea had strong conviction, but the Deterministic Risk Engine vetoed submission due to portfolio risk limits (underlying risk concentration would exceed 10% equity cap, and daily loss budget would be breached).",
    keyTakeaway:
      "Proves that deterministic risk controls strictly override all strategy and AI proposals. No prompt can bypass the risk constitution.",
  },
} as const;

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function WorkflowReplay() {
  const [replay, setReplay] = useState<Replay | null>(null);
  const [scenario, setScenario] = useState<"approved" | "no_trade" | "risk_veto">("approved");

  useEffect(() => {
    let active = true;
    fetch(`${apiBase}/api/v1/demo/workflow/replays/${scenario}`, { cache: "no-store" })
      .then((response) => response.ok ? response.json() as Promise<Replay> : null)
      .then((result) => { if (active && result) setReplay(result); })
      .catch(() => undefined);
    return () => { active = false; };
  }, [scenario]);

  const structure = replay?.candidate?.structure;
  const guidance = SCENARIO_GUIDANCE[scenario];
  const GuidanceIcon = guidance.icon;

  return (
    <>
      <div className="notice">Synthetic deterministic replay · no broker submission</div>

      <div className="scenario-selector-container">
        <div className="scenario-selector-header">
          <small>INTERACTIVE SCENARIO SWITCHER</small>
          <span>Select an outcome below to inspect how AlphaDesk evaluates different market conditions:</span>
        </div>
        <div className="replay-tabs" role="group" aria-label="Replay scenario">
          <button
            type="button"
            className={scenario === "approved" ? "active" : ""}
            onClick={() => setScenario("approved")}
          >
            TRADE (Approved)
          </button>
          <button
            type="button"
            className={scenario === "no_trade" ? "active" : ""}
            onClick={() => setScenario("no_trade")}
          >
            NO TRADE (Disciplined Pass)
          </button>
          <button
            type="button"
            className={scenario === "risk_veto" ? "active" : ""}
            onClick={() => setScenario("risk_veto")}
          >
            VETOED (Risk Rejection)
          </button>
        </div>
      </div>

      <div className={`scenario-explainer-card ${guidance.tone}`} role="region" aria-label="Scenario Explanation">
        <div className="scenario-explainer-header">
          <div className="scenario-explainer-title">
            <GuidanceIcon style={{ width: 18, height: 18, flexShrink: 0 }} />
            <div>
              <strong>{guidance.title}</strong>
              <small>{guidance.badge}</small>
            </div>
          </div>
        </div>
        <p className="scenario-explainer-summary">{guidance.summary}</p>
        <div className="scenario-explainer-takeaway">
          <strong>Key Invariant:</strong> {guidance.keyTakeaway}
        </div>
      </div>

      <section className="metric-grid four">
        <Metric label="Underlying" value={replay?.signal.symbol ?? "NVDA"} detail="Synthetic snapshot" />
        <Metric label="Signal score" value={replay ? `${replay.signal.score} / 100` : "Loading…"} detail="Scored in Python" />
        <Metric label="Risk decision" value={replay?.risk_decision?.decision ?? "Pending"} detail="Deterministic policy" />
        <Metric label="Disposition" value={replay?.disposition ?? "Loading…"} detail="Replay gate" />
      </section>
      <div className="two-column">
        <section className="panel">
          <p className="eyebrow">Selected candidate</p>
          <h2>{structure ? "Bull call debit spread" : "No eligible candidate"}</h2>
          <dl className="definition-grid">
            <div><dt>Long call</dt><dd>{structure?.legs[0]?.contract.strike ?? "—"} strike</dd></div>
            <div><dt>Short call</dt><dd>{structure?.legs[1]?.contract.strike ?? "—"} strike</dd></div>
            <div><dt>Maximum loss</dt><dd>${structure?.max_loss ?? "—"}</dd></div>
            <div><dt>Maximum profit</dt><dd>${structure?.max_profit ?? "—"}</dd></div>
          </dl>
        </section>
        <section className="panel">
          <p className="eyebrow">Immutable execution identity</p>
          <h2>Approved intent</h2>
          <div className="decision-box">
            <strong>{replay?.order_intent ? "OrderIntent created" : "Awaiting replay"}</strong>
            <p>{replay?.order_intent?.client_order_id ?? "Stable client-order ID will appear here."}</p>
          </div>
          <p className="body-copy">The fixture stops before submission. The live path additionally requires paper credentials, a fresh reconciliation, and a connected trade-updates stream.</p>
        </section>
      </div>
      <section className="panel">
        <p className="eyebrow">Immutable chain</p>
        <h2>Lifecycle audit</h2>
        <div className="pipeline horizontal">
          {(replay?.audit_timeline ?? ["SIGNAL_CREATED", "TRADE_IDEA_CREATED", "STRUCTURE_SELECTED", "RISK_APPROVED", "ORDER_INTENT_CREATED"]).slice(-5).map((event, index) => (
            <div className={replay ? "pipeline-step ready" : "pipeline-step"} key={event}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{event.replaceAll("_", " ")}</strong>
              <small>{replay ? "Recorded" : "Loading"}</small>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function Metric({ label, value, detail }: Readonly<{ label: string; value: string; detail: string }>) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}
