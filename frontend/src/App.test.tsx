import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders header and demo mode footer", async () => {
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

    expect(screen.getByText("APAAR")).toBeInTheDocument();
    expect(screen.getByText(/Demo mode: APAAR registry is simulated/i)).toBeInTheDocument();

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
