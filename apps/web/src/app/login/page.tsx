import { Suspense } from "react";
import Link from "next/link";
import { AuthPanel } from "@/components/auth-panel";
export default function Login(){return <main className="auth-page"><Link href="/" className="landing-brand"><span>A</span><strong>AlphaDesk</strong></Link><Suspense><AuthPanel mode="login"/></Suspense><p className="auth-foot">PAPER ONLY · Real funds and live routing are prohibited.</p></main>}
