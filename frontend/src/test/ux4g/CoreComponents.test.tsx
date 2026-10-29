import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  Button,
  IconButton,
  Link,
  Icon,
  Badge,
  FlagBadge,
  RoleBadge,
  Tag,
  Alert,
  Toast,
  ToastProvider,
  useToast,
  Tooltip,
} from "../../components/ux4g";

describe("UX4G Core Components", () => {
  describe("Button & IconButton", () => {
    it("renders with mandatory base class, variant class, and size class", () => {
      render(<Button variant="primary" size="m">Click Me</Button>);
      const btn = screen.getByRole("button", { name: "Click Me" });
      expect(btn).toBeInTheDocument();
      // Design.md §2 & §12: base + variant + size
      expect(btn.className).toContain("ux4g-btn");
      expect(btn.className).toContain("ux4g-btn-primary");
      expect(btn.className).toContain("ux4g-btn-m");
    });

    it("handles keyboard click and trigger events", () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Action</Button>);
      const btn = screen.getByRole("button", { name: "Action" });
      btn.focus();
      expect(document.activeElement).toBe(btn);
      fireEvent.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("renders loading state with aria-busy and spinner", () => {
      render(<Button isLoading loadingText="Saving...">Save</Button>);
      const btn = screen.getByRole("button");
      expect(btn).toHaveAttribute("aria-busy", "true");
      expect(btn).toBeDisabled();
      expect(screen.getByText("Saving...")).toBeInTheDocument();
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("renders IconButton with accessible aria-label", () => {
      render(
        <IconButton
          icon={<Icon name="search" label="Search" />}
          aria-label="Search records"
          variant="primary"
          size="md"
        />
      );
      const btn = screen.getByRole("button", { name: "Search records" });
      expect(btn).toBeInTheDocument();
      expect(btn.className).toContain("ux4g-icon-btn");
      expect(btn.className).toContain("ux4g-icon-btn-primary");
    });
  });

  describe("Link", () => {
    it("renders text link with accessible name and sizing class", () => {
      render(
        <MemoryRouter>
          <Link to="/about" size="md">About EduTrace</Link>
        </MemoryRouter>
      );
      const link = screen.getByRole("link", { name: "About EduTrace" });
      expect(link).toBeInTheDocument();
      expect(link.className).toContain("ux4g-text-link-md");
      expect(link).toHaveAttribute("href", "/about");
    });

    it("renders external link with rel and target attributes", () => {
      render(
        <Link href="https://aicte-india.org" isExternal size="sm">
          AICTE Official
        </Link>
      );
      const link = screen.getByRole("link", { name: "AICTE Official" });
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  describe("Icon", () => {
    it("renders decorative icon with aria-hidden true", () => {
      render(<Icon name="school" />);
      const icon = screen.getByText("school");
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveAttribute("aria-hidden", "true");
      expect(icon.className).toContain("ux4g-icon");
      expect(icon.className).toContain("ux4g-icon-outlined");
    });

    it("renders informative icon with accessible aria-label and role img", () => {
      render(<Icon name="verified" label="AICTE Verified Record" color="success" />);
      const icon = screen.getByRole("img", { name: "AICTE Verified Record" });
      expect(icon).toBeInTheDocument();
      expect(icon.className).toContain("ux4g-icon-success");
    });
  });

  describe("Badge, FlagBadge & RoleBadge", () => {
    it("renders standard UX4G badge", () => {
      render(<Badge variant="primary">120</Badge>);
      const badge = screen.getByText("120");
      expect(badge.className).toContain("ux4g-badge");
      expect(badge.className).toContain("ux4g-badge-digit-primary");
    });

    it("renders all four SPEC §19 FlagBadge levels with accessible labels", () => {
      const { rerender } = render(<FlagBadge level="error" count={3} />);
      let badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("Error");
      expect(badge).toHaveTextContent("(3)");

      rerender(<FlagBadge level="exception" />);
      badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("Exception");

      rerender(<FlagBadge level="warning" />);
      badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("Warning");

      rerender(<FlagBadge level="info" label="Clean" />);
      badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("Clean");
    });

    it("renders RoleBadge for system roles", () => {
      render(<RoleBadge role="aicte_admin" />);
      expect(screen.getByText("AICTE Admin")).toBeInTheDocument();
    });
  });

  describe("Tag", () => {
    it("renders tag with variant and dismiss action", () => {
      const handleDismiss = vi.fn();
      render(
        <Tag variant="tonal" color="brand" onDismiss={handleDismiss} dismissLabel="Remove filter">
          B.Tech CSE
        </Tag>
      );
      expect(screen.getByText("B.Tech CSE")).toBeInTheDocument();
      const dismissBtn = screen.getByRole("button", { name: "Remove filter" });
      fireEvent.click(dismissBtn);
      expect(handleDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("Alert & Toast", () => {
    it("renders alert with accessible role and dismiss button", () => {
      const handleDismiss = vi.fn();
      render(
        <Alert variant="warning" title="Warning Header" onDismiss={handleDismiss}>
          Over-intake condition detected.
        </Alert>
      );
      const alert = screen.getByRole("alert");
      expect(alert).toBeInTheDocument();
      expect(alert.className).toContain("ux4g-alert-warning");
      expect(screen.getByText("Warning Header")).toBeInTheDocument();

      const dismissBtn = screen.getByRole("button", { name: "Dismiss alert" });
      fireEvent.click(dismissBtn);
      expect(handleDismiss).toHaveBeenCalledTimes(1);
    });

    it("renders standalone Toast component with dismiss action", () => {
      const handleClose = vi.fn();
      render(
        <Toast variant="info" title="Toast Notice" onClose={handleClose}>
          Record updated
        </Toast>
      );
      expect(screen.getByText("Toast Notice")).toBeInTheDocument();
      expect(screen.getByText("Record updated")).toBeInTheDocument();
      const closeBtn = screen.getByRole("button", { name: "Dismiss alert" });
      fireEvent.click(closeBtn);
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it("renders Toast message and auto-dismisses", async () => {
      function TestToastComponent() {
        const { addToast } = useToast();
        return (
          <button type="button" onClick={() => addToast({ message: "Saved!", duration: 100 })}>
            Trigger
          </button>
        );
      }

      render(
        <ToastProvider>
          <TestToastComponent />
        </ToastProvider>
      );

      fireEvent.click(screen.getByText("Trigger"));
      expect(screen.getByText("Saved!")).toBeInTheDocument();

      await waitFor(
        () => {
          expect(screen.queryByText("Saved!")).not.toBeInTheDocument();
        },
        { timeout: 1000 }
      );
    });
  });

  describe("Tooltip", () => {
    it("toggles tooltip visibility and updates aria-describedby on hover and focus", () => {
      render(
        <Tooltip content="Helper tooltip information" placement="top-center">
          <button type="button">Target Button</button>
        </Tooltip>
      );
      const trigger = screen.getByRole("button", { name: "Target Button" });
      expect(trigger).not.toHaveAttribute("aria-describedby");

      fireEvent.mouseEnter(trigger.parentElement!);
      expect(trigger).toHaveAttribute("aria-describedby");
      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toBeInTheDocument();
      expect(tooltip).toHaveTextContent("Helper tooltip information");

      fireEvent.mouseLeave(trigger.parentElement!);
      expect(trigger).not.toHaveAttribute("aria-describedby");
    });
  });
});
