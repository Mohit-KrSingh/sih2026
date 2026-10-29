import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { PRODUCT_NAME } from "../../brand";
import { EduTraceIcon } from "../brand/EduTraceLogo";
import { Icon } from "../ux4g/Icon";
import { Button } from "../ux4g/Button";

export interface NavbarProps {
  className?: string;
}

/**
 * UX4G Main Header & Navigation Bar
 *
 * Implements SPEC §19 and REBRAND_TASKS.md R04:
 * - EduTrace wordmark linking home.
 * - Role-aware navigation structure.
 * - Accessible mobile collapsible navigation menu.
 * - Semantic landmarks and keyboard operability.
 */
export const Navbar: React.FC<NavbarProps> = ({ className = "" }) => {
  const { user, isAuthenticated, isAicte, isCollege, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const dashboardPath = isAicte
    ? "/aicte/overview"
    : isCollege
    ? "/college/dashboard"
    : user?.role === "verifier"
    ? "/verifier/search"
    : "/";

  const portalLabel = isAicte
    ? "AICTE Central Portal"
    : isCollege
    ? "College Portal"
    : user?.role === "verifier"
    ? "Verifier Portal"
    : "Central Portal";

  return (
    <nav
      role="navigation"
      aria-label="Main Navigation"
      className={`ux4g-navbar w-full border-b ux4g-border-neutral-subtle ux4g-bg-neutral-elevated ${className}`.trim()}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        {/* Brand & Wordmark */}
        <Link
          to="/"
          className="flex items-center gap-3 group focus:outline focus:outline-2"
          style={{ outlineColor: "var(--edutrace-focus-outline)" }}
        >
          <div className="w-10 h-10 rounded-lg flex items-center justify-center text-white shadow-sm shrink-0 ux4g-bg-primary-strong">
            <EduTraceIcon size={22} className="text-white" />
          </div>
          <div className="leading-tight">
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight ux4g-text-neutral-primary">
                {PRODUCT_NAME}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded font-semibold ux4g-bg-primary-soft ux4g-text-brand-primary border ux4g-border-neutral-subtle">
                {portalLabel}
              </span>
            </div>
            <p className="text-[11px] ux4g-text-neutral-secondary font-medium">
              Student Data Management & Verification System
            </p>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <div className="hidden md:flex items-center gap-1 lg:gap-2">
          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <Link
                to={dashboardPath}
                className="px-3 py-1.5 rounded-md text-sm font-medium transition-colors ux4g-text-brand-primary ux4g-bg-primary-soft hover:underline"
              >
                Dashboard
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-1 lg:gap-2 text-sm font-medium">
              <Link
                to="/"
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  isActive("/")
                    ? "ux4g-text-brand-primary font-semibold border-b-2 ux4g-border-primary"
                    : "ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
                }`}
                aria-current={isActive("/") ? "page" : undefined}
              >
                Home
              </Link>
              <Link
                to="/activate"
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  isActive("/activate")
                    ? "ux4g-text-brand-primary font-semibold border-b-2 ux4g-border-primary"
                    : "ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
                }`}
                aria-current={isActive("/activate") ? "page" : undefined}
              >
                Activate College
              </Link>
              <Link
                to="/verify"
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  isActive("/verify")
                    ? "ux4g-text-brand-primary font-semibold border-b-2 ux4g-border-primary"
                    : "ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
                }`}
                aria-current={isActive("/verify") ? "page" : undefined}
              >
                Verify Record
              </Link>
              <Link
                to="/student"
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  isActive("/student")
                    ? "ux4g-text-brand-primary font-semibold border-b-2 ux4g-border-primary"
                    : "ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
                }`}
                aria-current={isActive("/student") ? "page" : undefined}
              >
                Student Portal
              </Link>
              <Link
                to="/privacy"
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  isActive("/privacy")
                    ? "ux4g-text-brand-primary font-semibold border-b-2 ux4g-border-primary"
                    : "ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
                }`}
                aria-current={isActive("/privacy") ? "page" : undefined}
              >
                Privacy & DPDP
              </Link>
            </div>
          )}
        </div>

        {/* Right Action Area */}
        <div className="hidden md:flex items-center gap-3">
          {!isAuthenticated && (
            <div className="flex items-center gap-2">
              <Link to="/login/college">
                <Button variant="outline-primary" size="s">
                  College Login
                </Button>
              </Link>
              <Link to="/login/aicte">
                <Button variant="primary" size="s">
                  AICTE Login
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* Mobile menu toggle button */}
        <div className="flex md:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-md flex items-center justify-center ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft focus:outline focus:outline-2"
            style={{ outlineColor: "var(--edutrace-focus-outline)" }}
          >
            <Icon name={mobileMenuOpen ? "close" : "menu"} size="md" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Mobile Collapsed Navigation Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t ux4g-border-neutral-subtle ux4g-bg-neutral-elevated px-4 py-4 space-y-3">
          <div className="flex flex-col space-y-2">
            <Link
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 min-h-[44px] flex items-center rounded-md text-sm font-medium ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
            >
              Home
            </Link>
            <Link
              to="/activate"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 min-h-[44px] flex items-center rounded-md text-sm font-medium ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
            >
              Activate College
            </Link>
            <Link
              to="/verify"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 min-h-[44px] flex items-center rounded-md text-sm font-medium ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
            >
              Verify Record
            </Link>
            <Link
              to="/student"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 min-h-[44px] flex items-center rounded-md text-sm font-medium ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
            >
              Student Portal
            </Link>
            <Link
              to="/privacy"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 min-h-[44px] flex items-center rounded-md text-sm font-medium ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
            >
              Privacy & DPDP
            </Link>
          </div>

          <div className="pt-3 border-t ux4g-border-neutral-subtle">
            {isAuthenticated && user ? (
              <div className="space-y-2">
                <Link
                  to={dashboardPath}
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-center w-full py-2 rounded font-medium text-sm text-white ux4g-bg-primary-strong"
                >
                  Go to Dashboard
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="block text-center w-full py-2 rounded font-medium text-sm ux4g-text-neutral-primary ux4g-bg-neutral-subtle"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Link
                  to="/login/college"
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-center py-2 px-3 rounded text-xs font-semibold border ux4g-border-neutral-default ux4g-text-neutral-primary"
                >
                  College Login
                </Link>
                <Link
                  to="/login/aicte"
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-center py-2 px-3 rounded text-xs font-semibold text-white ux4g-bg-primary-strong"
                >
                  AICTE Login
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};
