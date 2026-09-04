"use client";

import { Bot, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { deskFetch } from "@/lib/api";

type AIResult = {
  provider: string;
  model: string;
  degraded: boolean;
  failure_reason: string | null;
  decision: { recommendation: string; confidence: number; reasons: string[] };
};

export function AIResearchPanel({ opportunityId }: { opportunityId: string }) {
  const [result, setResult] = useState<AIResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true); setMessage("");
    try { setResult(await deskFetch<AIResult>(`/desk/opportunities/${opportunityId}/ai`, { method: "POST" })); }
    catch (error) { setMessage(error instanceof Error ? error.message : "AI research unavailable"); }
    finally { setBusy(false); }
  }

  return <section className="control-panel"><div className="panel-title"><div><small>READ-ONLY AI WORKFLOW</small><h2>Context · Devil&apos;s Advocate · Decision Composer</h2></div><button onClick={run} disabled={busy}><Bot/>{busy ? "Analyzing…" : "Run OpenRouter analysis"}</button></div><p>The model receives cited evidence only. It has no broker, credential, Guardian, risk, pricing, quantity, or execution tools.</p>{message ? <p className="form-message">{message}</p> : null}{result ? <div className={`mode-banner ${result.degraded ? "danger" : "blue"}`}><ShieldCheck/><div><strong>{result.decision.recommendation} · {result.decision.confidence}%</strong><span>{result.degraded ? `AI degraded safely (${result.failure_reason}). Deterministic state is unchanged.` : `${result.provider} / ${result.model}: ${result.decision.reasons.join(" ")}`}</span></div></div> : null}</section>;
}
