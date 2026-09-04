import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminConsole } from "./admin-console";

const deskFetch = vi.fn();

vi.mock("@/lib/api", () => ({ deskFetch: (...args: unknown[]) => deskFetch(...args) }));

describe("AdminConsole", () => {
  beforeEach(() => deskFetch.mockReset());

  it("provisions the existing admin identity without an invitation", async () => {
    deskFetch
      .mockResolvedValueOnce({
        email: "admin@example.test",
        is_admin: true,
        workspace_id: null,
        workspace_status: null,
      })
      .mockResolvedValueOnce({
        workspace_id: "workspace-1",
        status: "ONBOARDING",
        created: true,
        watchlist_count: 7,
      });

    render(<AdminConsole />);
    const button = await screen.findByRole("button", { name: "Create my Paper Workspace" });
    fireEvent.click(button);

    await waitFor(() => expect(deskFetch).toHaveBeenLastCalledWith(
      "/admin/workspace",
      { method: "POST" },
    ));
    expect(await screen.findByText("Provisioned")).toBeInTheDocument();
    expect(screen.getByText(/existing Supabase identity remains the owner/i)).toBeInTheDocument();
  });
});
