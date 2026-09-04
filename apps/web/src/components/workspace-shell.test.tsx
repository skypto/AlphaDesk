import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "./workspace-shell";

const deskFetch = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/lib/api", () => ({
  deskFetch: (...args: unknown[]) => deskFetch(...args),
  supabaseBrowser: () => null,
}));

describe("WorkspaceShell admin navigation", () => {
  beforeEach(() => deskFetch.mockReset());

  it("shows admin navigation and disables operator tools before provisioning", async () => {
    deskFetch.mockResolvedValue({
      email: "admin@example.test",
      is_admin: true,
      workspace_id: null,
      workspace_status: null,
    });
    render(<WorkspaceShell mode="desk" title="Admin" description="Console"><div>Body</div></WorkspaceShell>);

    expect(await screen.findByRole("link", { name: /Admin Console/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Access & Invitations/ })).toBeInTheDocument();
    expect(screen.getByText("Workspace Control").closest("span")).toHaveAttribute("aria-disabled", "true");
  });
});
