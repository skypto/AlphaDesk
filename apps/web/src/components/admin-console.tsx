"use client";

import {
  ArrowRight,
  CheckCircle2,
  Database,
  LockKeyhole,
  ShieldCheck,
  Star,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { deskFetch, IdentityView } from "@/lib/api";

type ProvisionedWorkspace = {
  workspace_id: string;
  status: string;
  created: boolean;
  watchlist_count: number;
};

export function AdminConsole() {
  const [identity, setIdentity] = useState<IdentityView | null>(null);
  const [workspace, setWorkspace] = useState<ProvisionedWorkspace | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    deskFetch<IdentityView>("/identity/me")
      .then(setIdentity)
      .catch((error: Error) => setMessage(error.message));
  }, []);

  async function provision() {
    setBusy(true);
    setMessage("");
    try {
      const result = await deskFetch<ProvisionedWorkspace>("/admin/workspace", {
        method: "POST",
      });
      setWorkspace(result);
      setIdentity((current) => current ? {
        ...current,
        workspace_id: result.workspace_id,
        workspace_status: result.status,
      } : current);
      setMessage(result.created
        ? "Your Connected Paper Workspace is ready for provider setup."
        : "Your existing Connected Paper Workspace is ready.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Workspace provisioning failed");
    } finally {
      setBusy(false);
    }
  }

  if (!identity && !message) return <section className="loading-panel">Loading administrator state…</section>;
  if (!identity) return <p className="form-message" role="alert">{message}</p>;
  if (!identity.is_admin) return <section className="mode-banner danger"><LockKeyhole/><div><strong>Administrator access required</strong><span>This identity cannot manage invitations or provision administrator workspaces.</span></div></section>;

  const hasWorkspace = Boolean(identity.workspace_id || workspace);
  return (
    <div className="admin-console-grid">
      <section className="admin-provision-panel control-panel">
        <div className="admin-access-heading">
          <span><ShieldCheck /></span>
          <div><small>ADMINISTRATOR ACCESS</small><h2>Active</h2><p>Signed in with protected platform-administration rights.</p></div>
        </div>
        {hasWorkspace ? (
          <div className="admin-workspace-ready">
            <CheckCircle2 />
            <div><small>CONNECTED PAPER WORKSPACE</small><h3>Provisioned</h3><p>Status: {workspace?.status ?? identity.workspace_status}. Your existing Supabase identity remains the owner.</p></div>
            <Link className="primary-link" href="/desk/settings">Continue setup <ArrowRight /></Link>
          </div>
        ) : (
          <>
            <div className="admin-provision-copy"><h2>Create your Paper Workspace</h2><p>No Connected Paper Workspace has been provisioned for this account. Create a tenant-isolated workspace to enable operator controls.</p></div>
            <ul className="admin-provision-list">
              <li><ShieldCheck/><span><strong>Protected onboarding</strong>Administrator authorization is checked again by the API.</span></li>
              <li><Star/><span><strong>ONBOARDING outcome</strong>The default liquid-options watchlist is applied.</span></li>
              <li><LockKeyhole/><span><strong>No invitation required</strong>No invitation use is consumed.</span></li>
              <li><Database/><span><strong>No new identity</strong>Your existing Supabase identity and admin role are retained.</span></li>
            </ul>
            <button className="admin-provision-button" disabled={busy} onClick={provision}><LockKeyhole/>{busy ? "Creating workspace…" : "Create my Paper Workspace"}</button>
          </>
        )}
        {message ? <p className="form-message" role="status">{message}</p> : null}
      </section>
      <aside className={`admin-workspace-state control-panel ${hasWorkspace ? "ready" : "inactive"}`}>
        <div><small>CONNECTED PAPER WORKSPACE</small><span className={`status-pill ${hasWorkspace ? "good" : ""}`}>{hasWorkspace ? "ACTIVE" : "NOT PROVISIONED"}</span></div>
        <LockKeyhole />
        <h2>{hasWorkspace ? "Ready for provider setup" : "Inactive until provisioned"}</h2>
        <p>{hasWorkspace ? "Add your Alpaca paper and OpenRouter credentials to complete onboarding." : "Operator controls, market data streams, and paper execution remain unavailable until this workspace is created."}</p>
        {hasWorkspace ? <Link className="secondary-link" href="/desk">Open Workspace Control <ArrowRight /></Link> : null}
      </aside>
    </div>
  );
}
