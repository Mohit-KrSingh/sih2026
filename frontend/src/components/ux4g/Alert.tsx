import React from "react";
import { Icon } from "./Icon";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "success" | "warning" | "error";
  title?: string;
  onDismiss?: () => void;
  dismissLabel?: string;
  showIcon?: boolean;
}

/**
 * UX4G Alert Component
 * Uses `.ux4g-alert ux4g-alert-{variant}`.
 */
export const Alert: React.FC<AlertProps> = ({
  variant = "info",
  title,
  onDismiss,
  dismissLabel = "Dismiss alert",
  showIcon = true,
  className = "",
  children,
  ...props
}) => {
  const iconName = {
    info: "info",
    success: "check_circle",
    warning: "warning",
    error: "error",
  }[variant];

  const role = variant === "error" || variant === "warning" ? "alert" : "status";

  return (
    <div
      role={role}
      className={`ux4g-alert ux4g-alert-${variant} rounded-md ${className}`.trim()}
      {...props}
    >
      {showIcon && (
        <span className="ux4g-alert-icon shrink-0">
          <Icon name={iconName} size="md" color="inherit" aria-hidden="true" />
        </span>
      )}
      <div className="flex-1 min-w-0">
        {title && <p className="font-semibold text-sm mb-0.5">{title}</p>}
        <div className="text-sm">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label={dismissLabel}
          className="shrink-0 p-1 rounded hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-offset-1"
        >
          <Icon name="close" size="sm" color="inherit" aria-hidden="true" />
        </button>
      )}
    </div>
  );
};
