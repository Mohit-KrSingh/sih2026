import React from "react";
import { Link as RouterLink } from "react-router-dom";
import { Icon } from "./Icon";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  ariaLabel?: string;
  className?: string;
}

/**
 * UX4G Breadcrumb Component
 * Uses `.ux4g-breadcrumb`, `.ux4g-breadcrumb-list`, `.ux4g-breadcrumb-item`, `.ux4g-breadcrumb-link`.
 */
export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  ariaLabel = "Breadcrumb",
  className = "",
}) => {
  return (
    <nav aria-label={ariaLabel} className={`ux4g-breadcrumb ${className}`.trim()}>
      <ol className="ux4g-breadcrumb-list flex items-center gap-2 text-sm ux4g-text-neutral-secondary">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={index} className="ux4g-breadcrumb-item flex items-center gap-2">
              {index > 0 && (
                <span className="ux4g-breadcrumb-separator flex items-center ux4g-text-neutral-tertiary">
                  <Icon name="chevron_right" size="xs" color="inherit" aria-hidden="true" />
                </span>
              )}
              {isLast || !item.href ? (
                <span
                  className="ux4g-breadcrumb-page font-semibold ux4g-text-neutral-primary"
                  aria-current="page"
                >
                  {item.label}
                </span>
              ) : (
                <RouterLink
                  to={item.href}
                  className="ux4g-breadcrumb-link hover:ux4g-text-brand-primary underline-offset-2 hover:underline"
                >
                  {item.label}
                </RouterLink>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
