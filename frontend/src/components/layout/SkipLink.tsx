import React from "react";

export interface SkipLinkProps {
  targetId?: string;
  label?: string;
  className?: string;
}

/**
 * Accessible Skip Link Component
 *
 * Placed as the first focusable element in the DOM.
 * When tabbed to, becomes visibly positioned at the top of the viewport
 * with high-contrast styling and UX4G focus treatment.
 * Activating it moves focus directly to the main content container.
 */
export const SkipLink: React.FC<SkipLinkProps> = ({
  targetId = "main-content",
  label = "Skip to main content",
  className = "",
}) => {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.setAttribute("tabindex", "-1");
      target.focus();
      target.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      className={`sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2.5 focus:rounded-md focus:shadow-lg focus:outline focus:outline-2 focus:outline-offset-2 ux4g-bg-neutral-elevated ux4g-text-neutral-primary ux4g-border-neutral-default border font-semibold text-sm transition-transform ${className}`.trim()}
      style={{
        outlineColor: "var(--edutrace-focus-outline, var(--ux4g-color-primary-600))",
      }}
    >
      {label}
    </a>
  );
};
