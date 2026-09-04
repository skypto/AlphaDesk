import { AdminConsole } from "@/components/admin-console";
import { WorkspaceShell } from "@/components/workspace-shell";

export default function AdminPage() {
  return (
    <WorkspaceShell
      mode="desk"
      title="Administrator Access Active"
      description="Platform administration and protected workspace provisioning."
    >
      <AdminConsole />
    </WorkspaceShell>
  );
}
