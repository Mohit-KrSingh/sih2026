import React from "react";

export interface IconProps extends React.HTMLAttributes<HTMLElement> {
  name: string;
  variant?: "outlined" | "filled" | "round" | "sharp";
  color?: "primary" | "success" | "warning" | "error" | "info" | "neutral" | "inherit";
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  label?: string;
}

/**
 * UX4G Material Symbols / Icons Wrapper
 * Uses embedded UX4G Material Icons font families with `.ux4g-icon` classes.
 */
export const Icon: React.FC<IconProps> = ({
  name,
  variant = "outlined",
  color = "inherit",
  size = "md",
  label,
  className = "",
  style,
  ...props
}) => {
  const isDecorative = !label;

  const colorClass = color !== "inherit" ? `ux4g-icon-${color}` : "";

  // Size mapping using CSS variables or explicit width/height
  const sizePx = {
    xs: 14,
    sm: 16,
    md: 20,
    lg: 24,
    xl: 32,
  }[size];

  const sizeStyle: React.CSSProperties = {
    fontSize: `${sizePx}px`,
    width: `${sizePx}px`,
    height: `${sizePx}px`,
    ...style,
  };

  return (
    <span
      className={`ux4g-icon ux4g-icon-${variant} ${colorClass} ${className}`.trim()}
      style={sizeStyle}
      aria-hidden={isDecorative ? "true" : undefined}
      aria-label={label}
      role={isDecorative ? undefined : "img"}
      {...props}
    >
      {name}
    </span>
  );
};
