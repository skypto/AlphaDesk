"use client";

import { Clipboard, Copy, Link2, ShieldCheck, TicketCheck, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { deskFetch } from "@/lib/api";

type Invitation = {
  invitation_id: string; comment: string; max_uses: number; use_count: number;
  expires_at: string | null; disabled_at: string | null; created_at: string;
  invitation_code: string | null;
};

export function InvitationAdmin() {
  const [items, setItems] = useState<Invitation[]>([]);
  const [created, setCreated] = useState<Invitation | null>(null);
  const [comment, setComment] = useState("");
  const [uses, setUses] = useState(1);
  const [days, setDays] = useState(7);
  const [message, setMessage] = useState("");

  async function load() { setItems(await deskFetch<Invitation[]>("/admin/invitations")); }
  useEffect(() => { deskFetch<Invitation[]>("/admin/invitations").then(setItems).catch((error: Error) => setMessage(error.message)); }, []);

  async function copy(value: string, confirmation: string) {
    await navigator.clipboard.writeText(value);
    setMessage(confirmation);
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      const invitation = await deskFetch<Invitation>("/admin/invitations", { method: "POST", body: JSON.stringify({ comment, max_uses: uses, expires_in_days: days }) });
      setItems((current) => [invitation, ...current]);
      setCreated(invitation);
      setComment("");
      setMessage("Invitation created. Copy the code or link now; the code cannot be retrieved later.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Creation failed"); }
  }

  async function disable(id: string) {
    try {
      await deskFetch(`/admin/invitations/${id}`, { method: "DELETE" });
      if (created?.invitation_id === id) setCreated(null);
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Disable failed"); }
  }

  const code = created?.invitation_code;
  const registrationLink = code ? `${location.origin}/register?code=${encodeURIComponent(code)}` : "";

  return (
    <>
      <div className="mode-banner blue"><ShieldCheck /><div><strong>Hosted Supabase · strict invite-only access</strong><span>AlphaDesk validates a hashed code before any Supabase identity is created.</span></div></div>
      <div className="invite-admin-grid">
        <form className="invite-form" onSubmit={create}>
          <div className="invite-form-heading"><TicketCheck /><div><h2>Create invitation</h2><p>Set access limits, then share the code privately.</p></div></div>
          <label>Internal comment<input value={comment} maxLength={240} onChange={(event) => setComment(event.target.value)} placeholder="Hackathon judge access" /></label>
          <div className="invite-form-row">
            <label>Usage cap<input type="number" min={1} max={100} value={uses} onChange={(event) => setUses(Number(event.target.value))} /></label>
            <label>Expires in days<input type="number" min={1} max={90} value={days} onChange={(event) => setDays(Number(event.target.value))} /></label>
          </div>
          <button>Create invitation <Clipboard /></button>
        </form>
        <section className="invite-explainer control-panel">
          <small>HOW INVITATIONS WORK</small><h2>Controlled account creation</h2>
          <p><strong>Invitation required.</strong> Missing, expired, disabled, and exhausted codes create no identity.</p>
          <p><strong>One-time visibility.</strong> Raw codes appear only immediately after creation.</p>
          <p><strong>Server-enforced.</strong> The browser cannot call public Supabase signup.</p>
        </section>
      </div>
      {code ? (
        <section className="created-invitation control-panel" aria-live="polite">
          <div><small>NEW INVITATION · COPY NOW</small><h2>{code}</h2><p>This readable bearer code will not be shown again after this page reloads.</p></div>
          <div className="button-row">
            <button onClick={() => copy(code, "Invitation code copied.")}><Copy /> Copy code</button>
            <button className="secondary-button" onClick={() => copy(registrationLink, "Registration link copied.")}><Link2 /> Copy registration link</button>
          </div>
        </section>
      ) : null}
      {message ? <p className="form-message" role="status">{message}</p> : null}
      <section className="data-table">
        <header><span>COMMENT</span><span>USAGE</span><span>EXPIRY</span><span>STATUS</span><span>ACTION</span></header>
        {items.map((item) => <div className="data-row" key={item.invitation_id}><strong>{item.comment || "No comment"}</strong><span>{item.use_count} / {item.max_uses}</span><time>{item.expires_at ? new Date(item.expires_at).toLocaleDateString() : "Never"}</time><span className={item.disabled_at ? "status-pill" : "status-pill good"}>{item.disabled_at ? "DISABLED" : "ACTIVE"}</span><button className="icon-button" disabled={Boolean(item.disabled_at)} onClick={() => disable(item.invitation_id)} aria-label="Disable invitation"><Trash2 /></button></div>)}
      </section>
    </>
  );
}
