import React from "react";

export interface SpinnerProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "inverse" | "danger";
  type?: "full" | "split" | "partial";
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  label?: string;
}

/**
 * UX4G Spinner Component
 * Uses `.ux4g-spinner-{variant}-{type}` and `.ux4g-spinner-{size}`.
 */
export const Spinner: React.FC<SpinnerProps> = ({
  variant = "primary",
  type = "full",
  size = "md",
  label = "Loading...",
  className = "",
  ...props
}) => {
  return (
    <span
      role="status"
      aria-label={label}
      className={`ux4g-spinner-${variant}-${type} ux4g-spinner-${size} ${className}`.trim()}
      {...props}
    >
      <span className="sr-only">{label}</span>
    </span>
  );
};
