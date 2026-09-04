import { InvitationAdmin } from "@/components/invitation-admin";
import { WorkspaceShell } from "@/components/workspace-shell";
export default function Invitations(){return <WorkspaceShell mode="desk" title="Strict Invite-Only Access" description="Create, share, inspect, and disable server-enforced registration codes."><InvitationAdmin/></WorkspaceShell>}
