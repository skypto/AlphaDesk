import { ArrowRight, FlaskConical, LockKeyhole, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function WorkspaceLanding() {
  return <main className="landing">
    <header className="landing-nav"><Link href="/" className="landing-brand"><span>A</span><strong>AlphaDesk</strong></Link><span className="paper-only">PAPER ONLY</span></header>
    <section className="landing-hero"><p className="kicker">AUTONOMOUS OPTIONS RESEARCH · HUMAN-CONFIRMED PAPER EXECUTION</p><h1>Choose your workspace.</h1><p>Explore deterministic trading workflows safely, or connect an isolated Alpaca paper account for real market evidence and simulated-funds execution.</p></section>
    <section className="workspace-choice">
      <article className="choice-card demo-choice"><div className="choice-icon"><FlaskConical/></div><span className="mode-label">DEMO · SYNTHETIC DATA</span><h2>Public Demo Workspace</h2><p>A private anonymous session with deterministic replay fixtures. No login, credentials, market connection, or broker execution.</p><ul><li>TRADE, NO TRADE, and VETOED replays</li><li>Session-scoped Guardian controls</li><li>Safe for every visitor</li></ul><Link className="choice-action" href="/demo">Enter demo workspace <ArrowRight/></Link></article>
      <article className="choice-card desk-choice"><div className="choice-icon"><LockKeyhole/></div><span className="mode-label">CONNECTED PAPER · REAL DATA</span><h2>Connected Paper Workspace</h2><p>An invite-only, tenant-isolated desk using your own encrypted Alpaca paper and OpenRouter credentials.</p><ul><li>Real Alpaca paper account projections</li><li>Real-source options discovery</li><li>Explicit confirmation for every paper order</li></ul><Link className="choice-action" href="/login">Sign in with invitation <ArrowRight/></Link></article>
    </section>
    <footer className="landing-safety"><ShieldCheck/><span><strong>No live-money trading.</strong> Connected orders route only to Alpaca paper endpoints and always require confirmation.</span></footer>
  </main>;
}
