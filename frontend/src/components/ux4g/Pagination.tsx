import React from "react";
import { Icon } from "./Icon";

export interface PaginationProps {
  currentPage: number; // 1-indexed
  totalPages: number;
  onPageChange: (page: number) => void;
  ariaLabel?: string;
  className?: string;
}

/**
 * UX4G Pagination Component
 * Uses `.ux4g-pagination-wrapper`, `.ux4g-pagination`, `.ux4g-page-nav`, `.ux4g-page-number`.
 */
export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  ariaLabel = "Pagination",
  className = "",
}) => {
  if (totalPages <= 1) return null;

  const getPageNumbers = () => {
    const pages: (number | "...")[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (currentPage > 3) pages.push("...");
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (currentPage < totalPages - 2) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <nav
      aria-label={ariaLabel}
      className={`ux4g-pagination-wrapper flex items-center justify-between gap-4 py-2 ${className}`.trim()}
    >
      <div className="ux4g-pagination flex items-center gap-1">
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          aria-label="Previous page"
          className="ux4g-page-nav p-1.5 rounded-md hover:ux4g-bg-neutral-soft disabled:opacity-40 disabled:cursor-not-allowed ux4g-text-neutral-secondary"
        >
          <Icon name="chevron_left" size="sm" color="inherit" aria-hidden="true" />
        </button>

        {getPageNumbers().map((p, idx) => {
          if (p === "...") {
            return (
              <span key={`dots-${idx}`} className="px-2 py-1 text-sm ux4g-text-neutral-tertiary select-none">
                …
              </span>
            );
          }

          const isCurrent = p === currentPage;

          return (
            <button
              key={p}
              type="button"
              onClick={() => onPageChange(p as number)}
              aria-current={isCurrent ? "page" : undefined}
              aria-label={`Page ${p}`}
              className={`ux4g-page-number px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                isCurrent
                  ? "ux4g-bg-primary-strong ux4g-text-white font-semibold"
                  : "ux4g-text-neutral-secondary hover:ux4g-bg-neutral-soft"
              }`}
            >
              {p}
            </button>
          );
        })}

        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          aria-label="Next page"
          className="ux4g-page-nav p-1.5 rounded-md hover:ux4g-bg-neutral-soft disabled:opacity-40 disabled:cursor-not-allowed ux4g-text-neutral-secondary"
        >
          <Icon name="chevron_right" size="sm" color="inherit" aria-hidden="true" />
        </button>
      </div>

      <div className="text-xs ux4g-text-neutral-tertiary font-medium">
        Page {currentPage} of {totalPages}
      </div>
    </nav>
  );
};
