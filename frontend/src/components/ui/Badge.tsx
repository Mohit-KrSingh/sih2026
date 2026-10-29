import React from "react";
import type { FlagLevel } from "../../types/validation";
import type { Role } from "../../types/auth";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "success" | "warning" | "danger" | "neutral" | "outline";
  size?: "sm" | "md";
  children: React.ReactNode;
}

export function Badge({
  variant = "neutral",
  size = "md",
  className = "",
  children,
  ...props
}: BadgeProps) {
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs font-medium";

  const variantClasses = {
    primary: "bg-blue-100 text-blue-800 border border-blue-200",
    success: "bg-emerald-100 text-emerald-800 border border-emerald-200",
    warning: "bg-amber-100 text-amber-900 border border-amber-300",
    danger: "bg-red-100 text-red-800 border border-red-200",
    neutral: "bg-slate-100 text-slate-700 border border-slate-200",
    outline: "bg-white text-slate-700 border border-slate-300",
  }[variant];

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}

export interface FlagBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  level: FlagLevel;
  label?: string;
  count?: number;
}

export function FlagBadge({ level, label, count, className = "", ...props }: FlagBadgeProps) {
  const displayLabel =
    label ||
    {
      error: "Error",
      exception: "Exception",
      warning: "Warning",
      info: "Info",
    }[level];

  const levelClasses: Record<FlagLevel, string> = {
    // Red filled
    error: "bg-red-100 text-red-800 border border-red-300 font-semibold",
    // Red outlined
    exception: "bg-white text-red-700 border-2 border-red-500 font-bold",
    // Amber
    warning: "bg-amber-100 text-amber-900 border border-amber-300 font-medium",
    // Grey
    info: "bg-slate-100 text-slate-700 border border-slate-300 font-medium",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs uppercase tracking-wider ${levelClasses[level]} ${className}`}
      data-testid={`flag-badge-${level}`}
      {...props}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
      <span>{displayLabel}</span>
      {count !== undefined && (
        <span className="ml-0.5 px-1 py-0.2 bg-black/10 rounded-full font-mono text-[10px]">
          {count}
        </span>
      )}
    </span>
  );
}

export function RoleBadge({ role, className = "" }: { role: Role; className?: string }) {
  const roleConfig: Record<Role, { label: string; variant: BadgeProps["variant"] }> = {
    aicte_admin: { label: "AICTE Admin", variant: "primary" },
    aicte_officer: { label: "AICTE Officer", variant: "primary" },
    college_admin: { label: "College Admin", variant: "success" },
    college_staff: { label: "College Staff", variant: "neutral" },
    college_viewer: { label: "College Viewer", variant: "outline" },
    verifier: { label: "Verifier", variant: "warning" },
  };

  const config = roleConfig[role] || { label: role, variant: "neutral" };

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}
