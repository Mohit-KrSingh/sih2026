import React from "react";
import { LoadingSpinner } from "./LoadingSpinner";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  loadingText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      isLoading = false,
      loadingText,
      leftIcon,
      rightIcon,
      disabled,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      sm: "px-3 py-1.5 text-xs font-medium rounded-md gap-1.5",
      md: "px-4 py-2 text-sm font-medium rounded-lg gap-2",
      lg: "px-5 py-2.5 text-base font-semibold rounded-lg gap-2.5",
    }[size];

    const variantClasses = {
      primary:
        "bg-blue-700 hover:bg-blue-800 text-white shadow-sm focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2",
      secondary:
        "bg-slate-800 hover:bg-slate-900 text-white shadow-sm focus-visible:ring-2 focus-visible:ring-slate-600 focus-visible:ring-offset-2",
      outline:
        "bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 shadow-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2",
      danger:
        "bg-red-600 hover:bg-red-700 text-white shadow-sm focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2",
      ghost:
        "bg-transparent hover:bg-slate-100 text-slate-700 focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2",
    }[variant];

    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`inline-flex items-center justify-center transition-colors focus:outline-none disabled:opacity-50 disabled:pointer-events-none cursor-pointer ${sizeClasses} ${variantClasses} ${className}`}
        {...props}
      >
        {isLoading ? (
          <>
            <LoadingSpinner size={size === "lg" ? "md" : "sm"} />
            <span>{loadingText || children}</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="shrink-0">{leftIcon}</span>}
            <span>{children}</span>
            {rightIcon && <span className="shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
