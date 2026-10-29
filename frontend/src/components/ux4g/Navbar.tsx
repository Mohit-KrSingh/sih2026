import React from "react";
import { Link as RouterLink } from "react-router-dom";

export interface NavItem {
  label: string;
  href: string;
  active?: boolean;
}

export interface NavbarProps {
  brand: React.ReactNode;
  items?: NavItem[];
  rightContent?: React.ReactNode;
  ariaLabel?: string;
  className?: string;
}

/**
 * UX4G Navbar Component
 * Uses `.ux4g-navbar`, `.ux4g-navbar-wrap`, `.ux4g-navbar-logo`, `.ux4g-navbar-links`, `.ux4g-navbar-right`.
 */
export const Navbar: React.FC<NavbarProps> = ({
  brand,
  items = [],
  rightContent,
  ariaLabel = "Main Navigation",
  className = "",
}) => {
  return (
    <header className="w-full">
      <nav
        role="navigation"
        aria-label={ariaLabel}
        className={`ux4g-navbar w-full border-b ux4g-border-neutral-subtle ux4g-bg-neutral-elevated ${className}`.trim()}
      >
        <div className="ux4g-navbar-wrap max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="ux4g-navbar-logo flex items-center shrink-0">
            {brand}
          </div>

          {items.length > 0 && (
            <div className="ux4g-navbar-links hidden md:flex items-center gap-6">
              {items.map((item, idx) => (
                <RouterLink
                  key={`${item.href}-${idx}`}
                  to={item.href}
                  className={`text-sm font-medium transition-colors hover:ux4g-text-brand-primary ${
                    item.active
                      ? "ux4g-text-brand-primary font-semibold border-b-2 ux4g-border-primary pb-1"
                      : "ux4g-text-neutral-secondary"
                  }`}
                  aria-current={item.active ? "page" : undefined}
                >
                  {item.label}
                </RouterLink>
              ))}
            </div>
          )}

          {rightContent && (
            <div className="ux4g-navbar-right flex items-center gap-3">
              {rightContent}
            </div>
          )}
        </div>
      </nav>
    </header>
  );
};
