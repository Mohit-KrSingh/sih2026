import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App & Public Foundation", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders header, navigation, four entry cards, and demo mode footer", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "healthy",
        timestamp: "2026-10-27T00:00:00Z",
        version: "0.1.0",
        services: {
          database: "connected",
          redis: "connected",
        },
        demo_mode: true,
      }),
    } as Response);

    render(<App />);

    // Header brand
    expect(screen.getAllByText("EduTrace").length).toBeGreaterThan(0);

    // SPEC.md Section 1 & 19: Four entry cards on home page
    expect(screen.getAllByText("Activate College").length).toBeGreaterThan(0);
    expect(screen.getAllByText("College Login").length).toBeGreaterThan(0);
    expect(screen.getAllByText("AICTE Login").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verify Record").length).toBeGreaterThan(0);

    // Footer demo mode notice (SPEC.md hard rule 10)
    expect(
      screen.getByText(/Demo mode: APAAR registry is simulated/i)
    ).toBeInTheDocument();

    // Health status check
    await waitFor(() => {
      expect(screen.getByTestId("overall-status")).toHaveTextContent("healthy");
      expect(screen.getByTestId("db-status")).toHaveTextContent("connected");
      expect(screen.getByTestId("redis-status")).toHaveTextContent("connected");
    });
  });

  it("handles degraded health status", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "degraded",
        timestamp: "2026-10-27T00:00:00Z",
        version: "0.1.0",
        services: {
          database: "disconnected",
          redis: "connected",
        },
        demo_mode: true,
      }),
    } as Response);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("overall-status")).toHaveTextContent("degraded");
      expect(screen.getByTestId("db-status")).toHaveTextContent("disconnected");
      expect(screen.getByTestId("redis-status")).toHaveTextContent("connected");
    });
  });
});
