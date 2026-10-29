import React from "react";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PRODUCT_NAME, GRIEVANCE_EMAIL } from "../brand";

/**
 * Accessibility statement page
 */
export const AccessibilityPage: React.FC = () => {
  useDocumentTitle("Accessibility statement");

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      <header className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ux4g-bg-neutral-subtle ux4g-text-neutral-secondary border ux4g-border-neutral-subtle">
          <span>Standards compliance and inclusivity</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight leading-tight ux4g-text-neutral-primary">
          Accessibility statement
        </h1>
        <p className="text-base leading-relaxed ux4g-text-neutral-secondary">
          Our commitment to ensuring the {PRODUCT_NAME} platform is accessible, inclusive, and usable by everyone regardless of ability or device.
        </p>
      </header>

      <section className="space-y-4 text-sm leading-relaxed ux4g-text-neutral-secondary">
        <h2 className="text-lg font-bold ux4g-text-neutral-primary">1. Conformance standards</h2>
        <p>
          The {PRODUCT_NAME} interface is engineered to meet the requirements of the{" "}
          <strong className="ux4g-text-neutral-primary">Web Content Accessibility Guidelines (WCAG) 2.1 Level AA</strong> and the{" "}
          <strong className="ux4g-text-neutral-primary">Guidelines for Indian Government Websites (GIGW 3.0)</strong>, aligned with the Rights of Persons with Disabilities (RPwD) Act 2016.
        </p>

        <h2 className="text-lg font-bold ux4g-text-neutral-primary">2. Core accessibility features</h2>
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong className="ux4g-text-neutral-primary">Keyboard navigation:</strong> All navigation menus, dialogs, forms, and interactive controls are completely operable using standard keyboard navigation without keyboard traps.
          </li>
          <li>
            <strong className="ux4g-text-neutral-primary">Skip link:</strong> An accessible skip link is provided as the first focusable element on every page to allow keyboard and screen reader users to bypass repetitive header navigation.
          </li>
          <li>
            <strong className="ux4g-text-neutral-primary">Visible focus indicators:</strong> High-contrast focus rings adhere to UX4G Design System standards and are never suppressed.
          </li>
          <li>
            <strong className="ux4g-text-neutral-primary">Semantic landmarks and headings:</strong> Pages structure content using standard HTML5 landmarks (<code>header</code>, <code>nav</code>, <code>main</code>, <code>footer</code>) and maintain strict single-<code>h1</code> hierarchical headings.
          </li>
          <li>
            <strong className="ux4g-text-neutral-primary">Contrast and typography:</strong> Text meets or exceeds minimum contrast ratios (4.5:1 for body text, 3:1 for large text and UI components) using bundled offline Noto Sans typography.
          </li>
        </ul>

        <h2 className="text-lg font-bold ux4g-text-neutral-primary">3. Feedback and grievance</h2>
        <p>
          If you encounter any accessibility barrier or have difficulty using any part of this platform, please contact our accessibility and grievance officer at{" "}
          <a href={`mailto:${GRIEVANCE_EMAIL}`} className="font-semibold underline hover:ux4g-text-brand-primary">
            {GRIEVANCE_EMAIL}
          </a>.
        </p>

        <div className="pt-4 border-t ux4g-border-neutral-subtle">
          <Link to="/" className="font-semibold underline hover:ux4g-text-brand-primary">
            &larr; Return to home
          </Link>
        </div>
      </section>
    </div>
  );
};
