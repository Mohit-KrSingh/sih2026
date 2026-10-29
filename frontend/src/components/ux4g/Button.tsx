import React from "react";
import { Spinner } from "./Spinner";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primary"
    | "secondary"
    | "outline-primary"
    | "tonal-primary"
    | "text-primary"
    | "danger"
    | "outline-danger"
    | "text-danger"
    | "outline-neutral"
    | "text-neutral"
    | "outline"
    | "ghost";
  size?: "s" | "m" | "l" | "sm" | "md" | "lg" | "xs" | "xl";
  isLoading?: boolean;
  loadingText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

/**
 * UX4G Button Component Wrapper
 *
 * Adheres strictly to Design.md §2 and §12:
 * Always includes base class + variant class + size class (`ux4g-btn ux4g-btn-primary ux4g-btn-m`).
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "m",
      isLoading = false,
      loadingText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      className = "",
      children,
      type = "button",
      ...props
    },
    ref
  ) => {
    // Map variant to confirmed UX4G CSS classes
    const variantClass = (() => {
      switch (variant) {
        case "primary":
          return "ux4g-btn-primary";
        case "secondary":
        case "outline":
        case "outline-primary":
          return "ux4g-btn-outline-primary";
        case "tonal-primary":
          return "ux4g-btn-tonal-primary";
        case "ghost":
        case "text-primary":
          return "ux4g-btn-text-primary";
        case "danger":
          return "ux4g-btn-danger";
        case "outline-danger":
          return "ux4g-btn-outline-danger";
        case "text-danger":
          return "ux4g-btn-text-danger";
        case "outline-neutral":
          return "ux4g-btn-outline-neutral";
        case "text-neutral":
          return "ux4g-btn-text-neutral";
        default:
          return "ux4g-btn-primary";
      }
    })();

    // Map size to UX4G size classes (s, m, l, xs, xl)
    const sizeClass = (() => {
      switch (size) {
        case "xs":
          return "ux4g-btn-xs";
        case "s":
        case "sm":
          return "ux4g-btn-s";
        case "m":
        case "md":
          return "ux4g-btn-m";
        case "l":
        case "lg":
          return "ux4g-btn-l";
        case "xl":
          return "ux4g-btn-xl";
        default:
          return "ux4g-btn-m";
      }
    })();

    const isDisabled = disabled || isLoading;
    const isPrimaryFilled = variant === "primary" || variant === "danger";

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-busy={isLoading}
        aria-disabled={isDisabled}
        className={`ux4g-btn ${variantClass} ${sizeClass} ${fullWidth ? "w-full" : ""} ${className}`.trim()}
        {...props}
      >
        {isLoading ? (
          <span className="inline-flex items-center gap-2">
            <Spinner
              size="xs"
              variant={isPrimaryFilled ? "inverse" : variant === "danger" ? "danger" : "primary"}
            />
            <span>{loadingText || children}</span>
          </span>
        ) : (
          <span className="inline-flex items-center justify-center gap-2">
            {leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>}
            {children && <span>{children}</span>}
            {rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
          </span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "outline-primary" | "tonal-primary" | "text-primary";
  size?: "sm" | "md" | "lg" | "xl";
  icon: React.ReactNode;
  "aria-label": string;
}

/**
 * UX4G Icon Button Wrapper
 * Always includes base `ux4g-icon-btn` plus variant and size.
 */
export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      icon,
      "aria-label": ariaLabel,
      disabled,
      className = "",
      type = "button",
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled}
        aria-label={ariaLabel}
        className={`ux4g-icon-btn ux4g-icon-btn-${variant} ux4g-icon-btn-${size} ${className}`.trim()}
        {...props}
      >
        {icon}
      </button>
    );
  }
);

IconButton.displayName = "IconButton";
