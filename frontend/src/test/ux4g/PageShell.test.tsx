import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "../../auth/AuthContext";
import { PublicLayout } from "../../components/layout/PublicLayout";
import { AppLayout } from "../../components/layout/AppLayout";
import { SkipLink } from "../../components/layout/SkipLink";
import { UtilityBar } from "../../components/layout/UtilityBar";
import { Navbar } from "../../components/layout/Navbar";
import { PortalSidebar } from "../../components/layout/PortalSidebar";
import { Footer } from "../../components/layout/Footer";
import type { User } from "../../types/auth";

describe("UX4G Page Shell Architecture (R04)", () => {
  const mockLogout = vi.fn();

  const collegeUser: User = {
    id: 1,
    email: "admin@college.ac.in",
    role: "college_admin",
    institution_id: 101,
    is_active: true,
  };

  const aicteUser: User = {
    id: 2,
    email: "officer@aicte.gov.in",
    role: "aicte_officer",
    institution_id: null,
    is_active: true,
  };

  const renderWithAuth = (
    ui: React.ReactNode,
    user: User | null = null,
    initialPath = "/"
  ) => {
    return render(
      <AuthContext.Provider
        value={{
          user,
          token: user ? "mock-token" : null,
          isAuthenticated: !!user,
          isLoading: false,
          isAicte: user ? user.role.startsWith("aicte") : false,
          isCollege: user ? user.role.startsWith("college") : false,
          login: vi.fn(),
          logout: mockLogout,
          refreshUser: vi.fn(),
        }}
      >
        <MemoryRouter initialEntries={[initialPath]}>{ui}</MemoryRouter>
      </AuthContext.Provider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("SkipLink", () => {
    it("renders as accessible link targeting #main-content with screen-reader focusability", () => {
      render(
        <div>
          <SkipLink />
          <main id="main-content">
            <h1>Test Content</h1>
          </main>
        </div>
      );

      const skipLink = screen.getByRole("link", { name: "Skip to main content" });
      expect(skipLink).toBeInTheDocument();
      expect(skipLink).toHaveAttribute("href", "#main-content");
      expect(skipLink.className).toContain("sr-only");
      expect(skipLink.className).toContain("focus:not-sr-only");

      // Verify click smoothly focuses the main container
      const mainEl = document.getElementById("main-content")!;
      const focusSpy = vi.spyOn(mainEl, "focus");
      const scrollSpy = vi.fn();
      mainEl.scrollIntoView = scrollSpy;

      fireEvent.click(skipLink);
      expect(focusSpy).toHaveBeenCalled();
      expect(mainEl).toHaveAttribute("tabindex", "-1");
    });
  });

  describe("UtilityBar", () => {
    it("renders authority context, accessibility button, language switch, and login links when logged out", () => {
      const handleToggle = vi.fn();
      renderWithAuth(<UtilityBar onToggleAccessibility={handleToggle} />);

      // Authority context
      expect(screen.getByText(/All India Council for Technical Education/i)).toBeInTheDocument();
      expect(screen.getByText(/Ministry of Education, Govt. of India/i)).toBeInTheDocument();
      expect(screen.getByText("SIH 2026")).toBeInTheDocument();

      // Accessibility trigger
      const a11yBtn = screen.getByRole("button", { name: /Accessibility options/i });
      expect(a11yBtn).toBeInTheDocument();
      fireEvent.click(a11yBtn);
      expect(handleToggle).toHaveBeenCalledTimes(1);

      // Language switcher
      expect(screen.getByText("English")).toHaveAttribute("aria-current", "true");
      const hindiBtn = screen.getByRole("button", { name: "हिन्दी" });
      expect(hindiBtn).toBeDisabled();

      // Unauthenticated actions
      expect(screen.getByRole("link", { name: "College Login" })).toHaveAttribute("href", "/login/college");
      expect(screen.getByRole("link", { name: "AICTE Login" })).toHaveAttribute("href", "/login/aicte");
    });

    it("renders user email, role badge, and sign out button when logged in", () => {
      renderWithAuth(<UtilityBar />, collegeUser);

      expect(screen.getByText(collegeUser.email)).toBeInTheDocument();
      expect(screen.getByText("College Admin")).toBeInTheDocument();

      const signOutBtn = screen.getByRole("button", { name: "Sign out" });
      expect(signOutBtn).toBeInTheDocument();
      fireEvent.click(signOutBtn);
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });

  describe("Navbar", () => {
    it("renders brand wordmark linking home and public navigation links", () => {
      renderWithAuth(<Navbar />);

      const homeLink = screen.getByRole("link", { name: /EduTrace.*Central Portal/i });
      expect(homeLink).toHaveAttribute("href", "/");

      expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Activate College" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Verify Record" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Student Portal" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Privacy & DPDP" })).toBeInTheDocument();
    });

    it("renders mobile menu button and opens mobile menu with aria-expanded", () => {
      renderWithAuth(<Navbar />);

      const menuToggle = screen.getByRole("button", { name: "Toggle navigation menu" });
      expect(menuToggle).toHaveAttribute("aria-expanded", "false");

      fireEvent.click(menuToggle);
      expect(menuToggle).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("PortalSidebar", () => {
    it("renders college navigation items following SPEC §19", () => {
      renderWithAuth(<PortalSidebar />, collegeUser, "/college/seats");

      const sidebar = screen.getByRole("navigation", { name: "Portal Sidebar Navigation" });
      expect(sidebar).toBeInTheDocument();

      // Verify SPEC §19 college items
      expect(screen.getAllByRole("link", { name: /Dashboard/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Seats & Intake/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Students/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Add Student/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Bulk Upload/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Validation Flags/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Submit Data/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Queries/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Change Requests/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Staff/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /API Keys/i }).length).toBeGreaterThan(0);

      // Verify active link state
      const seatsLink = screen.getAllByRole("link", { name: /Seats & Intake/i })[0];
      expect(seatsLink).toHaveAttribute("aria-current", "page");
    });

    it("renders AICTE navigation items following SPEC §19", () => {
      renderWithAuth(<PortalSidebar />, aicteUser, "/aicte/overview");

      const sidebar = screen.getByRole("navigation", { name: "Portal Sidebar Navigation" });
      expect(sidebar).toBeInTheDocument();

      // Verify SPEC §19 AICTE items
      expect(screen.getAllByRole("link", { name: /Overview/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Approvals Queue/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Review Queue/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Intake Control/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Compliance & Over-Intake/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Duplicates/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Anomaly Detection/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Drill-Down Explorer/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Verifiers/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Rule Configuration/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Reports & Exports/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: /Audit Log Chain/i }).length).toBeGreaterThan(0);

      const overviewLink = screen.getAllByRole("link", { name: /Overview/i })[0];
      expect(overviewLink).toHaveAttribute("aria-current", "page");
    });
  });

  describe("Footer", () => {
    it("renders landmark footer with mandatory demo-mode notice, grievance contact, and secondary links", () => {
      renderWithAuth(<Footer />);

      const footer = screen.getByRole("contentinfo", { name: "Site Footer" });
      expect(footer).toBeInTheDocument();

      // SPEC §2 Rule 10 mandatory disclaimer text
      expect(
        screen.getByText(/Demo mode: APAAR registry is simulated\. EduTrace is a prototype and not an official government service\./i)
      ).toBeInTheDocument();

      // Grievance contact
      expect(screen.getByText(/grievance@edutrace\.ac\.in/i)).toBeInTheDocument();
      expect(screen.getByText(/support@edutrace\.ac\.in/i)).toBeInTheDocument();

      // Secondary links
      expect(screen.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute("href", "/privacy");
      expect(screen.getByRole("link", { name: "Terms of Service" })).toHaveAttribute("href", "/terms");
      expect(screen.getByRole("link", { name: "Accessibility Statement" })).toHaveAttribute("href", "/accessibility");
      expect(screen.getByRole("link", { name: "Help & Glossary" })).toHaveAttribute("href", "/help");

      // Verify no "Powered by NeGD" text exists per task specification
      expect(screen.queryByText(/Powered by NeGD/i)).not.toBeInTheDocument();
    });
  });

  describe("Full Page Shell Landmark Hierarchy", () => {
    it("PublicLayout renders sequential landmarks: skip link, header, main, footer without shell h1", () => {
      const { container } = renderWithAuth(
        <PublicLayout>
          <h1>Sample Public Page Title</h1>
          <p>Page description paragraph.</p>
        </PublicLayout>
      );

      // Landmarks
      expect(container.querySelector("header")).toBeInTheDocument();
      expect(container.querySelector("nav")).toBeInTheDocument();
      expect(container.querySelector("main#main-content")).toBeInTheDocument();
      expect(container.querySelector("footer")).toBeInTheDocument();

      // Single h1 rule
      const headings = screen.getAllByRole("heading", { level: 1 });
      expect(headings).toHaveLength(1);
      expect(headings[0]).toHaveTextContent("Sample Public Page Title");

      // Skip link is the very first interactive link element
      const allLinks = screen.getAllByRole("link");
      expect(allLinks[0]).toHaveTextContent("Skip to main content");
      expect(allLinks[0]).toHaveAttribute("href", "#main-content");
    });

    it("AppLayout renders sequential landmarks: skip link, header, sidebar nav, main, footer", () => {
      const { container } = renderWithAuth(
        <AppLayout>
          <h1>Institution Dashboard</h1>
          <p>Dashboard main content.</p>
        </AppLayout>,
        collegeUser,
        "/college/dashboard"
      );

      // Landmarks
      expect(container.querySelector("header")).toBeInTheDocument();
      expect(screen.getByRole("navigation", { name: "Portal Sidebar Navigation" })).toBeInTheDocument();
      expect(container.querySelector("main#main-content")).toBeInTheDocument();
      expect(container.querySelector("footer")).toBeInTheDocument();

      // Single h1 rule
      const headings = screen.getAllByRole("heading", { level: 1 });
      expect(headings).toHaveLength(1);
      expect(headings[0]).toHaveTextContent("Institution Dashboard");
    });
  });
});
