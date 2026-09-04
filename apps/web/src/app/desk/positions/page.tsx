import { DeskPositions } from "@/components/desk-positions";
import { WorkspaceShell } from "@/components/workspace-shell";
export default function Positions(){return <WorkspaceShell mode="desk" title="Positions & Orders" description="Only broker-confirmed, tenant-scoped Alpaca paper projections appear here."><DeskPositions/></WorkspaceShell>}
