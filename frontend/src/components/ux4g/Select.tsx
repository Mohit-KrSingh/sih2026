import React from "react";
import { Icon } from "./Icon";

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  size?: "sm" | "md" | "lg";
  state?: "default" | "error" | "success" | "warning";
  options?: SelectOption[];
  placeholder?: string;
  fullWidth?: boolean;
}

/**
 * UX4G Select Component
 * Wraps an accessible native select element with UX4G dropdown styling and arrow indicator.
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      size = "md",
      state = "default",
      options = [],
      placeholder,
      fullWidth = true,
      disabled,
      className = "",
      children,
      id,
      ...props
    },
    ref
  ) => {
    const isError = state === "error";

    return (
      <div
        className={`ux4g-input ux4g-input-${size} ux4g-input-${state} relative flex items-center pr-2 ${
          fullWidth ? "w-full" : ""
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`.trim()}
      >
        <select
          ref={ref}
          id={id}
          disabled={disabled}
          aria-invalid={isError ? "true" : undefined}
          className="w-full bg-transparent border-none outline-none text-inherit text-sm focus:ring-0 appearance-none cursor-pointer pr-6 py-1"
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.length > 0
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        <span className="pointer-events-none absolute right-2.5 flex items-center ux4g-text-neutral-tertiary">
          <Icon name="arrow_drop_down" size="sm" color="inherit" aria-hidden="true" />
        </span>
      </div>
    );
  }
);

Select.displayName = "Select";
