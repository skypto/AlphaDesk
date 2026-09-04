import { DemoGuardian } from "@/components/demo-guardian";
import { WorkspaceShell } from "@/components/workspace-shell";
export default function DemoAudit(){return <WorkspaceShell mode="demo" title="Audit & Demo Guardian" description="Demonstrate halt and recovery without changing shared or connected state."><DemoGuardian/></WorkspaceShell>}
