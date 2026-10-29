import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardFooter,
  Accordion,
  Modal,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
  EmptyState,
  Spinner,
  Skeleton,
  Progress,
} from "../../components/ux4g";

describe("UX4G Content Components", () => {
  describe("Card", () => {
    it("renders card with header, title, body, and footer structure", () => {
      render(
        <Card variant="solid">
          <CardHeader>
            <CardTitle>Institution Profile</CardTitle>
          </CardHeader>
          <CardBody>
            <p>Approved intake: 120 seats</p>
          </CardBody>
          <CardFooter>
            <span>Updated today</span>
          </CardFooter>
        </Card>
      );

      expect(screen.getByText("Institution Profile")).toBeInTheDocument();
      expect(screen.getByText("Approved intake: 120 seats")).toBeInTheDocument();
      expect(screen.getByText("Updated today")).toBeInTheDocument();
    });
  });

  describe("Accordion", () => {
    it("renders collapsible sections and toggles aria-expanded on click", () => {
      render(
        <Accordion
          items={[
            { id: "item-1", title: "Intake Policy", content: <div>Intake details</div> },
            { id: "item-2", title: "Compliance Rules", content: <div>Rule details</div> },
          ]}
        />
      );

      const button1 = screen.getByRole("button", { name: "Intake Policy" });
      const button2 = screen.getByRole("button", { name: "Compliance Rules" });

      expect(button1).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByText("Intake details")).not.toBeInTheDocument();

      fireEvent.click(button1);
      expect(button1).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByText("Intake details")).toBeInTheDocument();

      fireEvent.click(button2);
      expect(button1).toHaveAttribute("aria-expanded", "false");
      expect(button2).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByText("Rule details")).toBeInTheDocument();
    });
  });

  describe("Modal / Dialog", () => {
    it("renders accessible dialog when isOpen is true and dismisses on close button and Escape key", () => {
      const handleClose = vi.fn();
      const { rerender } = render(
        <Modal isOpen={false} onClose={handleClose} title="Review Gate">
          Modal Content
        </Modal>
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

      rerender(
        <Modal isOpen={true} onClose={handleClose} title="Review Gate">
          Modal Content
        </Modal>
      );

      const dialog = screen.getByRole("dialog", { name: "Review Gate" });
      expect(dialog).toBeInTheDocument();
      expect(dialog).toHaveAttribute("aria-modal", "true");

      const closeButton = screen.getByRole("button", { name: "Close dialog" });
      fireEvent.click(closeButton);
      expect(handleClose).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(document, { key: "Escape" });
      expect(handleClose).toHaveBeenCalledTimes(2);
    });
  });

  describe("Table", () => {
    it("renders table with header, rows, sort direction on head, and caption", () => {
      render(
        <Table size="m" columnDividers zebra>
          <TableCaption>AICTE Seat Allotment Table</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead sortDirection="ascending">Course Name</TableHead>
              <TableHead>Approved Intake</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Computer Science & Engineering</TableCell>
              <TableCell>120</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const table = screen.getByRole("table");
      expect(table).toBeInTheDocument();

      const sortedHeader = screen.getByRole("columnheader", { name: "Course Name" });
      expect(sortedHeader).toHaveAttribute("aria-sort", "ascending");

      expect(screen.getByText("Computer Science & Engineering")).toBeInTheDocument();
      expect(screen.getByText("AICTE Seat Allotment Table")).toBeInTheDocument();
    });
  });

  describe("EmptyState", () => {
    it("renders empty state with status role and optional action", () => {
      const handleAction = vi.fn();
      render(
        <EmptyState
          title="No Flags Found"
          description="All student records passed automated validation."
          action={<button type="button" onClick={handleAction}>Upload More</button>}
        />
      );

      expect(screen.getByRole("status")).toBeInTheDocument();
      expect(screen.getByText("No Flags Found")).toBeInTheDocument();
      expect(screen.getByText("All student records passed automated validation.")).toBeInTheDocument();

      const actionBtn = screen.getByRole("button", { name: "Upload More" });
      fireEvent.click(actionBtn);
      expect(handleAction).toHaveBeenCalledTimes(1);
    });
  });

  describe("Spinner, Skeleton & Progress", () => {
    it("renders Spinner with status role and screen reader text", () => {
      render(<Spinner size="md" variant="primary" label="Verifying APAAR IDs..." />);
      const spinner = screen.getByRole("status");
      expect(spinner).toBeInTheDocument();
      expect(spinner.className).toContain("ux4g-spinner-primary-full");
      expect(screen.getByText("Verifying APAAR IDs...")).toBeInTheDocument();
    });

    it("renders Skeleton loader with pulse animation and loading role", () => {
      render(<Skeleton width={200} height={20} radius="m" />);
      const skeleton = screen.getByRole("status", { name: "Loading..." });
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveStyle({ width: "200px", height: "20px" });
    });

    it("renders Progress bar with aria attributes and percentage", () => {
      render(<Progress value={45} max={100} label="Upload Progress" showPercent />);
      const progressbar = screen.getByRole("progressbar", { name: "Upload Progress" });
      expect(progressbar).toBeInTheDocument();
      expect(progressbar).toHaveAttribute("aria-valuenow", "45");
      expect(progressbar).toHaveAttribute("aria-valuemin", "0");
      expect(progressbar).toHaveAttribute("aria-valuemax", "100");
      expect(screen.getByText("45%")).toBeInTheDocument();
    });
  });
});
