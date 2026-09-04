import { Suspense } from "react";
import Link from "next/link";
import { AuthPanel } from "@/components/auth-panel";
export default function Register(){return <main className="auth-page"><Link href="/" className="landing-brand"><span>A</span><strong>AlphaDesk</strong></Link><Suspense><AuthPanel mode="register"/></Suspense><p className="auth-foot">Credentials are added later and encrypted by AlphaDesk. Never paste them into the signup form.</p></main>}
