"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { KeyRound, ShieldCheck } from "lucide-react";

import { apiBase, deskFetch, IdentityView, supabaseBrowser } from "@/lib/api";

type RegistrationStatus = {
  supabase_url_configured: boolean;
  server_secret_configured: boolean;
  public_signup_disabled: boolean;
  admin_auth_reachable: boolean;
  registration_available: boolean;
};

export function AuthPanel({ mode }: Readonly<{ mode: "login" | "register" }>) {
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invitationCode, setInvitationCode] = useState(
    search.get("code") ?? search.get("token") ?? "",
  );
  const [message, setMessage] = useState("");
  const [available, setAvailable] = useState(mode === "login");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (mode !== "register") return;
    fetch(`${apiBase}/api/v1/auth/registration-status`, { cache: "no-store" })
      .then((response) => response.json())
      .then((status: RegistrationStatus) => {
        setAvailable(status.registration_available);
        if (!status.registration_available) {
          setMessage("Invite-only registration is temporarily unavailable. Contact the administrator.");
        }
      })
      .catch(() => {
        setAvailable(false);
        setMessage("Invite-only registration is temporarily unavailable. Contact the administrator.");
      });
  }, [mode]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const client = supabaseBrowser();
    if (!client) {
      setMessage("Supabase is not configured for this deployment.");
      setBusy(false);
      return;
    }
    try {
      if (mode === "register") {
        const response = await fetch(`${apiBase}/api/v1/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, invitation_code: invitationCode }),
        });
        if (!response.ok) {
          throw new Error(
            response.status === 503
              ? "Invite-only registration is temporarily unavailable. Contact the administrator."
              : "Registration could not be completed. Check the code or contact the administrator.",
          );
        }
        const { error } = await client.auth.signInWithPassword({ email, password });
        if (error) {
          setMessage("Your account was created. Sign in to continue to your Connected Paper workspace.");
          return;
        }
        router.push("/desk/settings");
        router.refresh();
      } else {
        const { error } = await client.auth.signInWithPassword({ email, password });
        if (error) throw error;
        const identity = await deskFetch<IdentityView>("/identity/me");
        router.push(identity.is_admin && !identity.workspace_id ? "/admin" : "/desk");
        router.refresh();
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-card">
      <div>
        <span className="mode-label">CONNECTED PAPER · STRICT INVITE ONLY</span>
        <h1>{mode === "login" ? "Sign in to your desk" : "Create your operator account"}</h1>
        <p>
          {mode === "login"
            ? "Your Supabase session identifies your private AlphaDesk workspace."
            : "AlphaDesk validates your invitation before Supabase creates an identity or workspace."}
        </p>
      </div>
      {mode === "register" ? (
        <div className="auth-security-note">
          <ShieldCheck aria-hidden="true" />
          <span><strong>Server-controlled registration</strong> Public Supabase signup is disabled.</span>
        </div>
      ) : null}
      <form onSubmit={submit}>
        <label>
          Email
          <input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          Password
          <input type="password" required minLength={8} maxLength={128} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {mode === "register" ? (
          <label htmlFor="invitation-code">
            Invitation code
            <div className="invitation-code-input">
              <KeyRound aria-hidden="true" />
              <input id="invitation-code" required minLength={20} maxLength={128} autoComplete="off" spellCheck={false} value={invitationCode} onChange={(event) => setInvitationCode(event.target.value.toUpperCase())} placeholder="ABCDE-FGHJK-MNPQR-STVWX-YZ234-A" />
            </div>
            <small>Codes are case-insensitive; spaces and hyphens are optional.</small>
          </label>
        ) : null}
        <button disabled={busy || !available}>{busy ? "Working…" : mode === "login" ? "Sign in" : "Create connected workspace"}</button>
      </form>
      {message ? <p className="form-message" role="status">{message}</p> : null}
      {mode === "login"
        ? <p className="auth-switch">Have an invitation? <Link href="/register">Create an account</Link></p>
        : <p className="auth-switch">Already registered? <Link href="/login">Sign in</Link></p>}
    </div>
  );
}
