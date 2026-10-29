import React from "react";
import { SkipLink } from "./SkipLink";
import { UtilityBar } from "./UtilityBar";
import { Navbar } from "./Navbar";
import { PortalSidebar } from "./PortalSidebar";
import { Footer } from "./Footer";

export interface AppLayoutProps {
  children?: React.ReactNode;
}

/**
 * UX4G Authenticated Application Layout Shell
 *
 * Implements SPEC §19 and Task R04:
 * - Skip link as the first focusable element, landing on main.
 * - Header landmark with top utility bar and main navbar.
 * - Role-aware Sidebar navigation for College, AICTE, and Verifier portals.
 * - Mobile responsive navigation menu collapsing on screens < 1024px.
 * - Single main landmark for page content with focus management.
 * - Standardized footer with demo mode disclaimer and secondary links.
 */
export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col ux4g-bg-neutral-default ux4g-text-neutral-primary font-sans">
      <SkipLink targetId="main-content" />
      <header className="w-full">
        <UtilityBar />
        <Navbar />
      </header>
      <div className="flex-1 flex flex-col lg:flex-row w-full">
        <PortalSidebar />
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 focus:outline-none overflow-x-hidden"
        >
          {children}
        </main>
      </div>
      <Footer />
    </div>
  );
}
