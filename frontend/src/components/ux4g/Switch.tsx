import React from "react";

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: React.ReactNode;
  size?: "sm" | "md" | "lg";
}

/**
 * UX4G Switch Component
 * Uses `.ux4g-switch ux4g-switch-{size}` with `<input type="checkbox" role="switch">`.
 */
export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ label, size = "md", disabled, className = "", id, ...props }, ref) => {
    return (
      <label
        className={`ux4g-switch ux4g-switch-${size} ${
          disabled ? "opacity-50 cursor-not-allowed" : ""
        } ${className}`.trim()}
      >
        <input
          ref={ref}
          type="checkbox"
          role="switch"
          id={id}
          disabled={disabled}
          className="cursor-pointer disabled:cursor-not-allowed"
          {...props}
        />
        <span className="text-sm select-none">{label}</span>
      </label>
    );
  }
);

Switch.displayName = "Switch";
