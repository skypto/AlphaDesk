import { describe, expect, it } from "vitest";

import { h0SystemStatus } from "./system";

describe("H0 safety fixture", () => {
  it("is paper-only and blocks autonomous execution", () => {
    expect(h0SystemStatus.mode).toBe("PAPER_ONLY");
    expect(h0SystemStatus.autonomous_execution_enabled).toBe(false);
    expect(h0SystemStatus.guardian_halted).toBe(true);
  });
});

