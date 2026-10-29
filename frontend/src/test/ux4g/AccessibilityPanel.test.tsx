import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import React from "react";
import {
  AccessibilityProvider,
} from "../../context/AccessibilityContext";
import {
  STORAGE_KEY,
  useAccessibility,
} from "../../context/accessibilityUtils";
import { AccessibilityPanel } from "../../components/ux4g/AccessibilityPanel";

function TestConsumer() {
  const { isPanelOpen, openPanel, togglePanel } = useAccessibility();
  return (
    <div>
      <button id="open-btn" onClick={openPanel}>
        Open
      </button>
      <button id="toggle-btn" onClick={togglePanel}>
        Toggle
      </button>
      <span data-testid="status">{isPanelOpen ? "open" : "closed"}</span>
    </div>
  );
}

describe("UX4G Accessibility Toolkit (R05)", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.removeAttribute("data-text-size");
    document.documentElement.removeAttribute("data-contrast");
    document.documentElement.removeAttribute("data-underline-links");
    document.documentElement.removeAttribute("data-reduced-motion");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders when open and displays all five accessibility controls plus reset", () => {
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    expect(screen.getByTestId("status")).toHaveTextContent("closed");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    // Open panel
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByTestId("status")).toHaveTextContent("open");

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby", "a11y-toolkit-title");
    expect(screen.getByText("Accessibility Tools")).toBeInTheDocument();

    // 1. Text Sizing controls (Normal, Large, X-Large)
    expect(screen.getByRole("button", { name: /Normal \(100%\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Large \(112%\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /X-Large \(125%\)/i })).toBeInTheDocument();

    // 2. Color Theme controls (Light, Dark)
    expect(screen.getByRole("button", { name: "Light" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dark" })).toBeInTheDocument();

    // 3. High Contrast toggle
    expect(screen.getByRole("switch", { name: /high contrast/i })).toBeInTheDocument();

    // 4. Underline Links toggle
    expect(screen.getByRole("switch", { name: /underline links/i })).toBeInTheDocument();

    // 5. Reduced Motion toggle
    expect(screen.getByRole("switch", { name: /reduce motion/i })).toBeInTheDocument();

    // 6. Reset button
    expect(screen.getByRole("button", { name: /Reset Defaults/i })).toBeInTheDocument();
  });

  it("toggles text sizing across all 3 steps and updates root attribute and storage", () => {
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    // Click Large
    const largeBtn = screen.getByRole("button", { name: /Large \(112%\)/i });
    fireEvent.click(largeBtn);
    expect(document.documentElement.getAttribute("data-text-size")).toBe("large");

    let saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    expect(saved.textSize).toBe("large");

    // Click X-Large
    const xlargeBtn = screen.getByRole("button", { name: /X-Large \(125%\)/i });
    fireEvent.click(xlargeBtn);
    expect(document.documentElement.getAttribute("data-text-size")).toBe("x-large");

    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    expect(saved.textSize).toBe("x-large");

    // Click Normal
    const normalBtn = screen.getByRole("button", { name: /Normal \(100%\)/i });
    fireEvent.click(normalBtn);
    expect(document.documentElement.getAttribute("data-text-size")).toBe("normal");

    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    expect(saved.textSize).toBe("normal");
  });

  it("switches theme between Light and Dark mode", () => {
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    const darkBtn = screen.getByRole("button", { name: "Dark" });
    fireEvent.click(darkBtn);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    const lightBtn = screen.getByRole("button", { name: "Light" });
    fireEvent.click(lightBtn);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggles high contrast, underline links, and reduced motion switches", () => {
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    const contrastSwitch = screen.getByRole("switch", { name: /high contrast/i });
    const underlineSwitch = screen.getByRole("switch", { name: /underline links/i });
    const motionSwitch = screen.getByRole("switch", { name: /reduce motion/i });

    // Enable high contrast
    fireEvent.click(contrastSwitch);
    expect(document.documentElement.getAttribute("data-contrast")).toBe("high");

    // Enable underline links
    fireEvent.click(underlineSwitch);
    expect(document.documentElement.getAttribute("data-underline-links")).toBe("true");

    // Enable reduce motion
    fireEvent.click(motionSwitch);
    expect(document.documentElement.getAttribute("data-reduced-motion")).toBe("true");

    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    expect(saved.highContrast).toBe(true);
    expect(saved.underlineLinks).toBe(true);
    expect(saved.reduceMotion).toBe(true);
  });

  it("resets all options to defaults and clears localStorage", () => {
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    // Modify options
    fireEvent.click(screen.getByRole("button", { name: /Large \(112%\)/i }));
    fireEvent.click(screen.getByRole("switch", { name: /high contrast/i }));
    fireEvent.click(screen.getByRole("switch", { name: /underline links/i }));

    expect(document.documentElement.getAttribute("data-text-size")).toBe("large");
    expect(document.documentElement.getAttribute("data-contrast")).toBe("high");
    expect(document.documentElement.getAttribute("data-underline-links")).toBe("true");

    // Click Reset Defaults
    const resetBtn = screen.getByRole("button", { name: /Reset Defaults/i });
    fireEvent.click(resetBtn);

    expect(document.documentElement.getAttribute("data-text-size")).toBe("normal");
    expect(document.documentElement.getAttribute("data-contrast")).toBe("normal");
    expect(document.documentElement.getAttribute("data-underline-links")).toBe("false");

    const resetSaved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    expect(resetSaved.textSize).toBe("normal");
    expect(resetSaved.highContrast).toBe(false);
    expect(resetSaved.underlineLinks).toBe(false);
  });

  it("gracefully operates when localStorage is blocked or throws an error", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError: Access is denied for localStorage");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });

    // Should render and update state in memory without crashing
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    const largeBtn = screen.getByRole("button", { name: /Large \(112%\)/i });
    fireEvent.click(largeBtn);

    expect(document.documentElement.getAttribute("data-text-size")).toBe("large");
  });

  it("closes when Escape key is pressed or when backdrop is clicked", async () => {
    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // Escape closes
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    // Backdrop click closes
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    const backdrop = screen.getByRole("region", { name: /Accessibility Toolkit Backdrop/i });
    fireEvent.click(backdrop);
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("respects system prefers-color-scheme: dark and prefers-reduced-motion: reduce by default", () => {
    window.matchMedia = vi.fn().mockImplementation((query) => {
      return {
        matches: query.includes("prefers-color-scheme: dark") || query.includes("prefers-reduced-motion: reduce"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    });

    render(
      <AccessibilityProvider>
        <TestConsumer />
        <AccessibilityPanel />
      </AccessibilityProvider>
    );

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-reduced-motion")).toBe("true");
  });
});
