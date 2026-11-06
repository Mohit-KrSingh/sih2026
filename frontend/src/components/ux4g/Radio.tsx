import React from "react";

export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label: React.ReactNode;
  size?: "sm" | "md" | "lg";
  isError?: boolean;
}

/**
 * UX4G Radio Component
 * Uses `.ux4g-radio ux4g-radio-{size}` and `.ux4g-radio-error`.
 */
export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  (
    {
      label,
      size = "md",
      isError = false,
      disabled,
      className = "",
      id,
      ...props
    },
    ref
  ) => {
    return (
      <label
        className={`ux4g-radio ux4g-radio-${size} ${isError ? "ux4g-radio-error" : ""} ${
          disabled ? "opacity-50 cursor-not-allowed" : ""
        } ${className}`.trim()}
      >
        <input
          ref={ref}
          type="radio"
          id={id}
          disabled={disabled}
          aria-invalid={isError ? "true" : undefined}
          className="mt-0.5 cursor-pointer disabled:cursor-not-allowed"
          {...props}
        />
        <span className="text-sm select-none">{label}</span>
      </label>
    );
  }
);

Radio.displayName = "Radio";
