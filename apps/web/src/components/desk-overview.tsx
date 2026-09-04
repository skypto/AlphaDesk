"use client";

import { LockKeyhole, Radar, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { StateCard } from "@/components/workspace-shell";
import { deskFetch, IdentityView } from "@/lib/api";

type Workspace = { status: string; scanner_enabled: boolean; watchlist_count: number };
type Account = { equity: string; buying_power: string; status: string } | null;
type Broker = {
  state: string;
  stream_connected: boolean;
  last_reconciled_at: string | null;
};

export function DeskOverview() {
  const router = useRouter();
  const [data, setData] = useState<{
    identity: IdentityView;
    workspace: Workspace;
    account: Account;
    broker: Broker;
  } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const identity = await deskFetch<IdentityView>("/identity/me");
        if (!identity.workspace_id) {
          if (identity.is_admin) {
            router.replace("/admin");
            return;
          }
          throw new Error("No Connected Paper Workspace has been provisioned for this account.");
        }
        const [workspace, account, broker] = await Promise.all([
          deskFetch<Workspace>("/desk/workspace"),
          deskFetch<Account>("/desk/broker/account"),
          deskFetch<Broker>("/desk/broker/status"),
        ]);
        if (active) setData({ identity, workspace, account, broker });
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Workspace unavailable");
      }
    }
    void load();
    return () => { active = false; };
  }, [router]);

  if (error) return <section className="mode-banner danger"><LockKeyhole/><div><strong>Connected workspace unavailable</strong><span>{error}</span></div></section>;
  if (!data) return <section className="loading-panel">Loading tenant-scoped broker state…</section>;
  return <>
    <div className="state-grid">
      <StateCard title="PAPER EQUITY" value={data.account ? `$${Number(data.account.equity).toLocaleString()}` : "—"} detail="Broker-confirmed only"/>
      <StateCard title="BROKER STATE" value={data.broker.state} detail={data.broker.stream_connected ? "trade_updates connected" : "stream unavailable"} tone={data.broker.state === "RECONCILED" ? "good" : "warn"}/>
      <StateCard title="SCANNER" value={data.workspace.scanner_enabled ? "ENABLED" : "OFF"} detail={`${data.workspace.watchlist_count} / 25 symbols`}/>
    </div>
    <div className="mode-banner blue"><ShieldCheck/><div><strong>Workspace boundary active for {data.identity.email}</strong><span>No browser-supplied workspace ID is accepted. Account, events, orders, and Guardian state are server-derived from this identity.</span></div></div>
    <div className="panel-grid three">
      <Link className="control-panel action-panel" href="/desk/settings"><LockKeyhole/><h3>Connect providers</h3><p>Test and save write-only Alpaca paper and OpenRouter credentials.</p><span>Open settings</span></Link>
      <Link className="control-panel action-panel" href="/desk/scanner"><Radar/><h3>Discover opportunities</h3><p>Scan only real Alpaca evidence from your watchlist.</p><span>Open scanner</span></Link>
      <Link className="control-panel action-panel" href="/desk/audit"><ShieldCheck/><h3>Guardian control</h3><p>Halt this workspace or request reconciled recovery.</p><span>Open Guardian</span></Link>
    </div>
  </>;
}
