"use client";

import {
  Activity,
  BriefcaseBusiness,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Radar,
  Settings,
  ShieldCheck,
  TicketCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { deskFetch, IdentityView, supabaseBrowser } from "@/lib/api";
import { DemoGuidedTour } from "@/components/demo-guided-tour";

type Mode = "demo" | "desk";

const icons = { command: LayoutDashboard, scanner: Radar, positions: BriefcaseBusiness, lab: FlaskConical, guardian: ShieldCheck, settings: Settings, invites: TicketCheck };

const demoNavigation = [
  ["Command Center", "/demo", "command"],
  ["Opportunities", "/demo/opportunities", "scanner"],
  ["Positions & Orders", "/demo/positions", "positions"],
  ["Strategy Lab", "/demo/strategy-lab", "lab"],
  ["Audit & Guardian", "/demo/audit", "guardian"],
] as const;

const deskNavigation = [
  ["Workspace Control", "/desk", "command"],
  ["Market Scanner", "/desk/scanner", "scanner"],
  ["Positions & Orders", "/desk/positions", "positions"],
  ["Audit & Guardian", "/desk/audit", "guardian"],
  ["Credential Settings", "/desk/settings", "settings"],
] as const;

const adminNavigation = [
  ["Admin Console", "/admin", "command"],
  ["Access & Invitations", "/admin/invitations", "invites"],
] as const;

export function WorkspaceShell({ mode, title, description, children }: Readonly<{ mode: Mode; title: string; description: string; children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const [identity, setIdentity] = useState<IdentityView | null>(null);
  const navigation = mode === "demo" ? demoNavigation : deskNavigation;
  const accent = mode === "demo" ? "green" : "blue";

  useEffect(() => {
    if (mode !== "desk") return;
    deskFetch<IdentityView>("/identity/me").then(setIdentity).catch(() => setIdentity(null));
  }, [mode]);

  async function signOut() {
    await supabaseBrowser()?.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return <div className={`workspace-shell mode-${accent}`}>
    <aside className="workspace-sidebar">
      <Link href="/" className="workspace-brand"><span>A</span><div><strong>AlphaDesk</strong><small>Dual-workspace options desk</small></div></Link>
      <div className="paper-only">PAPER ONLY</div>
      <nav aria-label={`${mode} workspace navigation`}>
        {mode === "desk" && identity?.is_admin ? <span className="workspace-nav-label">ADMINISTRATION</span> : null}
        {mode === "desk" && identity?.is_admin ? adminNavigation.map(([label, href, icon]) => { const Icon = icons[icon]; const active = pathname === href || (href !== "/admin" && pathname.startsWith(`${href}/`)); return <Link key={href} className={active ? "workspace-link active" : "workspace-link"} href={href}><Icon size={18}/>{label}</Link>; }) : null}
        {mode === "desk" ? <span className="workspace-nav-label">CONNECTED PAPER</span> : null}
        {navigation.map(([label, href, icon]) => { const Icon = icons[icon]; const active = pathname === href || (href !== `/${mode}` && pathname.startsWith(`${href}/`)); const disabled = mode === "desk" && identity !== null && !identity.workspace_id; return disabled ? <span key={href} className="workspace-link disabled" aria-disabled="true"><Icon size={18}/>{label}</span> : <Link key={href} className={active ? "workspace-link active" : "workspace-link"} href={href}><Icon size={18}/>{label}</Link>; })}
      </nav>
      <div className="workspace-sidebar-spacer"/>
      <section className="workspace-status"><span className="mode-dot"/><small>{mode === "demo" ? "ISOLATED DEMO SESSION" : identity?.is_admin ? "ADMIN ACCESS ACTIVE" : "TENANT-ISOLATED WORKSPACE"}</small><strong>{mode === "demo" ? "Synthetic controls only" : identity?.is_admin && !identity.workspace_id ? "Operator controls inactive" : "Paper controls enforced"}</strong><p>{mode === "demo" ? "No broker adapter can be constructed." : identity?.is_admin && !identity.workspace_id ? "Create your Paper Workspace to enable operator features." : "Execution always requires operator confirmation."}</p></section>
      {mode === "desk" ? <button className="sidebar-button" onClick={signOut}><LogOut size={16}/>Sign out</button> : <Link className="sidebar-button" href="/login">Connect your paper account</Link>}
    </aside>
    <main className="workspace-main">
      <header className="workspace-header"><div><h1>{title}</h1><p>{description}</p></div><div className="workspace-mode"><span>{mode === "demo" ? "DEMO · SYNTHETIC DATA" : "CONNECTED PAPER · REAL DATA / SIMULATED FUNDS"}</span><small><Activity size={14}/> PAPER ONLY</small></div></header>
      <div className="workspace-content">
        {mode === "demo" ? <DemoGuidedTour /> : null}
        {children}
      </div>
    </main>
  </div>;
}

export function Stat({ label, value, detail }: Readonly<{ label: string; value: string; detail: string }>) {
  return <div className="stat"><small>{label}</small><strong>{value}</strong><span>{detail}</span></div>;
}

export function StateCard({ title, value, detail, tone = "neutral" }: Readonly<{ title: string; value: string; detail: string; tone?: "neutral" | "good" | "warn" }>) {
  return <section className={`state-card ${tone}`}><small>{title}</small><strong>{value}</strong><p>{detail}</p></section>;
}
