import React from "react";

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label: React.ReactNode;
  size?: "sm" | "md" | "lg";
  isError?: boolean;
  indeterminate?: boolean;
}

/**
 * UX4G Checkbox Component
 * Uses `.ux4g-checkbox ux4g-checkbox-{size}` and `.ux4g-checkbox-error`.
 */
export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  (
    {
      label,
      size = "md",
      isError = false,
      indeterminate = false,
      disabled,
      className = "",
      id,
      ...props
    },
    ref
  ) => {
    const inputRef = React.useRef<HTMLInputElement | null>(null);

    React.useEffect(() => {
      if (inputRef.current) {
        inputRef.current.indeterminate = indeterminate;
      }
    }, [indeterminate]);

    const handleRef = (node: HTMLInputElement | null) => {
      inputRef.current = node;
      if (typeof ref === "function") {
        ref(node);
      } else if (ref) {
        (ref as React.MutableRefObject<HTMLInputElement | null>).current = node;
      }
    };

    return (
      <label
        className={`ux4g-checkbox ux4g-checkbox-${size} ${isError ? "ux4g-checkbox-error" : ""} ${
          disabled ? "opacity-50 cursor-not-allowed" : ""
        } ${className}`.trim()}
      >
        <input
          ref={handleRef}
          type="checkbox"
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

Checkbox.displayName = "Checkbox";
