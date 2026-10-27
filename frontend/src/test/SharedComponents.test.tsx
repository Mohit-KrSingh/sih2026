import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FlagBadge, RoleBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/Table";

describe("Shared UI Components", () => {
  describe("FlagBadge (SPEC.md Section 19)", () => {
    it("renders error badge with red filled style", () => {
      render(<FlagBadge level="error" count={3} />);
      const badge = screen.getByTestId("flag-badge-error");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(/error/i);
      expect(badge).toHaveTextContent("3");
      // Check red filled class
      expect(badge.className).toContain("bg-red-100");
      expect(badge.className).toContain("text-red-800");
    });

    it("renders exception badge with red outlined style", () => {
      render(<FlagBadge level="exception" />);
      const badge = screen.getByTestId("flag-badge-exception");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(/exception/i);
      // Check red outlined classes: border-2, border-red-500, bg-white
      expect(badge.className).toContain("border-2");
      expect(badge.className).toContain("border-red-500");
      expect(badge.className).toContain("bg-white");
    });

    it("renders warning badge with amber style", () => {
      render(<FlagBadge level="warning" />);
      const badge = screen.getByTestId("flag-badge-warning");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(/warning/i);
      expect(badge.className).toContain("bg-amber-100");
      expect(badge.className).toContain("text-amber-900");
    });

    it("renders info badge with grey style", () => {
      render(<FlagBadge level="info" />);
      const badge = screen.getByTestId("flag-badge-info");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(/info/i);
      expect(badge.className).toContain("bg-slate-100");
      expect(badge.className).toContain("text-slate-700");
    });
  });

  describe("RoleBadge", () => {
    it("renders human readable label for each role", () => {
      const { rerender } = render(<RoleBadge role="aicte_admin" />);
      expect(screen.getByText("AICTE Admin")).toBeInTheDocument();

      rerender(<RoleBadge role="aicte_officer" />);
      expect(screen.getByText("AICTE Officer")).toBeInTheDocument();

      rerender(<RoleBadge role="college_admin" />);
      expect(screen.getByText("College Admin")).toBeInTheDocument();

      rerender(<RoleBadge role="college_staff" />);
      expect(screen.getByText("College Staff")).toBeInTheDocument();

      rerender(<RoleBadge role="verifier" />);
      expect(screen.getByText("Verifier")).toBeInTheDocument();
    });
  });

  describe("Button", () => {
    it("handles click events", () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click Me</Button>);

      fireEvent.click(screen.getByRole("button", { name: "Click Me" }));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("disables button and shows spinner when isLoading is true", () => {
      const handleClick = vi.fn();
      render(
        <Button isLoading loadingText="Submitting..." onClick={handleClick}>
          Submit
        </Button>
      );

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
      expect(screen.getByText("Submitting...")).toBeInTheDocument();

      fireEvent.click(button);
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe("Table", () => {
    it("renders table structure with headers and rows", () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Course Code</TableHead>
              <TableHead>Intake</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>COMP-101</TableCell>
              <TableCell>120</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByText("Course Code")).toBeInTheDocument();
      expect(screen.getByText("COMP-101")).toBeInTheDocument();
      expect(screen.getByText("120")).toBeInTheDocument();
    });
  });

  describe("EmptyState and ErrorState", () => {
    it("renders EmptyState and triggers action callback", () => {
      const onAction = vi.fn();
      render(
        <EmptyState
          title="No records found"
          description="There are currently no student records in draft."
          actionLabel="Add First Student"
          onAction={onAction}
        />
      );

      expect(screen.getByText("No records found")).toBeInTheDocument();
      expect(screen.getByText(/There are currently no student records/i)).toBeInTheDocument();

      const btn = screen.getByRole("button", { name: "Add First Student" });
      fireEvent.click(btn);
      expect(onAction).toHaveBeenCalledTimes(1);
    });

    it("renders ErrorState and triggers retry callback", () => {
      const onRetry = vi.fn();
      render(
        <ErrorState
          title="Validation Engine Error"
          message="Failed to compute anomaly clusters."
          onRetry={onRetry}
          retryLabel="Retry Computation"
        />
      );

      expect(screen.getByText("Validation Engine Error")).toBeInTheDocument();
      expect(screen.getByText("Failed to compute anomaly clusters.")).toBeInTheDocument();

      const btn = screen.getByRole("button", { name: "Retry Computation" });
      fireEvent.click(btn);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });
});
