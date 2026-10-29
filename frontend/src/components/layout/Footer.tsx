import React from "react";
import { Link } from "react-router-dom";
import {
  PRODUCT_NAME,
  DEMO_MODE_NOTICE,
  GRIEVANCE_EMAIL,
  SUPPORT_EMAIL,
} from "../../brand";

export interface FooterLink {
  label: string;
  href: string;
}

export interface FooterProps {
  className?: string;
}

/**
 * UX4G Standard Footer Component
 *
 * Implements SPEC §2 Rule 10, REBRAND_TASKS.md Decision 4, and Task R04:
 * - Mandatory demo mode line and prototype disclaimer.
 * - Secondary links only (Privacy Policy, Terms of Service, Accessibility Statement, Help & Glossary).
 * - Grievance officer and support contacts.
 * - Prohibits official emblems and "Powered by NeGD" attribution.
 */
export const Footer: React.FC<FooterProps> = ({ className = "" }) => {
  const currentYear = new Date().getFullYear();

  const secondaryLinks: FooterLink[] = [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
    { label: "Accessibility Statement", href: "/accessibility" },
    { label: "Help & Glossary", href: "/help" },
  ];

  return (
    <footer
      role="contentinfo"
      aria-label="Site Footer"
      className={`ux4g-footer-wrapper border-t ux4g-border-neutral-subtle ux4g-bg-neutral-soft ux4g-text-neutral-secondary py-8 px-4 sm:px-6 lg:px-8 mt-auto ${className}`.trim()}
    >
      <div className="max-w-7xl mx-auto flex flex-col gap-6">
        {/* Demo Mode Notice Banner (SPEC §2 Rule 10) */}
        <div className="p-3.5 ux4g-bg-neutral-subtle rounded-lg text-xs ux4g-text-neutral-primary flex flex-col sm:flex-row sm:items-center justify-between gap-3 border ux4g-border-neutral-subtle">
          <p className="font-medium leading-relaxed">{DEMO_MODE_NOTICE}</p>
          <span className="text-[11px] px-2.5 py-0.5 rounded font-bold uppercase tracking-wider ux4g-bg-neutral-emphasis ux4g-text-neutral-primary shrink-0 self-start sm:self-auto border ux4g-border-neutral-subtle">
            Demo Mode
          </span>
        </div>

        {/* Portal Attribution & Grievance Contact */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs pt-1">
          <div className="space-y-1">
            <p className="font-semibold ux4g-text-neutral-primary">
              {PRODUCT_NAME} &bull; Student Data Management and Verification System
            </p>
            <p className="ux4g-text-neutral-secondary font-medium">
              All India Council for Technical Education (AICTE) &bull; Ministry of Education, Govt. of India
            </p>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-xs ux4g-text-neutral-secondary">
            <span>
              Grievance Officer:{" "}
              <a
                href={`mailto:${GRIEVANCE_EMAIL}`}
                className="underline hover:ux4g-text-brand-primary"
              >
                {GRIEVANCE_EMAIL}
              </a>
            </span>
            <span aria-hidden="true" className="hidden sm:inline">
              &bull;
            </span>
            <span>
              Support:{" "}
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="underline hover:ux4g-text-brand-primary"
              >
                {SUPPORT_EMAIL}
              </a>
            </span>
          </div>
        </div>

        {/* Secondary Links & Legal Strip */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-4 border-t ux4g-border-neutral-subtle text-xs">
          <nav
            aria-label="Footer Secondary Links"
            className="flex flex-wrap items-center gap-6 text-sm"
          >
            {secondaryLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className="ux4g-text-neutral-secondary hover:ux4g-text-brand-primary underline-offset-2 hover:underline transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <p className="ux4g-text-neutral-secondary text-xs font-medium">
            &copy; {currentYear} {PRODUCT_NAME}. Designed in accordance with WCAG 2.1 AA and DPDP Act, 2023 principles.
          </p>
        </div>
      </div>
    </footer>
  );
};
