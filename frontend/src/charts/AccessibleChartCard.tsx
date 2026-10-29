import React, { useState } from "react";
import { Button } from "../components/ux4g/Button";
import { Icon } from "../components/ux4g/Icon";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ux4g/Table";

export interface AccessibleChartCardProps {
  title: string;
  subtitle?: string;
  icon?: string;
  summary: string;
  tableHeaders: string[];
  tableRows: (string | number)[][];
  headerRight?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  minTableWidth?: string;
}

/**
 * AccessibleChartCard
 *
 * Wraps analytical visualizations with:
 * 1. Accessible header and title
 * 2. "View as table" / "View as chart" toggle button
 * 3. Structured UX4G Table alternative with mobile horizontal scroll region
 * 4. Human-readable text summary for screen reader & visual users
 */
export const AccessibleChartCard: React.FC<AccessibleChartCardProps> = ({
  title,
  subtitle,
  icon = "bar_chart",
  summary,
  tableHeaders,
  tableRows,
  headerRight,
  children,
  className = "",
  minTableWidth = "min-w-[420px]",
}) => {
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");

  return (
    <div
      className={`ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-4 sm:p-5 shadow-sm space-y-3 flex flex-col justify-between ${className}`.trim()}
    >
      {/* Header with Title and View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b ux4g-border-neutral-subtle pb-3">
        <div className="min-w-0">
          <h3 className="font-bold text-sm ux4g-text-neutral-primary flex items-center gap-2">
            <Icon name={icon} size="s" color="primary" />
            <span className="truncate">{title}</span>
          </h3>
          {subtitle && (
            <p className="text-xs ux4g-text-neutral-secondary mt-0.5 truncate">{subtitle}</p>
          )}
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center shrink-0">
          {headerRight}

          <Button
            size="sm"
            variant="outline"
            onClick={() => setViewMode((prev) => (prev === "chart" ? "table" : "chart"))}
            aria-expanded={viewMode === "table"}
            aria-label={viewMode === "chart" ? `View as table for ${title}` : `View as chart for ${title}`}
            leftIcon={
              <Icon
                name={viewMode === "chart" ? "table_chart" : "bar_chart"}
                size="xs"
                color="inherit"
              />
            }
          >
            {viewMode === "chart" ? "View as table" : "View as chart"}
          </Button>
        </div>
      </div>

      {/* Main Content: Chart or Table View */}
      <div className="flex-1 w-full">
        {viewMode === "chart" ? (
          <div role="region" aria-label={`${title} chart visualization`} className="w-full">
            {children}
          </div>
        ) : (
          <div
            tabIndex={0}
            role="region"
            aria-label={`${title} data table`}
            className="overflow-x-auto w-full focus:outline-none focus:ring-1 focus:ring-primary rounded border ux4g-border-neutral-subtle"
          >
            <Table className={minTableWidth}>
              <TableHeader>
                <TableRow>
                  {tableHeaders.map((header, idx) => (
                    <TableHead key={idx} className={idx === 0 ? "text-left" : "text-right"}>
                      {header}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {tableRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length} className="text-center py-6 ux4g-text-neutral-secondary">
                      No data available to display.
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRows.map((row, rowIdx) => (
                    <TableRow key={rowIdx}>
                      {row.map((cell, cellIdx) => (
                        <TableCell
                          key={cellIdx}
                          className={cellIdx === 0 ? "text-left font-medium" : "text-right font-mono"}
                        >
                          {typeof cell === "number" ? cell.toLocaleString() : cell}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Text Summary below Chart / Table */}
      <div className="pt-2 border-t ux4g-border-neutral-subtle flex items-start gap-2">
        <Icon
          name="info"
          size="xs"
          color="inherit"
          className="ux4g-text-neutral-secondary shrink-0 mt-0.5"
        />
        <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">{summary}</p>
      </div>
    </div>
  );
};
