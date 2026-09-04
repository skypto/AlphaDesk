import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import WorkspaceLanding from "./page";

describe("workspace landing", () => {
  it("clearly separates synthetic demo and connected paper modes", () => {
    render(<WorkspaceLanding />);
    expect(screen.getByText("PAPER ONLY")).toBeInTheDocument();
    expect(screen.getByText("Public Demo Workspace")).toBeInTheDocument();
    expect(screen.getByText("Connected Paper Workspace")).toBeInTheDocument();
    expect(screen.getByText("No live-money trading.")).toBeInTheDocument();
  });
});
