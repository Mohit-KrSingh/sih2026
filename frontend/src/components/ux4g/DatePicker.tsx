import React from "react";
import { Icon } from "./Icon";

export interface DatePickerProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  size?: "sm" | "md" | "lg";
  state?: "default" | "error" | "success" | "warning";
  fullWidth?: boolean;
}

/**
 * UX4G Date Picker Component
 * Uses native date input within UX4G input container with calendar icon.
 */
export const DatePicker = React.forwardRef<HTMLInputElement, DatePickerProps>(
  (
    {
      size = "md",
      state = "default",
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
        className={`ux4g-input ux4g-input-${size} ux4g-input-${state} relative flex items-center pr-2 ${
          fullWidth ? "w-full" : ""
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`.trim()}
      >
        <span className="ux4g-input-leading-icon flex items-center shrink-0 ux4g-text-neutral-tertiary">
          <Icon name="calendar_today" size="sm" color="inherit" aria-hidden="true" />
        </span>
        <input
          ref={ref}
          type="date"
          id={id}
          disabled={disabled}
          aria-invalid={isError ? "true" : undefined}
          className="w-full bg-transparent border-none outline-none text-inherit text-sm focus:ring-0 cursor-pointer"
          {...props}
        />
      </div>
    );
  }
);

DatePicker.displayName = "DatePicker";
