import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  FlagBadge,
  Alert,
  SubmitGateAlert,
  LockedDataAlert,
  SuspendedApprovalAlert,
  DemoModeAlert,
} from "../../components/ux4g";
import type { FlagLevel } from "../../types/validation";

type RgbTuple = [number, number, number];

/**
 * WCAG 2.1 AA Relative Luminance & Contrast Ratio calculation.
 * Formula: https://www.w3.org/WAI/GL/wiki/Relative_luminance
 */
function getLuminance([r, g, b]: RgbTuple): number {
  const [sR, sG, sB] = [r, g, b].map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * sR + 0.7152 * sG + 0.0722 * sB;
}

function getContrastRatio(rgb1: RgbTuple, rgb2: RgbTuple): number {
  const l1 = getLuminance(rgb1);
  const l2 = getLuminance(rgb2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("R08: Flags, Badges and Alerts", () => {
  describe("FlagBadge Component (SPEC §19 & REBRAND_TASKS R08)", () => {
    const levels: FlagLevel[] = ["error", "exception", "warning", "info"];

    it("renders all four levels with proper labels and icons without relying on color alone", () => {
      const expectedLabels: Record<FlagLevel, string> = {
        error: "Error",
        exception: "Exception",
        warning: "Warning",
        info: "Info",
      };

      const expectedIcons: Record<FlagLevel, string> = {
        error: "cancel",
        exception: "report_problem",
        warning: "warning",
        info: "info",
      };

      levels.forEach((level) => {
        const { unmount } = render(<FlagBadge level={level} />);
        const badge = screen.getByTestId(`flag-badge-${level}`);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveAttribute("role", "status");
        expect(badge).toHaveAttribute("data-level", level);

        // Accessible text label must be present (never color alone)
        expect(badge).toHaveTextContent(expectedLabels[level]);

        // Semantic icon must be present
        const icon = badge.querySelector(".ux4g-icon");
        expect(icon).toBeInTheDocument();
        expect(icon).toHaveTextContent(expectedIcons[level]);

        unmount();
      });
    });

    it("renders error level with red filled style", () => {
      render(<FlagBadge level="error" count={5} />);
      const badge = screen.getByTestId("flag-badge-error");
      expect(badge.style.backgroundColor).toBe("var(--edutrace-flag-error-bg)");
      expect(badge.style.color).toBe("var(--edutrace-flag-error-text)");
      expect(badge).toHaveTextContent("Error");
      expect(badge).toHaveTextContent("(5)");
      expect(badge).toHaveAttribute("aria-label", "Error (5)");
    });

    it("renders exception level with red outlined style (2px border)", () => {
      render(<FlagBadge level="exception" />);
      const badge = screen.getByTestId("flag-badge-exception");
      expect(badge.style.borderWidth).toBe("2px");
      expect(badge.style.borderColor).toBe("var(--edutrace-flag-exception-border)");
      expect(badge.style.backgroundColor).toBe("var(--edutrace-flag-exception-bg)");
      expect(badge.style.color).toBe("var(--edutrace-flag-exception-text)");
      expect(badge).toHaveTextContent("Exception");
    });

    it("renders warning level with orange style", () => {
      render(<FlagBadge level="warning" />);
      const badge = screen.getByTestId("flag-badge-warning");
      expect(badge.style.backgroundColor).toBe("var(--edutrace-flag-warning-bg)");
      expect(badge.style.color).toBe("var(--edutrace-flag-warning-text)");
      expect(badge).toHaveTextContent("Warning");
    });

    it("renders info level with neutral grey style", () => {
      render(<FlagBadge level="info" />);
      const badge = screen.getByTestId("flag-badge-info");
      expect(badge.style.backgroundColor).toBe("var(--edutrace-flag-info-bg)");
      expect(badge.style.color).toBe("var(--edutrace-flag-info-text)");
      expect(badge).toHaveTextContent("Info");
    });

    it("renders custom label with level-aware aria-label for accessibility", () => {
      render(<FlagBadge level="error" label="APAAR_FORMAT" count={2} />);
      const badge = screen.getByTestId("flag-badge-error");
      expect(badge).toHaveTextContent("APAAR_FORMAT");
      expect(badge).toHaveTextContent("(2)");
      expect(badge).toHaveAttribute("aria-label", "Error: APAAR_FORMAT (2)");
    });
  });

  describe("Alerts for Submit Gate, Locked Data, Suspended Approval & Demo Mode", () => {
    it("renders SubmitGateAlert in passed state when canSubmit is true", () => {
      render(<SubmitGateAlert canSubmit={true} />);
      const alert = screen.getByTestId("submit-gate-alert");
      expect(alert).toBeInTheDocument();
      expect(alert.className).toContain("ux4g-alert-success");
      expect(screen.getByText("Submit Gate Passed: Ready for Final Submission")).toBeInTheDocument();
    });

    it("renders SubmitGateAlert in blocked state with blockers when canSubmit is false", () => {
      render(
        <SubmitGateAlert
          canSubmit={false}
          openErrorsCount={3}
          unjustifiedExceptionsCount={1}
          blockers={["APAAR_FORMAT on row 14", "INTAKE_EXCEEDED on UG Computer Science"]}
        />
      );
      const alert = screen.getByTestId("submit-gate-alert");
      expect(alert).toBeInTheDocument();
      expect(alert.className).toContain("ux4g-alert-error");
      expect(screen.getByText("Submit Gate Blocked: Outstanding Compliance Issues")).toBeInTheDocument();
      expect(screen.getByText(/3/)).toBeInTheDocument();
      expect(screen.getByText(/APAAR_FORMAT on row 14/)).toBeInTheDocument();
    });

    it("renders LockedDataAlert with academic year and change request guidance", () => {
      render(<LockedDataAlert academicYear="2026-27" receiptNo="REC-2026-0042" />);
      const alert = screen.getByTestId("locked-data-alert");
      expect(alert).toBeInTheDocument();
      expect(screen.getByText("Central Repository Locked (Read-Only)")).toBeInTheDocument();
      expect(screen.getByText(/academic year 2026-27/)).toBeInTheDocument();
      expect(screen.getByText(/REC-2026-0042/)).toBeInTheDocument();
      const link = screen.getByRole("link", { name: "Change Request" });
      expect(link).toHaveAttribute("href", "/college/change-requests");
    });

    it("renders SuspendedApprovalAlert with read-only notice and status label", () => {
      render(
        <SuspendedApprovalAlert
          status="suspended"
          institutionName="Apex Institute of Technology"
          reason="Pending affiliation renewal documentation"
        />
      );
      const alert = screen.getByTestId("suspended-approval-alert");
      expect(alert).toBeInTheDocument();
      expect(alert.className).toContain("ux4g-alert-error");
      expect(screen.getByText("AICTE Approval Suspended — Read-Only Mode")).toBeInTheDocument();
      expect(screen.getByText(/Apex Institute of Technology's/)).toBeInTheDocument();
      expect(screen.getByText(/HTTP 403/)).toBeInTheDocument();
      expect(screen.getByText(/Pending affiliation renewal documentation/)).toBeInTheDocument();
    });

    it("renders DemoModeAlert with statutory disclaimer per SPEC Rule 10", () => {
      render(<DemoModeAlert />);
      const alert = screen.getByTestId("demo-mode-alert");
      expect(alert).toBeInTheDocument();
      expect(screen.getByText("Demonstration Environment (Demo Mode)")).toBeInTheDocument();
      expect(screen.getByText(/APAAR registry lookups, DigiLocker verification/)).toBeInTheDocument();
      expect(screen.getByText(/not an official government service/)).toBeInTheDocument();
    });

    it("supports dismissing Alert when onDismiss is provided", () => {
      const handleDismiss = vi.fn();
      render(<Alert variant="info" title="Dismissible Note" onDismiss={handleDismiss} />);
      const dismissBtn = screen.getByRole("button", { name: "Dismiss alert" });
      fireEvent.click(dismissBtn);
      expect(handleDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("WCAG 2.1 AA Contrast Ratio Verification (>= 4.5:1 required)", () => {
    /**
     * Exact sRGB values from UX4G Design System 3.0 tokens
     * mapped via tokens.css for both light and dark themes.
     */
    const badgeColorPairs: Record<string, { fg: RgbTuple; bg: RgbTuple; minRatio: number }> = {
      "Flag Error (Light)": { fg: [255, 255, 255], bg: [179, 37, 30], minRatio: 4.5 },
      "Flag Exception (Light)": { fg: [138, 26, 22], bg: [255, 255, 255], minRatio: 4.5 },
      "Flag Warning (Light)": { fg: [255, 255, 255], bg: [173, 78, 0], minRatio: 4.5 },
      "Flag Info (Light)": { fg: [255, 255, 255], bg: [64, 64, 64], minRatio: 4.5 },
      "Flag Error (Dark)": { fg: [255, 255, 255], bg: [179, 37, 30], minRatio: 4.5 },
      "Flag Exception (Dark)": { fg: [255, 179, 174], bg: [10, 10, 10], minRatio: 4.5 },
      "Flag Warning (Dark)": { fg: [255, 255, 255], bg: [173, 78, 0], minRatio: 4.5 },
      "Flag Info (Dark)": { fg: [255, 255, 255], bg: [64, 64, 64], minRatio: 4.5 },
    };

    const alertColorPairs: Record<string, { fg: RgbTuple; bg: RgbTuple; minRatio: number }> = {
      "Alert Info (Light)": { fg: [0, 35, 41], bg: [201, 247, 242], minRatio: 4.5 },
      "Alert Success (Light)": { fg: [0, 56, 31], bg: [221, 248, 216], minRatio: 4.5 },
      "Alert Warning (Light)": { fg: [97, 37, 0], bg: [255, 231, 186], minRatio: 4.5 },
      "Alert Error (Light)": { fg: [138, 26, 22], bg: [255, 236, 238], minRatio: 4.5 },
      "Alert Info (Dark)": { fg: [201, 247, 242], bg: [0, 109, 117], minRatio: 4.5 },
      "Alert Success (Dark)": { fg: [221, 248, 216], bg: [0, 82, 44], minRatio: 4.5 },
      "Alert Warning (Dark)": { fg: [255, 231, 186], bg: [135, 56, 0], minRatio: 4.5 },
      "Alert Error (Dark)": { fg: [255, 236, 238], bg: [138, 26, 22], minRatio: 4.5 },
    };

    Object.entries(badgeColorPairs).forEach(([name, { fg, bg, minRatio }]) => {
      it(`verifies ${name} text/background pair meets WCAG 2.1 AA 4.5:1 contrast`, () => {
        const ratio = getContrastRatio(fg, bg);
        expect(ratio).toBeGreaterThanOrEqual(minRatio);
      });
    });

    Object.entries(alertColorPairs).forEach(([name, { fg, bg, minRatio }]) => {
      it(`verifies ${name} text/background pair meets WCAG 2.1 AA 4.5:1 contrast`, () => {
        const ratio = getContrastRatio(fg, bg);
        expect(ratio).toBeGreaterThanOrEqual(minRatio);
      });
    });
  });
});
