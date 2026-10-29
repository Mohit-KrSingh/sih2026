import React from "react";
import type { FlagLevel } from "../../types/validation";
import type { Role } from "../../types/auth";
import { Icon } from "./Icon";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "success" | "warning" | "danger" | "neutral" | "info" | "outline";
  type?: "digit" | "icon" | "dot";
  size?: "s" | "m" | "l" | "sm" | "md";
}

/**
 * UX4G Standard Badge
 * Uses `.ux4g-badge-{type}-{color}` and `.ux4g-badge-{size}`.
 */
export const Badge: React.FC<BadgeProps> = ({
  variant = "neutral",
  type = "digit",
  size = "m",
  className = "",
  children,
  ...props
}) => {
  const normalizedSize = size === "sm" ? "s" : size === "md" ? "m" : size;
  const isOutline = variant === "outline";
  const normalizedVariant = isOutline ? "neutral" : variant;
  const outlineClass = isOutline ? "border ux4g-border-neutral-default bg-transparent" : "";

  return (
    <span
      className={`ux4g-badge ux4g-badge-${type}-${normalizedVariant} ux4g-badge-${normalizedSize} ${outlineClass} ${className}`.trim()}
      {...props}
    >
      {children}
    </span>
  );
};

export interface FlagBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  level: FlagLevel;
  label?: string;
  count?: number;
  showIcon?: boolean;
}

/**
 * EduTrace FlagBadge Component
 *
 * SPEC §19 and DECISIONS.md Difference 6:
 * - Error: Red filled with "Error" label
 * - Exception: Red outlined with "Exception" label (2px border)
 * - Warning: Orange with "Warning" label
 * - Info: Neutral grey with "Info" label
 *
 * Exclusively uses EduTrace semantic token variables mapped to UX4G Design System.
 * Ensures WCAG 2.1 AA >= 4.5:1 text contrast and accessibility without relying on color alone.
 */
export const FlagBadge: React.FC<FlagBadgeProps> = ({
  level,
  label,
  count,
  showIcon = true,
  className = "",
  style,
  ...props
}) => {
  const defaultLabel = {
    error: "Error",
    exception: "Exception",
    warning: "Warning",
    info: "Info",
  }[level];

  const displayLabel = label || defaultLabel;

  const iconName = {
    error: "cancel",
    exception: "report_problem",
    warning: "warning",
    info: "info",
  }[level];

  // Token-driven styling based on EduTrace & UX4G design tokens
  const levelStyles: Record<FlagLevel, React.CSSProperties> = {
    error: {
      backgroundColor: "var(--edutrace-flag-error-bg)",
      color: "var(--edutrace-flag-error-text)",
      borderColor: "var(--edutrace-flag-error-border)",
      borderWidth: "1px",
      borderStyle: "solid",
    },
    exception: {
      backgroundColor: "var(--edutrace-flag-exception-bg)",
      color: "var(--edutrace-flag-exception-text)",
      borderColor: "var(--edutrace-flag-exception-border)",
      borderWidth: "2px",
      borderStyle: "solid",
    },
    warning: {
      backgroundColor: "var(--edutrace-flag-warning-bg)",
      color: "var(--edutrace-flag-warning-text)",
      borderColor: "var(--edutrace-flag-warning-border)",
      borderWidth: "1px",
      borderStyle: "solid",
    },
    info: {
      backgroundColor: "var(--edutrace-flag-info-bg)",
      color: "var(--edutrace-flag-info-text)",
      borderColor: "var(--edutrace-flag-info-border)",
      borderWidth: "1px",
      borderStyle: "solid",
    },
  };

  const accessibleLabel = label
    ? `${defaultLabel}: ${label}${count !== undefined ? ` (${count})` : ""}`
    : `${displayLabel}${count !== undefined ? ` (${count})` : ""}`;

  return (
    <span
      data-testid={`flag-badge-${level}`}
      data-level={level}
      aria-label={accessibleLabel}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${className}`.trim()}
      style={{
        ...levelStyles[level],
        ...style,
      }}
      role="status"
      {...props}
    >
      {showIcon && <Icon name={iconName} size="xs" color="inherit" aria-hidden="true" />}
      <span>{displayLabel}</span>
      {count !== undefined && (
        <span className="font-bold">({count})</span>
      )}
    </span>
  );
};

export interface RoleBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  role: Role;
}

/**
 * Human-readable role badge for accounts using UX4G tokens.
 */
export const RoleBadge: React.FC<RoleBadgeProps> = ({ role, className = "", style, ...props }) => {
  const roleLabels: Record<Role, string> = {
    college_admin: "College Admin",
    college_staff: "College Staff",
    college_viewer: "College Viewer",
    aicte_officer: "AICTE Officer",
    aicte_admin: "AICTE Admin",
    verifier: "Verifier",
    student: "Student",
  };

  const isAicte = role.startsWith("aicte");
  const isVerifier = role === "verifier";

  const badgeStyle: React.CSSProperties = {
    backgroundColor: isAicte
      ? "var(--edutrace-brand-primary-surface)"
      : isVerifier
      ? "var(--edutrace-brand-secondary-surface)"
      : "var(--ux4g-bg-neutral-soft)",
    color: isAicte
      ? "var(--edutrace-brand-primary)"
      : isVerifier
      ? "var(--edutrace-brand-secondary)"
      : "var(--edutrace-text-primary)",
    borderColor: isAicte
      ? "var(--edutrace-brand-primary-border)"
      : "var(--edutrace-border-subtle)",
    borderWidth: "1px",
    borderStyle: "solid",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${className}`.trim()}
      style={{
        ...badgeStyle,
        ...style,
      }}
      {...props}
    >
      {roleLabels[role] || role}
    </span>
  );
};
