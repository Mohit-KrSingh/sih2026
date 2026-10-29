import React from "react";

export interface FormFieldProps {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * UX4G Form Field Component
 *
 * Binds label, hint text, and error messages to an input control with accessible
 * `id`, `htmlFor`, `aria-describedby`, and `aria-invalid` attributes.
 */
export const FormField: React.FC<FormFieldProps> = ({
  id,
  label,
  required = false,
  hint,
  error,
  children,
  className = "",
}) => {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  // Clone single React element child to automatically attach id, describedBy, and error state
  const renderedChild = React.isValidElement(children)
    ? React.cloneElement(children as React.ReactElement<any>, {
        id,
        "aria-describedby": describedBy,
        "aria-invalid": error ? "true" : undefined,
        state: error ? "error" : (children.props as any).state || "default",
      })
    : children;

  return (
    <div className={`w-full flex flex-col gap-1.5 ${className}`.trim()}>
      <div className="flex items-center justify-between">
        <label
          htmlFor={id}
          className="text-sm font-semibold select-none flex items-center gap-1"
        >
          <span>{label}</span>
          {required && (
            <span className="ux4g-text-error font-bold" aria-hidden="true">
              *
            </span>
          )}
        </label>
        {required && (
          <span className="text-xs ux4g-text-neutral-secondary font-normal select-none">
            Required
          </span>
        )}
      </div>

      {hint && (
        <p id={hintId} className="text-xs ux4g-text-neutral-secondary">
          {hint}
        </p>
      )}

      {renderedChild}

      {error && (
        <p id={errorId} role="alert" className="text-xs font-semibold ux4g-text-error">
          {error}
        </p>
      )}
    </div>
  );
};
