import { ConnectedGuardian } from "@/components/connected-guardian";
import { WorkspaceShell } from "@/components/workspace-shell";
export default function Audit(){return <WorkspaceShell mode="desk" title="Audit & Guardian" description="Workspace-isolated incident controls with broker-state recovery gates."><ConnectedGuardian/></WorkspaceShell>}
