"use client";

import { AlertTriangle, CheckCircle2, Clock3, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { deskFetch } from "@/lib/api";

type Leg = { side: string; ratio: number; contract?: { symbol?: string; strike?: string; option_type?: string } };
type Structure = { structure_type?: string; max_loss?: string; max_profit?: string; break_evens?: string[]; legs?: Leg[] };
type Candidate = { structure?: Structure };
type RiskCheck = { name: string; passed: boolean };
type RiskDecision = { checks?: RiskCheck[] };
type OrderIntent = { client_order_id: string; quantity: number; limit_price: string };
type Analysis = { opportunity_id: string; symbol: string; disposition: string; source: string; observed_at: string; expires_at: string; signal: Record<string, unknown>; candidate: Candidate | null; risk_decision: RiskDecision | null; order_intent: OrderIntent | null; reason_codes: string[] };

export function OrderReview({ id }: { id: string }) {
  const [opportunity, setOpportunity] = useState<Analysis | null>(null); const [ack, setAck] = useState(false); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { deskFetch<Analysis>(`/desk/opportunities/${id}`).then(setOpportunity).catch((error: Error) => setMessage(error.message)); }, [id]);
  const expired = useMemo(() => !opportunity || new Date(opportunity.expires_at) <= new Date(), [opportunity]);
  if (!opportunity) return <section className="loading-panel">{message || "Loading immutable order review…"}</section>;

  const structure = opportunity.candidate?.structure; const intent = opportunity.order_intent; const checks = opportunity.risk_decision?.checks ?? [];
  const allowed = opportunity.source === "ALPACA_REAL" && opportunity.disposition === "TRADE" && Boolean(intent) && !expired;
  async function confirm() { if (!intent) return; setBusy(true); try { const order = await deskFetch<{ broker_order_id: string; status: string }>(`/desk/opportunities/${id}/confirm`, { method: "POST", body: JSON.stringify({ client_order_id: intent.client_order_id }) }); setMessage(`Paper order reconciled: ${order.broker_order_id} · ${order.status}`); } catch (error) { setMessage(error instanceof Error ? error.message : "Submission failed safely"); } finally { setBusy(false); } }

  return <><div className={`mode-banner ${allowed ? "blue" : "danger"}`}>{allowed ? <ShieldCheck/> : <AlertTriangle/>}<div><strong>{allowed ? "Real-source intent ready for operator review" : "This opportunity cannot be submitted"}</strong><span>{allowed ? "Every safety and freshness check is re-run when you confirm." : opportunity.reason_codes.join(", ") || "No approved immutable intent is present."}</span></div></div><div className="review-grid"><section className="control-panel"><div className="panel-title"><div><small>IMMUTABLE ORDER REVIEW</small><h2>{opportunity.symbol} · {String(structure?.structure_type ?? "No structure").replaceAll("_", " ")}</h2></div><span className="status-pill good">{opportunity.source}</span></div><div className="review-stats"><div><small>Quantity</small><strong>{intent?.quantity ?? "—"}</strong></div><div><small>Limit</small><strong>${intent?.limit_price ?? "—"}</strong></div><div><small>Maximum loss</small><strong>${structure?.max_loss ?? "—"}</strong></div><div><small>Maximum profit</small><strong>${structure?.max_profit ?? "—"}</strong></div><div><small>Break-even</small><strong>{structure?.break_evens?.join(", ") ?? "—"}</strong></div><div><small>Quote expiry</small><strong>{new Date(opportunity.expires_at).toLocaleTimeString()}</strong></div></div><h3>Strategy legs</h3><div className="leg-list">{(structure?.legs ?? []).map((leg, index) => <div key={`${leg.contract?.symbol}-${index}`}><span>{leg.side} × {leg.ratio}</span><strong>{leg.contract?.symbol ?? `${leg.contract?.strike} ${leg.contract?.option_type}`}</strong></div>)}</div><h3>Deterministic risk checks</h3><div className="check-grid">{checks.map((check) => <div key={check.name}><CheckCircle2/><span>{check.name}</span><strong>{check.passed ? "PASS" : "FAIL"}</strong></div>)}</div></section><aside className="control-panel confirmation-panel"><Clock3/><small>STABLE CLIENT-ORDER ID</small><code>{intent?.client_order_id ?? "No intent"}</code><p>Confirmation does not blindly retry. Submission uncertainty is reconciled by this ID.</p><label className="ack"><input type="checkbox" checked={ack} onChange={(event) => setAck(event.target.checked)}/>I understand this sends an order to my Alpaca paper account using simulated funds.</label><button disabled={!allowed || !ack || busy} onClick={confirm}>{busy ? "Reconciling…" : "Submit Paper Order"}</button><p className="microcopy">No unattended execution. Quotes, risk, Guardian, broker state, account status, and idempotency are checked again.</p></aside></div>{message ? <p className="form-message">{message}</p> : null}</>;
}
