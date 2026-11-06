
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
  TableEmptyState,
  TableSkeletonRows,
  TableError,
  TablePagination,
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

    it("renders scrollable region with role, aria-label, and tabIndex for mobile responsiveness", () => {
      render(
        <Table ariaLabel="Enrolment Records" stickyHeader maxHeight="400px">
          <TableHeader sticky>
            <TableRow>
              <TableHead>ID</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>1</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const region = screen.getByRole("region", { name: "Enrolment Records" });
      expect(region).toBeInTheDocument();
      expect(region).toHaveAttribute("tabindex", "0");
      expect(region.className).toContain("overflow-x-auto");
      expect(region.className).toContain("overflow-y-auto");
    });

    it("handles sortable column header interactions with click and keyboard", () => {
      const handleSort = vi.fn();
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead
                sortable
                sortDirection="descending"
                onSort={handleSort}
              >
                Student Name
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Aaditya</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const sortBtn = screen.getByRole("button", { name: /Student Name, sort none/i });
      expect(sortBtn).toBeInTheDocument();

      fireEvent.click(sortBtn);
      expect(handleSort).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(sortBtn, { key: "Enter" });
      expect(handleSort).toHaveBeenCalledTimes(2);

      fireEvent.keyDown(sortBtn, { key: " " });
      expect(handleSort).toHaveBeenCalledTimes(3);
    });

    it("renders focusable and selectable table rows", () => {
      render(
        <Table>
          <TableBody>
            <TableRow focusable selected data-testid="test-row">
              <TableCell>Focused Row</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const row = screen.getByTestId("test-row");
      expect(row).toHaveAttribute("tabindex", "0");
      expect(row).toHaveAttribute("aria-selected", "true");
    });

    it("renders TableEmptyState spanning columns", () => {
      render(
        <Table>
          <TableBody>
            <TableEmptyState
              colSpan={5}
              title="No Students Uploaded"
              description="Upload a CSV to view rows here."
            />
          </TableBody>
        </Table>
      );

      expect(screen.getByText("No Students Uploaded")).toBeInTheDocument();
      expect(screen.getByText("Upload a CSV to view rows here.")).toBeInTheDocument();
    });

    it("renders TableSkeletonRows with specified columns and rows", () => {
      const { container } = render(
        <Table>
          <TableBody>
            <TableSkeletonRows columns={4} rows={3} />
          </TableBody>
        </Table>
      );

      const trs = container.querySelectorAll("tbody tr");
      expect(trs.length).toBe(3);
      const cells = container.querySelectorAll("tbody td");
      expect(cells.length).toBe(12);
    });

    it("renders TableError state with retry button", () => {
      const handleRetry = vi.fn();
      render(
        <Table>
          <TableBody>
            <TableError
              colSpan={4}
              title="Network Error"
              message="Failed to fetch records from registry."
              onRetry={handleRetry}
              retryLabel="Retry loading"
            />
          </TableBody>
        </Table>
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Network Error")).toBeInTheDocument();
      expect(screen.getByText("Failed to fetch records from registry.")).toBeInTheDocument();

      const retryBtn = screen.getByRole("button", { name: "Retry loading" });
      fireEvent.click(retryBtn);
      expect(handleRetry).toHaveBeenCalledTimes(1);
    });

    it("renders TablePagination with record counts, page size, and page navigation", () => {
      const handlePageChange = vi.fn();
      const handlePageSizeChange = vi.fn();

      render(
        <TablePagination
          currentPage={2}
          totalPages={5}
          totalItems={100}
          pageSize={20}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
          ariaLabel="Test table pagination"
        />
      );

      expect(screen.getByText(/Showing/i)).toBeInTheDocument();
      expect(screen.getByText("21")).toBeInTheDocument();
      expect(screen.getByText("40")).toBeInTheDocument();
      expect(screen.getAllByText("100").length).toBeGreaterThanOrEqual(1);

      const sizeSelect = screen.getByLabelText("Rows per page:");
      fireEvent.change(sizeSelect, { target: { value: "50" } });
      expect(handlePageSizeChange).toHaveBeenCalledWith(50);

      const nextBtn = screen.getByRole("button", { name: "Next page" });
      fireEvent.click(nextBtn);
      expect(handlePageChange).toHaveBeenCalledWith(3);
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
