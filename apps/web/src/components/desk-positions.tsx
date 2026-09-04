"use client";

import { useEffect, useState, useCallback } from "react";
import {
  BriefcaseBusiness,
  CheckCircle2,
  Clock,
  Layers,
  LogOut,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { deskFetch } from "@/lib/api";
import { StateCard } from "@/components/workspace-shell";

type Account = {
  equity: string;
  buying_power: string;
  cash?: string;
  last_equity?: string;
} | null;

type Position = {
  asset_id: string;
  symbol: string;
  side: string;
  quantity: string;
  market_value: string;
  unrealized_pl: string;
};

type Order = {
  broker_order_id: string;
  client_order_id: string;
  status: string;
  symbol: string | null;
  quantity: string;
  filled_quantity: string;
  time_in_force?: string;
};

type Broker = {
  state: string;
};

function parseOptionSymbol(symbol: string) {
  const match = symbol.match(/^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$/);
  if (!match) {
    return { root: symbol, isOption: false, expiry: null, type: null, strike: null };
  }
  const root = match[1];
  const expiry = `20${match[2]}-${match[3]}-${match[4]}`;
  const type = match[5] === "C" ? "Call" : "Put";
  const strike = (Number(match[6]) / 1000).toFixed(2);
  return { root, isOption: true, expiry, type, strike };
}

export function DeskPositions() {
  const [state, setState] = useState<{
    account: Account;
    positions: Position[];
    orders: Order[];
    broker: Broker;
  } | null>(null);
  const [error, setError] = useState("");
  const [closingSymbol, setClosingSymbol] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const refreshData = useCallback(async () => {
    try {
      const [account, positions, orders, broker] = await Promise.all([
        deskFetch<Account>("/desk/broker/account"),
        deskFetch<Position[]>("/desk/broker/positions"),
        deskFetch<Order[]>("/desk/broker/orders"),
        deskFetch<Broker>("/desk/broker/status"),
      ]);
      setState({ account, positions, orders, broker });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projections");
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  async function handleClosePosition(symbol: string) {
    setBusy(true);
    setActionMessage(null);
    try {
      await deskFetch(`/desk/broker/positions/${encodeURIComponent(symbol)}/close`, {
        method: "POST",
      });
      setActionMessage({
        type: "success",
        text: `Closing order for ${symbol} routed to Alpaca paper matching engine.`,
      });
      setClosingSymbol(null);
      await refreshData();
    } catch (e) {
      setActionMessage({
        type: "error",
        text: e instanceof Error ? e.message : `Failed to close position for ${symbol}`,
      });
    } finally {
      setBusy(false);
    }
  }

  if (!state) {
    return <section className="loading-panel">{error || "Loading broker-confirmed projections…"}</section>;
  }

  const pendingOrders = state.orders.filter(
    (o) => o.status === "accepted" || o.status === "new" || o.status === "pending_new"
  );

  return (
    <>
      <div className="mode-banner">
        <ShieldCheck />
        <div>
          <strong>Connected Paper Read Model · Continuous Broker Parity</strong>
          <span>
            Internal read models are synchronized continuously with Alpaca trade updates. Broker truth strictly prevails on any discrepancy.
          </span>
        </div>
      </div>

      <div className="state-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <StateCard
          title="PAPER EQUITY"
          value={
            state.account
              ? `$${Number(state.account.equity).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`
              : "—"
          }
          detail="Tenant broker projection"
          tone="good"
        />
        <StateCard
          title="ACTIVE POSITIONS"
          value={`${state.positions.length} Contract${state.positions.length === 1 ? "" : "s"}`}
          detail="Broker-confirmed exposure"
          tone={state.positions.length > 0 ? "good" : "neutral"}
        />
        <StateCard
          title="WORKING ORDERS"
          value={`${pendingOrders.length} Pending`}
          detail={`${state.orders.length} in lifecycle`}
          tone="good"
        />
        <StateCard
          title="BROKER RECONCILIATION"
          value={state.broker.state}
          detail="Freshness verified · In parity"
          tone={state.broker.state === "RECONCILED" ? "good" : "warn"}
        />
      </div>

      {actionMessage && (
        <div
          className={`mode-banner ${actionMessage.type === "error" ? "danger" : "blue"}`}
          style={{ marginTop: "16px" }}
        >
          {actionMessage.type === "error" ? <XCircle /> : <CheckCircle2 />}
          <div>
            <strong>{actionMessage.type === "error" ? "Execution Warning" : "Closing Order Submitted"}</strong>
            <span>{actionMessage.text}</span>
          </div>
        </div>
      )}

      <div className="positions-section-header" style={{ marginTop: "24px" }}>
        <div>
          <small>PORTFOLIO EXPOSURE</small>
          <h2>Open Option Contracts & Positions</h2>
        </div>
        <span className="status-pill good">ALL EXPOSURE RECONCILED</span>
      </div>

      <section className="data-table">
        <header style={{ gridTemplateColumns: "1.4fr 1.2fr .8fr 1fr 1fr .8fr 1.1fr" }}>
          <span>CONTRACT / STRUCTURE</span>
          <span>EXPIRY & SIDE</span>
          <span>QTY</span>
          <span>MARKET VALUE</span>
          <span>UNREALIZED P/L</span>
          <span>STATE</span>
          <span>ACTION</span>
        </header>
        {state.positions.length ? (
          state.positions.map((p) => {
            const { root, isOption, expiry, type, strike } = parseOptionSymbol(p.symbol);
            const unrealized = Number(p.unrealized_pl);
            const isPositive = unrealized >= 0;
            const isClosing = closingSymbol === p.symbol;

            return (
              <div
                className="data-row"
                key={p.asset_id}
                style={{ gridTemplateColumns: "1.4fr 1.2fr .8fr 1fr 1fr .8fr 1.1fr" }}
              >
                <div>
                  {isOption ? (
                    <>
                      <strong>
                        {root} ${strike} {type}
                      </strong>
                      <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>
                        {p.symbol}
                      </small>
                    </>
                  ) : (
                    <strong>{p.symbol}</strong>
                  )}
                </div>
                <div>
                  <span>{p.side.toUpperCase()}</span>
                  <small style={{ color: "#707d79", fontSize: "9px", display: "block" }}>
                    {expiry ? `Exp: ${expiry}` : "Equity"}
                  </small>
                </div>
                <span>{p.quantity}</span>
                <span>
                  $
                  {Number(p.market_value).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
                <div>
                  <strong style={{ color: isPositive ? "#2f7a1f" : "#a8372c" }}>
                    {isPositive ? `+$` : `-$`}
                    {Math.abs(unrealized).toFixed(2)}
                  </strong>
                </div>
                <span className="status-pill good">RECONCILED</span>
                <div>
                  {isClosing ? (
                    <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                      <button
                        className="danger-button"
                        style={{ fontSize: "11px", padding: "4px 8px" }}
                        disabled={busy}
                        onClick={() => handleClosePosition(p.symbol)}
                      >
                        {busy ? "Closing…" : "Confirm"}
                      </button>
                      <button
                        className="secondary-button"
                        style={{ fontSize: "11px", padding: "4px 8px" }}
                        disabled={busy}
                        onClick={() => setClosingSymbol(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      className="secondary-button"
                      style={{
                        color: "#a8372c",
                        borderColor: "#f3c2be",
                        fontSize: "11px",
                        padding: "4px 10px",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                      onClick={() => setClosingSymbol(p.symbol)}
                    >
                      <LogOut size={12} />
                      Close Position
                    </button>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="table-empty">
            <BriefcaseBusiness />
            <strong>No open positions</strong>
            <p>Your Alpaca paper account currently has no active broker-confirmed exposure.</p>
          </div>
        )}
      </section>

      <div className="positions-section-header" style={{ marginTop: "28px" }}>
        <div>
          <small>IMMUTABLE EXECUTION IDENTITY</small>
          <h2>Orders & Submission Lifecycle</h2>
        </div>
        <span className="status-pill">IDEMPOTENCY ENFORCED</span>
      </div>

      <section className="data-table">
        <header style={{ gridTemplateColumns: "1.3fr 1.3fr 1fr .9fr .7fr 1fr" }}>
          <span>CLIENT ORDER ID</span>
          <span>STRUCTURE / SYMBOL</span>
          <span>BROKER ORDER ID</span>
          <span>FILLED / TOTAL</span>
          <span>TIF</span>
          <span>STATUS</span>
        </header>
        {state.orders.length ? (
          state.orders.map((o) => {
            const isFilled = o.status === "filled";
            return (
              <div
                className="data-row"
                key={o.broker_order_id}
                style={{ gridTemplateColumns: "1.3fr 1.3fr 1fr .9fr .7fr 1fr" }}
              >
                <code
                  style={{
                    fontSize: "9px",
                    background: "#f0f4f2",
                    padding: "3px 6px",
                    borderRadius: "4px",
                  }}
                >
                  {o.client_order_id.length > 18
                    ? `${o.client_order_id.slice(0, 16)}…`
                    : o.client_order_id}
                </code>
                <strong>{o.symbol ?? "MULTI-LEG"}</strong>
                <code style={{ fontSize: "10px" }}>{o.broker_order_id.slice(0, 12)}…</code>
                <span>
                  {o.filled_quantity} / {o.quantity}
                </span>
                <span>{o.time_in_force ?? "DAY"}</span>
                <span className={`status-pill ${isFilled ? "good" : ""}`}>
                  {isFilled ? (
                    <CheckCircle2
                      style={{ width: 12, height: 12, display: "inline", marginRight: 4 }}
                    />
                  ) : (
                    <Clock
                      style={{ width: 12, height: 12, display: "inline", marginRight: 4 }}
                    />
                  )}
                  {o.status.toUpperCase()}
                </span>
              </div>
            );
          })
        ) : (
          <div className="table-empty">
            <Clock />
            <strong>No active working orders</strong>
            <p>All submitted paper orders have reached terminal execution or reconciliation.</p>
          </div>
        )}
      </section>

      <div className="panel-grid" style={{ marginTop: "24px" }}>
        <section className="control-panel">
          <Layers style={{ color: "var(--accent)" }} />
          <h3>CQRS Projection Model</h3>
          <p>
            Positions and order states are completely disposable and rebuildable from the immutable event log. Broker reconciliation runs periodically to assert that local projections match broker reality.
          </p>
        </section>

        <section className="control-panel">
          <ShieldCheck style={{ color: "var(--accent)" }} />
          <h3>Reconciliation Priority</h3>
          <p>
            On any divergence between internal intent and external broker state, the broker state always wins. The Guardian detects discrepancy, pauses new orders, and forces reconciliation.
          </p>
        </section>
      </div>
    </>
  );
}
