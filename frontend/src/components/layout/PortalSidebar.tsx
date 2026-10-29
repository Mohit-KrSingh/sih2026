import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Icon } from "../ux4g/Icon";

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: string;
  badge?: React.ReactNode;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

export interface PortalSidebarProps {
  className?: string;
}

/**
 * PortalSidebar Component
 *
 * Implements SPEC §19 role-specific navigation for College, AICTE, and Verifier portals.
 * - Desktop: Semantic `<nav aria-label="Portal Sidebar Navigation">`
 * - Mobile: Collapses into an expandable menu below 1024px.
 * - Semantic tokens and UX4G active states.
 */
export const PortalSidebar: React.FC<PortalSidebarProps> = ({ className = "" }) => {
  const { user, isAicte, isCollege } = useAuth();
  const location = useLocation();
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  const collegeSections: NavSection[] = [
    {
      title: "Academic Data",
      items: [
        { id: "dashboard", label: "Dashboard", path: "/college/dashboard", icon: "dashboard" },
        { id: "seats", label: "Seats & Intake", path: "/college/seats", icon: "domain" },
        { id: "students", label: "Students", path: "/college/students", icon: "group" },
        { id: "add-student", label: "Add Student", path: "/college/students/new", icon: "person_add" },
        { id: "upload", label: "Bulk Upload", path: "/college/upload", icon: "upload_file" },
      ],
    },
    {
      title: "Compliance & Submit",
      items: [
        { id: "validation", label: "Validation Flags", path: "/college/validation", icon: "warning" },
        { id: "submit", label: "Submit Data", path: "/college/submit", icon: "task_alt" },
        { id: "queries", label: "Queries", path: "/college/queries", icon: "help" },
        { id: "change-requests", label: "Change Requests", path: "/college/change-requests", icon: "assignment" },
      ],
    },
    {
      title: "Administration",
      items: [
        { id: "staff", label: "Staff", path: "/college/staff", icon: "badge" },
        { id: "api-keys", label: "API Keys", path: "/college/api-keys", icon: "key" },
      ],
    },
  ];

  const aicteSections: NavSection[] = [
    {
      title: "Oversight & Review",
      items: [
        { id: "overview", label: "Overview", path: "/aicte/overview", icon: "dashboard" },
        { id: "approvals", label: "Approvals Queue", path: "/aicte/approvals", icon: "how_to_reg" },
        { id: "review", label: "Review Queue", path: "/aicte/review", icon: "rate_review" },
        { id: "change-requests", label: "Change Requests", path: "/aicte/change-requests", icon: "assignment" },
      ],
    },
    {
      title: "Compliance Monitoring",
      items: [
        { id: "intake", label: "Intake Control", path: "/aicte/intake", icon: "domain" },
        { id: "compliance", label: "Compliance & Over-Intake", path: "/aicte/compliance", icon: "gavel" },
        { id: "duplicates", label: "Duplicates", path: "/aicte/duplicates", icon: "content_copy" },
        { id: "anomalies", label: "Anomaly Detection", path: "/aicte/anomalies", icon: "crisis_alert" },
        { id: "explore", label: "Drill-Down Explorer", path: "/aicte/explore", icon: "explore" },
      ],
    },
    {
      title: "Registry & Governance",
      items: [
        { id: "verifiers", label: "Verifiers", path: "/aicte/verifiers", icon: "verified_user" },
        { id: "rules", label: "Rule Configuration", path: "/aicte/rules", icon: "tune" },
        { id: "reports", label: "Reports & Exports", path: "/aicte/reports", icon: "analytics" },
        { id: "audit", label: "Audit Log Chain", path: "/aicte/audit", icon: "history" },
      ],
    },
  ];

  const verifierSections: NavSection[] = [
    {
      title: "Verification Portal",
      items: [
        { id: "search", label: "Search & Request Consent", path: "/verifier/search", icon: "search" },
        { id: "history", label: "Consent History", path: "/verifier/history", icon: "history" },
      ],
    },
  ];

  const sections = isAicte
    ? aicteSections
    : isCollege
    ? collegeSections
    : user?.role === "verifier"
    ? verifierSections
    : [];

  if (sections.length === 0) {
    return null;
  }

  const allItems = sections.flatMap((s) => s.items);
  const isItemActive = (path: string) => {
    const isExact = location.pathname === path;
    const isPrefix =
      path !== "/college/dashboard" &&
      path !== "/aicte/overview" &&
      path !== "/verifier/search" &&
      location.pathname.startsWith(path);
    return isExact || isPrefix;
  };

  const activeItem = allItems.find((item) => isItemActive(item.path));

  return (
    <>
      {/* Mobile Drawer Toggle Toolbar */}
      <div className="lg:hidden w-full border-b ux4g-border-neutral-subtle ux4g-bg-neutral-soft p-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider ux4g-text-neutral-tertiary">
            Portal Menu
          </span>
          {activeItem && (
            <span className="text-xs font-semibold ux4g-text-neutral-primary">
              &bull; {activeItem.label}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setMobileDrawerOpen(!mobileDrawerOpen)}
          aria-expanded={mobileDrawerOpen}
          aria-label="Toggle sidebar navigation menu"
          className="ux4g-btn ux4g-btn-outline-primary ux4g-btn-s flex items-center gap-1.5"
        >
          <Icon name={mobileDrawerOpen ? "close" : "menu"} size="xs" aria-hidden="true" />
          <span>{mobileDrawerOpen ? "Close" : "Navigation"}</span>
        </button>
      </div>

      {/* Mobile Navigation Dropdown */}
      {mobileDrawerOpen && (
        <div className="lg:hidden w-full border-b ux4g-border-neutral-subtle ux4g-bg-neutral-elevated p-4 space-y-4 shadow-sm">
          {sections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              {section.title && (
                <div className="text-[11px] font-bold uppercase tracking-wider ux4g-text-neutral-tertiary px-3 mb-1">
                  {section.title}
                </div>
              )}
              <ul className="space-y-1">
                {section.items.map((item) => {
                  const active = isItemActive(item.path);
                  return (
                    <li key={item.id}>
                      <Link
                        to={item.path}
                        onClick={() => setMobileDrawerOpen(false)}
                        aria-current={active ? "page" : undefined}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                          active
                            ? "ux4g-bg-primary-soft ux4g-text-brand-primary font-bold border-l-4 ux4g-border-primary"
                            : "ux4g-text-neutral-secondary hover:ux4g-bg-neutral-soft hover:ux4g-text-neutral-primary"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon
                            name={item.icon}
                            size="sm"
                            color={active ? "primary" : "neutral"}
                            aria-hidden="true"
                          />
                          <span>{item.label}</span>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Desktop Persistent Sidebar */}
      <nav
        aria-label="Portal Sidebar Navigation"
        className={`w-64 shrink-0 hidden lg:block border-r ux4g-border-neutral-subtle ux4g-bg-neutral-elevated min-h-[calc(100vh-8rem)] p-4 ${className}`.trim()}
      >
        <div className="flex flex-col gap-6">
          {/* User profile strip inside sidebar */}
          {user && (
            <div className="p-3 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs text-white shrink-0 ux4g-bg-primary-strong">
                  {user.email.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1 leading-tight">
                  <p className="text-xs font-semibold ux4g-text-neutral-primary truncate" title={user.email}>
                    {user.email}
                  </p>
                  {user.institution_id && (
                    <p className="text-[10px] ux4g-text-neutral-secondary font-mono truncate">
                      ID: {user.institution_id}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Section groups */}
          {sections.map((section, sIdx) => (
            <div key={sIdx} className="flex flex-col gap-1.5">
              {section.title && (
                <div className="px-3 text-[11px] font-bold uppercase tracking-wider ux4g-text-neutral-tertiary mb-1">
                  {section.title}
                </div>
              )}
              <ul className="space-y-1">
                {section.items.map((item) => {
                  const active = isItemActive(item.path);
                  return (
                    <li key={item.id}>
                      <Link
                        to={item.path}
                        aria-current={active ? "page" : undefined}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                          active
                            ? "ux4g-bg-primary-soft ux4g-text-brand-primary font-bold border-l-4 ux4g-border-primary"
                            : "ux4g-text-neutral-secondary hover:ux4g-bg-neutral-soft hover:ux4g-text-neutral-primary"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 truncate">
                          <Icon
                            name={item.icon}
                            size="sm"
                            color={active ? "primary" : "neutral"}
                            aria-hidden="true"
                          />
                          <span className="truncate">{item.label}</span>
                        </div>
                        {item.badge && <span className="ml-2 shrink-0">{item.badge}</span>}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>
    </>
  );
};
