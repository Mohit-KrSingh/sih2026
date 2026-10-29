import React from "react";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  size?: "sm" | "md" | "lg";
  state?: "default" | "error" | "success" | "warning";
  fullWidth?: boolean;
}

/**
 * UX4G Textarea Component
 * Uses `.ux4g-input ux4g-input-{state}` with `<textarea className="ux4g-textarea">`.
 */
export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      size = "md",
      state = "default",
      fullWidth = true,
      disabled,
      className = "",
      rows = 4,
      id,
      ...props
    },
    ref
  ) => {
    const isError = state === "error";

    return (
      <div
        className={`ux4g-input ux4g-input-${size} ux4g-input-${state} p-2 ${
          fullWidth ? "w-full" : ""
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`.trim()}
      >
        <textarea
          ref={ref}
          id={id}
          rows={rows}
          disabled={disabled}
          aria-invalid={isError ? "true" : undefined}
          className="ux4g-textarea w-full bg-transparent border-none outline-none text-inherit text-sm resize-y focus:ring-0"
          {...props}
        />
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
