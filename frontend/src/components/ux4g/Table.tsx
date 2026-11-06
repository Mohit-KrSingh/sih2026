import React from "react";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";
import { Icon } from "./Icon";
import { Pagination } from "./Pagination";
import { Skeleton } from "./Skeleton";

export interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  size?: "s" | "m" | "lg";
  zebra?: boolean;
  columnDividers?: boolean;
  stickyHeader?: boolean;
  ariaLabel?: string;
  containerClassName?: string;
  maxHeight?: string | number;
}

/**
 * UX4G Table Component
 * Uses `.ux4g-table ux4g-table-{size}` with optional `.ux4g-table-column-dividers` and `.ux4g-table-zebra-rows`.
 * Wrapped in an accessible keyboard-operable scroll region for horizontal responsiveness on phones.
 */
export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  (
    {
      size = "m",
      zebra = false,
      columnDividers = false,
      stickyHeader = false,
      ariaLabel = "Data table",
      containerClassName = "",
      maxHeight,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const scrollStyles: React.CSSProperties = {};
    if (maxHeight) {
      scrollStyles.maxHeight = typeof maxHeight === "number" ? `${maxHeight}px` : maxHeight;
    }

    return (
      <div
        role="region"
        aria-label={ariaLabel}
        tabIndex={0}
        style={scrollStyles}
        className={`w-full overflow-x-auto ux4g-border ux4g-border-neutral-subtle rounded-lg focus:outline-none focus:ring-1 focus:ring-primary ${
          stickyHeader || maxHeight ? "overflow-y-auto" : ""
        } ${containerClassName}`.trim()}
      >
        <table
          ref={ref}
          className={`ux4g-table ux4g-table-${size} ${
            columnDividers ? "ux4g-table-column-dividers" : ""
          } ${zebra ? "ux4g-table-zebra-rows" : ""} w-full text-left text-sm ${className}`.trim()}
          {...props}
        >
          {children}
        </table>
      </div>
    );
  }
);

Table.displayName = "Table";

export interface TableHeaderProps extends React.HTMLAttributes<HTMLTableSectionElement> {
  sticky?: boolean;
}

export const TableHeader = React.forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  ({ sticky = false, className = "", children, ...props }, ref) => (
    <thead
      ref={ref}
      className={`ux4g-bg-neutral-soft border-b ux4g-border-neutral-subtle text-xs font-semibold uppercase ux4g-text-neutral-secondary ${
        sticky ? "sticky top-0 z-10 shadow-xs" : ""
      } ${className}`.trim()}
      {...props}
    >
      {children}
    </thead>
  )
);
TableHeader.displayName = "TableHeader";

export const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className = "", children, ...props }, ref) => (
  <tbody
    ref={ref}
    className={`divide-y ux4g-border-neutral-subtle ux4g-bg-neutral-elevated ${className}`.trim()}
    {...props}
  >
    {children}
  </tbody>
));
TableBody.displayName = "TableBody";

export interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  focusable?: boolean;
  selected?: boolean;
}

export const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
  (
    {
      focusable = false,
      selected = false,
      className = "",
      children,
      tabIndex,
      ...props
    },
    ref
  ) => (
    <tr
      ref={ref}
      tabIndex={focusable ? (tabIndex ?? 0) : tabIndex}
      aria-selected={selected ? true : undefined}
      className={`hover:ux4g-bg-neutral-soft transition-colors ${
        focusable
          ? "focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary cursor-pointer"
          : ""
      } ${selected ? "ux4g-bg-neutral-soft font-medium" : ""} ${className}`.trim()}
      {...props}
    >
      {children}
    </tr>
  )
);
TableRow.displayName = "TableRow";

export interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  sortable?: boolean;
  sortDirection?: "ascending" | "descending" | "none";
  onSort?: () => void;
}

export const TableHead = React.forwardRef<HTMLTableCellElement, TableHeadProps>(
  (
    {
      sortable = false,
      sortDirection = "none",
      onSort,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    if (sortable) {
      const nextDirection =
        sortDirection === "ascending"
          ? "descending"
          : sortDirection === "descending"
          ? "none"
          : "ascending";

      return (
        <th
          ref={ref}
          aria-sort={sortDirection}
          className={`px-4 py-3 font-semibold ux4g-text-neutral-secondary text-xs uppercase tracking-wider select-none ${className}`.trim()}
          {...props}
        >
          <button
            type="button"
            onClick={onSort}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSort?.();
              }
            }}
            aria-label={`${
              typeof children === "string" ? children : "Column"
            }, sort ${nextDirection}`}
            className="flex items-center gap-1.5 font-semibold text-inherit hover:ux4g-text-neutral-primary focus:outline-none focus:ring-2 focus:ring-primary rounded px-1 -mx-1 py-0.5 tracking-wider uppercase transition-colors cursor-pointer"
          >
            <span>{children}</span>
            <Icon
              name={
                sortDirection === "ascending"
                  ? "arrow_upward"
                  : sortDirection === "descending"
                  ? "arrow_downward"
                  : "unfold_more"
              }
              size="sm"
              color={sortDirection !== "none" ? "primary" : "inherit"}
              aria-hidden="true"
            />
          </button>
        </th>
      );
    }

    return (
      <th
        ref={ref}
        aria-sort={sortDirection !== "none" ? sortDirection : undefined}
        className={`px-4 py-3 font-semibold ux4g-text-neutral-secondary text-xs uppercase tracking-wider ${className}`.trim()}
        {...props}
      >
        {children}
      </th>
    );
  }
);
TableHead.displayName = "TableHead";

export const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className = "", children, ...props }, ref) => (
  <td
    ref={ref}
    className={`px-4 py-3 ux4g-text-neutral-primary ${className}`.trim()}
    {...props}
  >
    {children}
  </td>
));
TableCell.displayName = "TableCell";

export const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className = "", children, ...props }, ref) => (
  <caption
    ref={ref}
    className={`text-xs ux4g-text-neutral-tertiary py-2 caption-bottom ${className}`.trim()}
    {...props}
  >
    {children}
  </caption>
));
TableCaption.displayName = "TableCaption";

export interface TableEmptyStateProps {
  colSpan: number;
  title?: string;
  description?: string;
  icon?: string;
  action?: React.ReactNode;
}

export const TableEmptyState: React.FC<TableEmptyStateProps> = ({
  colSpan,
  title = "No records found",
  description = "No data matches your current criteria.",
  icon = "inbox",
  action,
}) => (
  <tr>
    <td colSpan={colSpan} className="p-8 text-center">
      <EmptyState title={title} description={description} icon={icon} action={action} />
    </td>
  </tr>
);

export interface TableSkeletonRowsProps {
  columns: number;
  rows?: number;
}

export const TableSkeletonRows: React.FC<TableSkeletonRowsProps> = ({
  columns,
  rows = 5,
}) => (
  <>
    {Array.from({ length: rows }).map((_, rIdx) => (
      <tr key={`skel-row-${rIdx}`} className="border-b ux4g-border-neutral-subtle">
        {Array.from({ length: columns }).map((_, cIdx) => (
          <td key={`skel-cell-${rIdx}-${cIdx}`} className="px-4 py-3">
            <Skeleton height={16} width={cIdx === 0 ? "40%" : "80%"} />
          </td>
        ))}
      </tr>
    ))}
  </>
);

export interface TableErrorProps {
  colSpan?: number;
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export const TableError: React.FC<TableErrorProps> = ({
  colSpan,
  title = "Failed to load table data",
  message,
  onRetry,
  retryLabel = "Try again",
}) => {
  const content = (
    <div
      role="alert"
      className="p-4 rounded-lg ux4g-border ux4g-border-error ux4g-bg-neutral-soft flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
    >
      <div className="flex items-start gap-3">
        <Icon name="error" size="md" color="error" aria-hidden="true" />
        <div>
          <h4 className="text-sm font-semibold ux4g-text-status-error">{title}</h4>
          <p className="text-xs ux4g-text-neutral-secondary mt-0.5">{message}</p>
        </div>
      </div>
      {onRetry && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRetry}
          aria-label={retryLabel}
        >
          {retryLabel}
        </Button>
      )}
    </div>
  );

  if (colSpan) {
    return (
      <tr>
        <td colSpan={colSpan} className="p-4">
          {content}
        </td>
      </tr>
    );
  }

  return <div className="p-4">{content}</div>;
};

export interface TablePaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems?: number;
  pageSize?: number;
  pageSizeOptions?: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  ariaLabel?: string;
  className?: string;
}

export const TablePagination: React.FC<TablePaginationProps> = ({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  pageSizeOptions = [10, 25, 50, 100],
  onPageChange,
  onPageSizeChange,
  ariaLabel = "Table pagination",
  className = "",
}) => {
  const startItem =
    totalItems !== undefined && pageSize !== undefined
      ? Math.min((currentPage - 1) * pageSize + 1, totalItems)
      : undefined;
  const endItem =
    totalItems !== undefined && pageSize !== undefined
      ? Math.min(currentPage * pageSize, totalItems)
      : undefined;

  return (
    <div
      className={`flex flex-col sm:flex-row items-center justify-between gap-3 p-3 border-t ux4g-border-neutral-subtle ux4g-bg-neutral-elevated ${className}`.trim()}
    >
      <div className="flex items-center gap-4 text-xs ux4g-text-neutral-secondary">
        {totalItems !== undefined && startItem !== undefined && endItem !== undefined ? (
          <span>
            Showing <strong className="ux4g-text-neutral-primary">{startItem}</strong> to{" "}
            <strong className="ux4g-text-neutral-primary">{endItem}</strong> of{" "}
            <strong className="ux4g-text-neutral-primary">{totalItems}</strong> records
          </span>
        ) : totalItems !== undefined ? (
          <span>
            Total: <strong className="ux4g-text-neutral-primary">{totalItems}</strong> records
          </span>
        ) : null}

        {pageSize && onPageSizeChange && (
          <div className="flex items-center gap-1.5">
            <label htmlFor="table-page-size" className="text-xs">
              Rows per page:
            </label>
            <select
              id="table-page-size"
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="ux4g-select text-xs py-1 px-2 rounded border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated ux4g-text-neutral-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={onPageChange}
        ariaLabel={ariaLabel}
      />
    </div>
  );
};
