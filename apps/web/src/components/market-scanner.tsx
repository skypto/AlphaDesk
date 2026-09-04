"use client";

import { AlertTriangle, Clock3, History, Play, Radar, RefreshCw } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { deskFetch } from "@/lib/api";

type Analysis = { opportunity_id: string; scan_run_id: string | null; symbol: string; disposition: string; source: string; observed_at: string; expires_at: string; signal: Record<string, unknown>; candidate: Record<string, unknown> | null; order_intent: Record<string, unknown> | null; reason_codes: string[] };
type Workspace = { scanner_enabled: boolean; watchlist_count: number; status: string };
type ScanFailure = { symbol: string; code: "REAL_DATA_UNAVAILABLE" };
type ScanResult = { scan_run_id: string; trigger: string; started_at: string; completed_at: string; attempted: number; results: Analysis[]; failures: ScanFailure[] };
type ScanRun = { scan_run_id: string; trigger: string; source: string; started_at: string; completed_at: string | null; attempted: number; completed: number; failed: number };
type MarketClock = { is_open: boolean; timestamp: string; next_open: string; next_close: string; timezone: string; regular_session: string; source: string };

const easternTime = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "numeric", minute: "2-digit", second: "2-digit", timeZoneName: "short" });
const easternDateTime = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });

function formatCountdown(target: string | null, current: Date): string | null {
  if (!target) return null;
  const diffMs = new Date(target).getTime() - current.getTime();
  if (diffMs <= 0) return "in moments";
  const diffMins = Math.floor(diffMs / 60000);
  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function MarketScanner() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [entry, setEntry] = useState("");
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [results, setResults] = useState<Analysis[]>([]);
  const [runs, setRuns] = useState<ScanRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [clock, setClock] = useState<MarketClock | null>(null);
  const [now, setNow] = useState(() => new Date());
  const [busy, setBusy] = useState(false);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [message, setMessage] = useState("");


  async function selectRun(run: ScanRun) {
    setHistoryBusy(true);
    try {
      setResults(await deskFetch<Analysis[]>(`/desk/scanner/runs/${run.scan_run_id}`));
      setSelectedRunId(run.scan_run_id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Scan history unavailable");
    } finally {
      setHistoryBusy(false);
    }
  }

  async function refreshStoredResults() {
    const nextRuns = await deskFetch<ScanRun[]>("/desk/scanner/runs");
    setRuns(nextRuns);
    if (nextRuns[0]) await selectRun(nextRuns[0]);
    else {
      setResults([]);
      setSelectedRunId(null);
    }
  }

  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        const [watchlist, space, scanRuns, marketClock] = await Promise.all([
          deskFetch<string[]>("/desk/watchlist"),
          deskFetch<Workspace>("/desk/workspace"),
          deskFetch<ScanRun[]>("/desk/scanner/runs"),
          deskFetch<MarketClock>("/desk/market-clock"),
        ]);
        if (!active) return;
        setSymbols(watchlist);
        setWorkspace(space);
        setRuns(scanRuns);
        setClock(marketClock);
        if (scanRuns[0]) {
          const latest = await deskFetch<Analysis[]>(`/desk/scanner/runs/${scanRuns[0].scan_run_id}`);
          if (active) {
            setResults(latest);
            setSelectedRunId(scanRuns[0].scan_run_id);
          }
        }
      } catch (error) {
        if (active) setMessage(error instanceof Error ? error.message : "Scanner unavailable");
      }
    }
    void initialize();
    const timeTicker = window.setInterval(() => setNow(new Date()), 1000);
    const clockTicker = window.setInterval(() => {
      void deskFetch<MarketClock>("/desk/market-clock").then(setClock).catch(() => undefined);
    }, 60_000);
    return () => {
      active = false;
      window.clearInterval(timeTicker);
      window.clearInterval(clockTicker);
    };
  }, []);

  async function saveWatchlist(event: FormEvent) {
    event.preventDefault();
    const next = Array.from(new Set(entry.split(/[\s,]+/).map((value) => value.trim().toUpperCase()).filter(Boolean))).slice(0, 25);
    try {
      setSymbols(await deskFetch<string[]>("/desk/watchlist", { method: "PUT", body: JSON.stringify({ symbols: next }) }));
      setEntry("");
      setMessage("Watchlist updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Update failed");
    }
  }

  async function scan() {
    setBusy(true);
    setMessage("Scanning real Alpaca market, news, contract, quote, and Greek sources…");
    try {
      const scanResult = await deskFetch<ScanResult>("/desk/scanner/scan", { method: "POST" });
      const run: ScanRun = { scan_run_id: scanResult.scan_run_id, trigger: scanResult.trigger, source: "ALPACA_REAL", started_at: scanResult.started_at, completed_at: scanResult.completed_at, attempted: scanResult.attempted, completed: scanResult.results.length, failed: scanResult.failures.length };
      setResults(scanResult.results);
      setSelectedRunId(run.scan_run_id);
      setRuns((previous) => [run, ...previous.filter((item) => item.scan_run_id !== run.scan_run_id)].slice(0, 10));
      setMessage(run.failed === 0 ? `Scan completed for all ${run.completed} symbols. Synthetic fallback was not used.` : `Scan processed ${run.completed} of ${run.attempted} symbols; ${run.failed} were unavailable from real-data sources. Synthetic fallback was not used.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Scan unavailable");
    } finally {
      setBusy(false);
    }
  }

  async function toggle() {
    try {
      setWorkspace(await deskFetch<Workspace>("/desk/scanner", { method: "PUT", body: JSON.stringify({ enabled: !workspace?.scanner_enabled }) }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Scanner update failed");
    }
  }

  const selectedRun = runs.find((run) => run.scan_run_id === selectedRunId) ?? null;
  const latestSelected = Boolean(selectedRun && runs[0]?.scan_run_id === selectedRun.scan_run_id);
  const nextEvent = clock ? (clock.is_open ? clock.next_close : clock.next_open) : null;
  const countdown = formatCountdown(nextEvent, now);

  return <>
    <section className={`market-clock-strip ${clock?.is_open ? "open" : "closed"}`} aria-live="polite">
      <div className="market-clock-state">
        <span className="mode-dot"/>
        <div>
          <small>US MARKET STATUS</small>
          <strong>{clock ? (clock.is_open ? "Regular session open" : "Regular session closed") : "Checking Alpaca clock…"}</strong>
          {countdown ? <span className="countdown-pill">{clock?.is_open ? `Closes in ${countdown}` : `Opens in ${countdown}`}</span> : null}
        </div>
      </div>
      <div><small>REGULAR SESSION</small><strong>{clock?.regular_session ?? "9:30 AM-4:00 PM ET"}</strong></div>
      <div><small>EASTERN TIME</small><strong>{easternTime.format(now)}</strong></div>
      <div className="market-clock-guidance">{clock?.is_open ? <Clock3/> : <AlertTriangle/>}<span><strong>{clock?.is_open ? "Freshness checks active" : "After-hours notice"}</strong><small>{clock?.is_open ? `Next close ${nextEvent ? easternDateTime.format(new Date(nextEvent)) : ""}` : `Option quotes may be stale. Next open ${nextEvent ? easternDateTime.format(new Date(nextEvent)) : ""}.`}</small></span></div>
    </section>

    {clock && !clock.is_open ? (
      <div className="closed-market-banner" role="status">
        <AlertTriangle />
        <div>
          <strong>Regular Market Session is Currently Closed</strong>
          <p>
            Connected Paper evaluates live Alpaca options chains with zero synthetic fallback. Outside regular U.S. trading hours (9:30 AM–4:00 PM ET), options quotes are stale or illiquid, causing candidates to report <code>UNAVAILABLE</code> or <code>NO TRADE</code>.
          </p>
          <Link href="/demo">
            Try the Public Demo Workspace with interactive scenario replays →
          </Link>
        </div>
      </div>
    ) : null}

    <div className="scanner-toolbar"><div><small>{latestSelected ? "LATEST SCAN RESULTS" : "HISTORICAL SCAN RESULTS"}</small><strong>{selectedRun ? `${selectedRun.completed} / ${selectedRun.attempted} watchlist symbols` : `${symbols.length} / 25 watchlist symbols`}</strong>{selectedRun ? <span>{easternDateTime.format(new Date(selectedRun.started_at))} · {selectedRun.trigger.toLowerCase()}</span> : null}</div><label className="toggle"><input type="checkbox" checked={workspace?.scanner_enabled ?? false} onChange={toggle}/><span/>5-minute market-hours scan</label><button disabled={busy || symbols.length === 0} onClick={scan}><Play/>{busy ? "Scanning…" : "Scan now"}</button></div>
    {message ? <p className="form-message">{message}</p> : null}
    <form className="watchlist-form" onSubmit={saveWatchlist}><label>Replace watchlist (comma or space separated)<input value={entry} onChange={(event) => setEntry(event.target.value)} placeholder={symbols.join(", ") || "SPY, QQQ, AAPL, MSFT"}/></label><button className="secondary-button">Save watchlist</button></form>

    <div className="scanner-results-layout">
      <section className="data-table"><header><span>OPPORTUNITY</span><span>DISPOSITION</span><span>SOURCE</span><span>OBSERVED</span><span>ACTION</span></header>{results.length === 0 ? <div className="table-empty"><Radar/><strong>No scan results yet</strong><p>Run a scan to evaluate your watchlist using verified real Alpaca data.</p></div> : results.map((result) => <div className="data-row" key={result.opportunity_id}><strong>{result.symbol}</strong><div><span className={`status-pill ${result.disposition === "TRADE" ? "good" : ""}`}>{result.disposition.replaceAll("_", " ")}</span>{result.disposition === "UNAVAILABLE" ? <small style={{ color: "#915714", fontSize: "8px", display: "block", marginTop: "3px" }}>Stale / closed market</small> : null}</div><span>{result.source}</span><time>{easternDateTime.format(new Date(result.observed_at))}</time><Link href={`/desk/opportunities/${result.opportunity_id}`}>Review →</Link></div>)}</section>
      <aside className="scan-history" aria-label="Scan history"><h2><History/>Scan history</h2>{runs.length === 0 ? <p>No completed scans.</p> : runs.slice(0, 5).map((run, index) => <button className={run.scan_run_id === selectedRunId ? "selected" : ""} disabled={historyBusy} key={run.scan_run_id} onClick={() => void selectRun(run)}><span>{index === 0 ? <b>Latest scan</b> : easternDateTime.format(new Date(run.started_at))}</span><strong>{run.completed} / {run.attempted}</strong><small>{run.failed ? `${run.failed} failed` : "all processed"}</small></button>)}</aside>
    </div>
    <button className="refresh-link" onClick={() => void refreshStoredResults()}><RefreshCw/>Refresh scan history</button>
  </>;
}
