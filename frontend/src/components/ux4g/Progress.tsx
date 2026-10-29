import React from "react";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0 to max
  max?: number;
  label?: string;
  showPercent?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "success" | "warning" | "danger";
  className?: string;
}

/**
 * UX4G Progress Component
 * Accessible progress bar with `role="progressbar"`, aria attributes, and percentage tracking.
 */
export const Progress: React.FC<ProgressProps> = ({
  value,
  max = 100,
  label,
  showPercent = false,
  size = "md",
  variant = "primary",
  className = "",
  ...props
}) => {
  const percentage = Math.min(100, Math.max(0, Math.round((value / max) * 100)));

  const heightClass = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-4",
  }[size];

  const barColor = {
    primary: "var(--ux4g-color-primary-600)",
    success: "var(--ux4g-color-green-600)",
    warning: "var(--ux4g-color-orange-600)",
    danger: "var(--ux4g-color-red-600)",
  }[variant];

  return (
    <div className={`w-full flex flex-col gap-1.5 ${className}`.trim()} {...props}>
      {(label || showPercent) && (
        <div className="flex items-center justify-between text-xs font-medium ux4g-text-neutral-secondary">
          {label && <span>{label}</span>}
          {showPercent && <span>{percentage}%</span>}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || "Progress"}
        className={`w-full ${heightClass} rounded-full overflow-hidden`}
        style={{ backgroundColor: "var(--ux4g-bg-neutral-subtle)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{ width: `${percentage}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
};
