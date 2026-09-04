import { WorkspaceShell } from "@/components/workspace-shell";
import { WorkflowReplay } from "@/components/workflow-replay";
export default function DemoOpportunities() { return <WorkspaceShell mode="demo" title="Synthetic Opportunities" description="Switch replay outcomes produced by the backend, not hard-coded in the interface."><WorkflowReplay/></WorkspaceShell>; }
