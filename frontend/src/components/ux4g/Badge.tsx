import React from "react";
import type { FlagLevel } from "../../types/validation";
import type { Role } from "../../types/auth";
import { Icon } from "./Icon";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "success" | "warning" | "danger" | "neutral" | "info";
  type?: "digit" | "icon" | "dot";
  size?: "s" | "m" | "l";
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
  return (
    <span
      className={`ux4g-badge ux4g-badge-${type}-${variant} ux4g-badge-${size} ${className}`.trim()}
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
 * - Exception: Red outlined with "Exception" label
 * - Warning: Orange with "Warning" label
 * - Info: Neutral grey with "Info" label
 *
 * Exclusively uses EduTrace semantic token variables mapped to UX4G Design System.
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
  const displayLabel =
    label ||
    {
      error: "Error",
      exception: "Exception",
      warning: "Warning",
      info: "Info",
    }[level];

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

  return (
    <span
      data-testid={`flag-badge-${level}`}
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
        <span className="font-bold opacity-90">({count})</span>
      )}
    </span>
  );
};

export interface RoleBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  role: Role;
}

/**
 * Human-readable role badge for accounts.
 */
export const RoleBadge: React.FC<RoleBadgeProps> = ({ role, className = "", style, ...props }) => {
  const roleLabels: Record<Role, string> = {
    college_admin: "College Admin",
    college_staff: "College Staff",
    college_viewer: "College Viewer",
    aicte_officer: "AICTE Officer",
    aicte_admin: "AICTE Admin",
    verifier: "Verified Organisation",
    student: "Student",
  };

  const isAicte = role.startsWith("aicte");
  const isVerifier = role === "verifier";

  const badgeStyle: React.CSSProperties = {
    backgroundColor: isAicte
      ? "var(--ux4g-color-primary-50)"
      : isVerifier
      ? "var(--ux4g-color-secondary-50)"
      : "var(--ux4g-color-neutral-100)",
    color: isAicte
      ? "var(--ux4g-color-primary-700)"
      : isVerifier
      ? "var(--ux4g-color-secondary-700)"
      : "var(--ux4g-color-neutral-800)",
    borderColor: isAicte
      ? "var(--ux4g-color-primary-200)"
      : isVerifier
      ? "var(--ux4g-color-secondary-200)"
      : "var(--ux4g-color-neutral-300)",
    borderWidth: "1px",
    borderStyle: "solid",
    ...style,
  };

  return (
    <span
      data-testid={`role-badge-${role}`}
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${className}`.trim()}
      style={badgeStyle}
      {...props}
    >
      {roleLabels[role] || role}
    </span>
  );
};
