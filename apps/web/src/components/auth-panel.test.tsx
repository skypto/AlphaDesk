import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthPanel } from "./auth-panel";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams("code=ABCDE-FGHJK-MNPQR-STVWX-YZ234-A"),
}));

vi.mock("@/lib/api", () => ({
  apiBase: "http://api.test",
  supabaseBrowser: () => ({ auth: { signInWithPassword: vi.fn() } }),
}));

describe("strict invitation registration", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ registration_available: true }),
    }));
  });

  it("requires and prefills the invitation code", async () => {
    render(<AuthPanel mode="register" />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Create connected workspace" })).toBeEnabled());
    const input = screen.getByLabelText(/Invitation code/);
    expect(input).toBeRequired();
    expect(input).toHaveValue("ABCDE-FGHJK-MNPQR-STVWX-YZ234-A");
    expect(screen.getByText("Server-controlled registration")).toBeInTheDocument();
  });
});
