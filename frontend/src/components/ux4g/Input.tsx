import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  size?: "sm" | "md" | "lg" | "xl";
  state?: "default" | "error" | "success" | "warning";
  prefixIcon?: React.ReactNode;
  suffixIcon?: React.ReactNode;
  fullWidth?: boolean;
}

/**
 * UX4G Input Component
 * Uses `.ux4g-input ux4g-input-{size} ux4g-input-{state}`.
 */
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      size = "md",
      state = "default",
      prefixIcon,
      suffixIcon,
      fullWidth = true,
      disabled,
      className = "",
      id,
      ...props
    },
    ref
  ) => {
    const isError = state === "error";

    return (
      <div
        style={{ minHeight: "44px" }}
        className={`ux4g-input ux4g-input-${size} ux4g-input-${state} min-h-[44px] flex items-center ${
          fullWidth ? "w-full" : ""
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`.trim()}
      >
        {prefixIcon && (
          <span className="ux4g-input-leading-icon flex items-center shrink-0">
            {prefixIcon}
          </span>
        )}
        <input
          ref={ref}
          id={id}
          disabled={disabled}
          aria-invalid={isError ? "true" : undefined}
          style={{ minHeight: "44px" }}
          className="w-full min-h-[44px] py-2.5 bg-transparent border-none outline-none text-inherit text-sm focus:ring-0"
          {...props}
        />
        {suffixIcon && (
          <span className="ux4g-input-actions flex items-center shrink-0 ml-1">
            {suffixIcon}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
