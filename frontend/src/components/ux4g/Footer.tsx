import React from "react";
import { Link as RouterLink } from "react-router-dom";
import { PRODUCT_NAME, DEMO_MODE_NOTICE } from "../../brand";

export interface FooterLink {
  label: string;
  href: string;
  isExternal?: boolean;
}

export interface FooterProps {
  className?: string;
}

/**
 * UX4G Footer Component
 *
 * Adheres to SPEC §2 Rule 10, REBRAND_TASKS.md Decision 4, and GIGW 3.0:
 * - Includes demo mode disclaimer and prototype notice.
 * - Secondary links only (Privacy, Help, Terms, Accessibility, Grievance).
 * - No official emblems or agency logos.
 */
export const Footer: React.FC<FooterProps> = ({ className = "" }) => {
  const currentYear = new Date().getFullYear();

  const links: FooterLink[] = [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
    { label: "Accessibility Statement", href: "/accessibility" },
    { label: "Help & Glossary", href: "/help" },
  ];

  return (
    <footer
      role="contentinfo"
      className={`ux4g-footer-wrapper border-t ux4g-border-neutral-subtle ux4g-bg-neutral-soft ux4g-text-neutral-secondary py-8 px-4 sm:px-6 lg:px-8 ${className}`.trim()}
    >
      <div className="max-w-7xl mx-auto flex flex-col gap-6">
        {/* Demo Mode Notice Banner (SPEC Rule 10) */}
        <div className="p-3 ux4g-bg-neutral-subtle rounded-lg text-xs ux4g-text-neutral-primary flex items-center justify-between">
          <p className="font-medium">{DEMO_MODE_NOTICE}</p>
          <span className="text-xs px-2 py-0.5 rounded ux4g-bg-neutral-emphasis font-semibold uppercase">
            Demo
          </span>
        </div>

        {/* Secondary Navigation Links */}
        <div className="ux4g-footer-row flex flex-wrap items-center justify-between gap-4 pt-2 border-t ux4g-border-neutral-subtle">
          <nav aria-label="Footer Secondary Links" className="flex flex-wrap items-center gap-6 text-sm">
            {links.map((link) => (
              <RouterLink
                key={link.href}
                to={link.href}
                className="hover:ux4g-text-brand-primary underline-offset-2 hover:underline"
              >
                {link.label}
              </RouterLink>
            ))}
          </nav>

          <p className="text-xs ux4g-text-neutral-tertiary">
            © {currentYear} {PRODUCT_NAME}. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};
