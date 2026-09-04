"use client";

import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  Lock,
  CheckCircle2,
  Info,
  Activity,
} from "lucide-react";
import { useEffect, useState } from "react";

import { apiBase } from "@/lib/api";

type Status = {
  guardian_halted: boolean;
  guardian_reason: string | null;
  expires_at: string;
};

export function DemoGuardian() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Initializing isolated demo session…");

  useEffect(() => {
    fetch(`${apiBase}/api/v1/demo/session`, {
      method: "POST",
      credentials: "include",
    })
      .then((response) => response.json() as Promise<Status>)
      .then((next) => {
        setStatus(next);
        setMessage(
          next.guardian_halted
            ? "Demo session is currently HALTED by supervisor."
            : "Demo Guardian is healthy and ready for deterministic replays."
        );
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  async function call(path: "guardian/halt" | "guardian/recover") {
    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/api/v1/demo/${path}`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) throw new Error("Demo Guardian request failed");
      const next = (await response.json()) as Status;
      setStatus(next);
      if (next.guardian_halted) {
        setMessage(
          "Synthetic kill switch ACTIVATED: Fail-closed state triggered for your browser session."
        );
      } else {
        setMessage(
          "Demo session RECOVERED: Supervisor restored to ready state for deterministic replays."
        );
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const isHalted = Boolean(status?.guardian_halted);

  return (
    <>
      <div className={`mode-banner ${isHalted ? "danger" : ""}`}>
        {isHalted ? <ShieldAlert /> : <ShieldCheck />}
        <div>
          <strong>
            {isHalted
              ? "Demo Guardian: FAIL-CLOSED HALT ACTIVE"
              : "Demo Guardian: SUPERVISORY SYSTEMS READY"}
          </strong>
          <span>{message}</span>
        </div>
      </div>

      <section className="control-panel">
        <div className="panel-title">
          <div>
            <small>SESSION-SCOPED SUPERVISORY CONTROLS</small>
            <h2>Manual Safety &amp; Kill Switch Demonstration</h2>
          </div>
          <span className={`status-pill ${isHalted ? "warn" : "good"}`}>
            {isHalted ? "HALTED (EXECUTION BLOCKED)" : "SUPERVISOR ACTIVE"}
          </span>
        </div>
        <p>
          These interactive controls test AlphaDesk&apos;s supervisory circuit breaker in real time.
          Modifications apply exclusively to your signed browser cookie session and cannot affect
          connected paper accounts or other evaluators.
        </p>

        <div className="button-row" style={{ marginTop: 14 }}>
          <button
            type="button"
            className="danger-button"
            disabled={loading || isHalted}
            onClick={() => call("guardian/halt")}
            style={{ display: "inline-flex", alignItems: "center", gap: 7 }}
          >
            <AlertTriangle style={{ width: 14, height: 14 }} />
            {isHalted ? "Kill Switch Tripped" : "Activate demo kill switch"}
          </button>
          <button
            type="button"
            className="secondary-button"
            disabled={loading || !isHalted}
            onClick={() => call("guardian/recover")}
            style={{ display: "inline-flex", alignItems: "center", gap: 7 }}
          >
            <RotateCcw style={{ width: 14, height: 14 }} />
            Reset demo session
          </button>
        </div>
        {status?.guardian_reason && (
          <p className="form-message" style={{ marginTop: 12 }}>
            <strong>Active Incident Reason:</strong> {status.guardian_reason}
          </p>
        )}
      </section>

      {/* Structured Guidance explaining both buttons */}
      <section className="guardian-guide-section">
        <div className="guardian-guide-header-strip">
          <Info style={{ width: 16, height: 16, color: "var(--demo)" }} />
          <strong>Operator &amp; Judge Guidance: Understanding Supervisory Controls</strong>
        </div>

        <div className="guardian-guide-grid">
          {/* Kill Switch Card */}
          <div className="guardian-guide-card">
            <div className="guardian-guide-card-header">
              <div className="guardian-guide-icon danger">
                <AlertTriangle style={{ width: 18, height: 18 }} />
              </div>
              <div>
                <h4>What &ldquo;Activate demo kill switch&rdquo; Does</h4>
                <small className="guide-tag red">Emergency Circuit Breaker</small>
              </div>
            </div>
            <div className="guardian-guide-body">
              <p>
                <strong>Operational Function:</strong> Instantly trips the trading desk into an
                emergency fail-closed state (simulating trigger{" "}
                <code>MANUAL_KILL_SWITCH</code>).
              </p>
              <div className="guardian-guide-bullets">
                <div className="guide-bullet">
                  <Lock style={{ width: 14, height: 14, flexShrink: 0 }} />
                  <div>
                    <strong>Order Intent Lockdown:</strong> The{" "}
                    <code>GuardianExecutionGate</code> immediately blocks all pending and new
                    order intents from advancing to broker submission.
                  </div>
                </div>
                <div className="guide-bullet">
                  <Activity style={{ width: 14, height: 14, flexShrink: 0 }} />
                  <div>
                    <strong>Supervisory Watchdogs:</strong> In production, this same halt is
                    automatically triggered if broker balance diverges, market feeds go stale,
                    or order frequency limits are exceeded.
                  </div>
                </div>
                <div className="guide-bullet">
                  <ShieldCheck style={{ width: 14, height: 14, flexShrink: 0 }} />
                  <div>
                    <strong>Demo Isolation:</strong> In this demo workspace, clicking this button
                    safely toggles your signed session&apos;s <code>guardian_halted</code> state
                    so you can observe how the UI and pipeline enforce halt gates.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Reset Demo Card */}
          <div className="guardian-guide-card">
            <div className="guardian-guide-card-header">
              <div className="guardian-guide-icon green">
                <RotateCcw style={{ width: 18, height: 18 }} />
              </div>
              <div>
                <h4>What &ldquo;Reset demo session&rdquo; Does</h4>
                <small className="guide-tag green">Reconciliation-Gated Recovery</small>
              </div>
            </div>
            <div className="guardian-guide-body">
              <p>
                <strong>Operational Function:</strong> Restores the supervisor to normal
                operational state (<code>HEALTHY</code>) after an incident is addressed.
              </p>
              <div className="guardian-guide-bullets">
                <div className="guide-bullet">
                  <CheckCircle2 style={{ width: 14, height: 14, flexShrink: 0 }} />
                  <div>
                    <strong>Reconciliation Verification:</strong> In connected paper mode,
                    recovery is strictly gated. The desk will refuse recovery until fresh Alpaca
                    portfolio marks, positions, and order states are verified without discrepancy.
                  </div>
                </div>
                <div className="guide-bullet">
                  <Activity style={{ width: 14, height: 14, flexShrink: 0 }} />
                  <div>
                    <strong>Audit Trail Preserved:</strong> Resetting an incident does not erase
                    incident history—all halt intervals, trigger reasons, and operator timestamps
                    remain immutably logged in the audit ledger.
                  </div>
                </div>
                <div className="guide-bullet">
                  <ShieldCheck style={{ width: 14, height: 14, flexShrink: 0 }} />
                  <div>
                    <strong>Demo Restoration:</strong> In this demo workspace, clicking this
                    clears the synthetic halt on your session and returns all scenario inspection
                    tools to ready.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="guardian-isolation-note">
          <Lock style={{ width: 14, height: 14, flexShrink: 0, color: "var(--demo)" }} />
          <span>
            <strong>Tenant Isolation Invariant:</strong> Demo kill switches operate strictly via
            HMAC-signed session cookies (<code>alphadesk_demo</code>). Actions taken here never
            interfere with connected paper broker credentials or other users&apos; testing sessions.
          </span>
        </div>
      </section>
    </>
  );
}
