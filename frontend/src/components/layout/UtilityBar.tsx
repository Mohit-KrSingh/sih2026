import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { useAccessibility } from "../../context/accessibilityUtils";
import { RoleBadge } from "../ux4g/Badge";
import { Icon } from "../ux4g/Icon";

export interface UtilityBarProps {
  onToggleAccessibility?: () => void;
  className?: string;
}

/**
 * UX4G Top Utility Bar
 *
 * Micro-header component rendering:
 * 1. Authority Context: AICTE & Ministry of Education, Govt. of India banner.
 * 2. Accessibility Tools trigger button (for R05 panel).
 * 3. Language switch (English default; Hindi stretch goal per R13).
 * 4. User authentication state and session controls.
 */
export const UtilityBar: React.FC<UtilityBarProps> = ({
  onToggleAccessibility,
  className = "",
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const { togglePanel, isPanelOpen } = useAccessibility();

  const handleToggleA11y = () => {
    if (onToggleAccessibility) {
      onToggleAccessibility();
    } else {
      togglePanel();
    }
  };

  return (
    <div
      role="region"
      aria-label="Top Utility and Accessibility Bar"
      className={`w-full border-b ux4g-border-neutral-subtle ux4g-bg-neutral-soft ux4g-text-neutral-secondary text-xs py-1.5 px-4 sm:px-6 lg:px-8 ${className}`.trim()}
    >
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        {/* Left: Authority & initiative context */}
        <div className="flex items-center gap-1.5 sm:gap-2 text-xs truncate">
          <span className="font-semibold ux4g-text-neutral-primary hidden sm:inline">
            All India Council for Technical Education
          </span>
          <span className="font-semibold ux4g-text-neutral-primary sm:hidden">
            AICTE
          </span>
          <span aria-hidden="true" className="ux4g-text-neutral-secondary hidden sm:inline">
            &bull;
          </span>
          <span className="hidden md:inline">Ministry of Education, Govt. of India</span>
          <span
            className="px-1.5 py-0.5 rounded text-[10px] font-mono ux4g-bg-neutral-subtle ux4g-text-neutral-primary font-medium border ux4g-border-neutral-subtle shrink-0"
            title="Smart India Hackathon 2026 Prototype"
          >
            SIH 2026
          </span>
        </div>

        {/* Right: Accessibility, Language, and Authentication */}
        <div className="flex items-center gap-2 sm:gap-3 ml-auto">
          {/* Accessibility Tools Trigger */}
          <button
            type="button"
            id="a11y-trigger-btn"
            onClick={handleToggleA11y}
            aria-label="Accessibility options"
            aria-haspopup="dialog"
            aria-expanded={isPanelOpen}
            title="Open accessibility options (text size, high contrast, reduce motion)"
            className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded text-xs font-medium ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-subtle transition-colors focus:outline focus:outline-2"
            style={{ outlineColor: "var(--edutrace-focus-outline)" }}
          >
            <Icon name="tune" size="xs" aria-hidden="true" />
            <span className="hidden sm:inline">Accessibility</span>
          </button>

          {/* Language Switch (English default; Hindi in R13) */}
          <div
            className="hidden sm:inline-flex items-center gap-1 border-l ux4g-border-neutral-subtle pl-3"
            role="group"
            aria-label="Language selection"
          >
            <span className="text-[11px] ux4g-text-neutral-secondary sr-only md:not-sr-only">
              Language:
            </span>
            <button
              type="button"
              aria-current="true"
              className="px-1.5 py-0.5 rounded text-xs font-semibold ux4g-text-brand-primary ux4g-bg-neutral-subtle"
              title="Current Language: English"
            >
              English
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Hindi language support coming in stretch task R13"
              className="px-1.5 py-0.5 rounded text-xs ux4g-text-neutral-secondary cursor-not-allowed opacity-60"
            >
              हिन्दी
            </button>
          </div>

          {/* Authentication State */}
          <div className="inline-flex items-center gap-1.5 sm:gap-2 border-l ux4g-border-neutral-subtle pl-2 sm:pl-3">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span
                  className="font-medium ux4g-text-neutral-primary truncate max-w-[120px] text-xs hidden md:inline"
                  title={user.email}
                >
                  {user.email}
                </span>
                <RoleBadge role={user.role} />
                <button
                  type="button"
                  onClick={logout}
                  aria-label="Sign out"
                  title="Sign out of account"
                  className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded text-xs font-medium ux4g-text-neutral-secondary hover:ux4g-text-brand-primary hover:ux4g-bg-neutral-subtle transition-colors focus:outline focus:outline-2"
                  style={{ outlineColor: "var(--edutrace-focus-outline)" }}
                >
                  <Icon name="logout" size="xs" aria-hidden="true" />
                  <span className="hidden md:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs font-medium">
                <Link
                  to="/login/college"
                  className="ux4g-text-neutral-secondary hover:ux4g-text-brand-primary hover:underline transition-colors"
                >
                  College Login
                </Link>
                <span aria-hidden="true" className="ux4g-text-neutral-secondary">
                  &bull;
                </span>
                <Link
                  to="/login/aicte"
                  className="ux4g-text-neutral-secondary hover:ux4g-text-brand-primary hover:underline transition-colors"
                >
                  AICTE Login
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
