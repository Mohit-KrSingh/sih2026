import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  Navbar,
  Sidebar,
  Breadcrumb,
  Tabs,
  Stepper,
  Pagination,
  Footer,
} from "../../components/ux4g";

describe("UX4G Navigation Components", () => {
  describe("Navbar", () => {
    it("renders navigation bar with brand, links, and right action area", () => {
      render(
        <MemoryRouter>
          <Navbar
            brand={<span>EduTrace Logo</span>}
            items={[
              { label: "Dashboard", href: "/dashboard", active: true },
              { label: "Verification", href: "/verify" },
            ]}
            rightContent={<button type="button">Sign In</button>}
          />
        </MemoryRouter>
      );

      const nav = screen.getByRole("navigation", { name: "Main Navigation" });
      expect(nav).toBeInTheDocument();
      expect(screen.getByText("EduTrace Logo")).toBeInTheDocument();

      const activeLink = screen.getByRole("link", { name: "Dashboard" });
      expect(activeLink).toHaveAttribute("aria-current", "page");

      expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
    });
  });

  describe("Sidebar", () => {
    it("renders semantic navigation landmark with sections and links", () => {
      render(
        <MemoryRouter>
          <Sidebar
            ariaLabel="College Navigation"
            sections={[
              {
                title: "Academic Data",
                items: [
                  { id: "seats", label: "Seat Declarations", href: "/college/seats", active: true },
                  { id: "students", label: "Student List", href: "/college/students" },
                ],
              },
            ]}
          />
        </MemoryRouter>
      );

      const aside = screen.getByRole("navigation", { name: "College Navigation" });
      expect(aside).toBeInTheDocument();
      expect(screen.getByText("Academic Data")).toBeInTheDocument();

      const activeLink = screen.getByRole("link", { name: /Seat Declarations/ });
      expect(activeLink).toHaveAttribute("aria-current", "page");
    });
  });

  describe("Breadcrumb", () => {
    it("renders ordered list of breadcrumb items with last marked aria-current page", () => {
      render(
        <MemoryRouter>
          <Breadcrumb
            items={[
              { label: "Home", href: "/" },
              { label: "AICTE Portal", href: "/aicte" },
              { label: "Compliance Red List" },
            ]}
          />
        </MemoryRouter>
      );

      const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
      expect(nav).toBeInTheDocument();

      expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "AICTE Portal" })).toBeInTheDocument();

      const currentPage = screen.getByText("Compliance Red List");
      expect(currentPage).toHaveAttribute("aria-current", "page");
    });
  });

  describe("Tabs", () => {
    it("renders tablist with tab items and tabpanel", () => {
      render(
        <Tabs
          items={[
            { id: "t1", label: "Overview", content: <div>Overview Content</div> },
            { id: "t2", label: "Anomalies", content: <div>Anomalies Content</div> },
          ]}
        />
      );

      const tablist = screen.getByRole("tablist");
      expect(tablist).toBeInTheDocument();

      const tab1 = screen.getByRole("tab", { name: "Overview" });
      const tab2 = screen.getByRole("tab", { name: "Anomalies" });
      expect(tab1).toHaveAttribute("aria-selected", "true");
      expect(tab2).toHaveAttribute("aria-selected", "false");

      expect(screen.getByText("Overview Content")).toBeInTheDocument();

      fireEvent.click(tab2);
      expect(tab1).toHaveAttribute("aria-selected", "false");
      expect(tab2).toHaveAttribute("aria-selected", "true");
      expect(screen.getByText("Anomalies Content")).toBeInTheDocument();
    });

    it("supports keyboard arrow navigation between tabs", () => {
      render(
        <Tabs
          items={[
            { id: "t1", label: "Tab 1", content: <div>Panel 1</div> },
            { id: "t2", label: "Tab 2", content: <div>Panel 2</div> },
          ]}
        />
      );

      const tab1 = screen.getByRole("tab", { name: "Tab 1" });
      const tab2 = screen.getByRole("tab", { name: "Tab 2" });

      tab1.focus();
      fireEvent.keyDown(tab1, { key: "ArrowRight" });
      expect(tab2).toHaveAttribute("aria-selected", "true");
      expect(screen.getByText("Panel 2")).toBeInTheDocument();

      fireEvent.keyDown(tab2, { key: "ArrowLeft" });
      expect(tab1).toHaveAttribute("aria-selected", "true");
      expect(screen.getByText("Panel 1")).toBeInTheDocument();
    });
  });

  describe("Stepper", () => {
    it("renders stepper with current, completed, and upcoming step indicators", () => {
      render(
        <Stepper
          currentStep={1}
          steps={[
            { title: "Activation", description: "Institution Claim" },
            { title: "Verification", description: "OTP Validation" },
            { title: "Submission", description: "Final Review" },
          ]}
        />
      );

      const stepper = screen.getByRole("navigation", { name: "Progress Stepper" });
      expect(stepper).toBeInTheDocument();

      // Current step has aria-current="step"
      const stepItems = screen.getAllByRole("listitem");
      expect(stepItems[1]).toHaveAttribute("aria-current", "step");
      expect(stepItems[0]).not.toHaveAttribute("aria-current");
      expect(stepItems[2]).not.toHaveAttribute("aria-current");
    });
  });

  describe("Pagination", () => {
    it("renders pagination controls and triggers page change callbacks", () => {
      const handlePageChange = vi.fn();
      render(
        <Pagination currentPage={2} totalPages={5} onPageChange={handlePageChange} />
      );

      const prevBtn = screen.getByRole("button", { name: "Previous page" });
      const nextBtn = screen.getByRole("button", { name: "Next page" });
      const activePage = screen.getByRole("button", { name: "Page 2" });

      expect(activePage).toHaveAttribute("aria-current", "page");

      fireEvent.click(nextBtn);
      expect(handlePageChange).toHaveBeenCalledWith(3);

      fireEvent.click(prevBtn);
      expect(handlePageChange).toHaveBeenCalledWith(1);
    });
  });

  describe("Footer", () => {
    it("renders landmark footer with demo mode disclaimer and secondary links", () => {
      render(
        <MemoryRouter>
          <Footer />
        </MemoryRouter>
      );

      const footer = screen.getByRole("contentinfo");
      expect(footer).toBeInTheDocument();
      // SPEC §2 Rule 10 mandatory disclaimer check
      expect(screen.getByText(/Demo mode: APAAR registry is simulated/i)).toBeInTheDocument();

      expect(screen.getByRole("link", { name: "Privacy Policy" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Accessibility Statement" })).toBeInTheDocument();
    });
  });
});
