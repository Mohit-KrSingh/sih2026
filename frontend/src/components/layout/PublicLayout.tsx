import React from "react";
import { SkipLink } from "./SkipLink";
import { UtilityBar } from "./UtilityBar";
import { Navbar } from "./Navbar";
import { Footer } from "./Footer";

export interface PublicLayoutProps {
  children?: React.ReactNode;
}

/**
 * UX4G Public Page Layout Shell
 *
 * Implements SPEC §19 and Task R04:
 * - Skip link as the first focusable element, landing on main.
 * - Header landmark with top utility bar and main navigation.
 * - Single main landmark for page content with focus management.
 * - Accessible footer landmark with demo mode notice and secondary links.
 */
export function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col ux4g-bg-neutral-default ux4g-text-neutral-primary font-sans">
      <SkipLink targetId="main-content" />
      <header className="w-full">
        <UtilityBar />
        <Navbar />
      </header>
      <main
        id="main-content"
        tabIndex={-1}
        className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 focus:outline-none"
      >
        {children}
      </main>
      <Footer />
    </div>
  );
}
