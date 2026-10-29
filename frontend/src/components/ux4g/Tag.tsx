import React from "react";
import { Icon } from "./Icon";

export interface TagProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "tonal" | "filled" | "outline" | "text";
  color?: "neutral" | "brand" | "success" | "warning" | "error" | "info";
  size?: "s" | "m";
  onDismiss?: () => void;
  dismissLabel?: string;
  icon?: string;
}

/**
 * UX4G Tag Component
 * Uses `.ux4g-tag ux4g-tag-{variant}-{color} ux4g-tag-{size}`.
 */
export const Tag: React.FC<TagProps> = ({
  variant = "tonal",
  color = "neutral",
  size = "s",
  onDismiss,
  dismissLabel = "Remove tag",
  icon,
  className = "",
  children,
  ...props
}) => {
  return (
    <span
      className={`ux4g-tag ux4g-tag-${variant}-${color} ux4g-tag-${size} ${className}`.trim()}
      {...props}
    >
      {icon && <Icon name={icon} size="xs" color="inherit" aria-hidden="true" />}
      <span>{children}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          aria-label={dismissLabel}
          className="inline-flex items-center justify-center ml-1 p-0.5 rounded hover:opacity-75 focus:outline-none"
        >
          <Icon name="close" size="xs" color="inherit" aria-hidden="true" />
        </button>
      )}
    </span>
  );
};
