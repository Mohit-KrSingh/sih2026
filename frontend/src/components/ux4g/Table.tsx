import React from "react";

export interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  size?: "s" | "m" | "lg";
  zebra?: boolean;
  columnDividers?: boolean;
}

/**
 * UX4G Table Component
 * Uses `.ux4g-table ux4g-table-{size}` with optional `.ux4g-table-column-dividers` and `.ux4g-table-zebra-rows`.
 */
export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  (
    {
      size = "m",
      zebra = false,
      columnDividers = false,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div className="w-full overflow-x-auto ux4g-border ux4g-border-neutral-subtle rounded-lg">
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

export const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className = "", children, ...props }, ref) => (
  <thead
    ref={ref}
    className={`ux4g-bg-neutral-soft border-b ux4g-border-neutral-subtle text-xs font-semibold uppercase ux4g-text-neutral-secondary ${className}`.trim()}
    {...props}
  >
    {children}
  </thead>
));
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

export const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className = "", children, ...props }, ref) => (
  <tr
    ref={ref}
    className={`hover:ux4g-bg-neutral-soft transition-colors ${className}`.trim()}
    {...props}
  >
    {children}
  </tr>
));
TableRow.displayName = "TableRow";

export interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  sortDirection?: "ascending" | "descending" | "none";
}

export const TableHead = React.forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ sortDirection, className = "", children, ...props }, ref) => (
    <th
      ref={ref}
      aria-sort={sortDirection}
      className={`px-4 py-3 font-semibold ux4g-text-neutral-secondary ${className}`.trim()}
      {...props}
    >
      {children}
    </th>
  )
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
