import React, { useId } from "react";

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, hint, options, placeholder, id, className = "", ...props }, ref) => {
    const generatedId = useId();
    const selectId = id || generatedId;
    const errorId = `${selectId}-error`;
    const hintId = `${selectId}-hint`;

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label htmlFor={selectId} className="block text-sm font-medium text-slate-800">
            {label}
            {props.required && <span className="text-red-500 ml-1" aria-hidden="true">*</span>}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          className={`w-full px-3 py-2 text-sm bg-white border rounded-md shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 ${
            error
              ? "border-red-400 text-red-900 focus:border-red-500 focus:ring-red-500"
              : "border-slate-300 text-slate-900 focus:border-blue-600 focus:ring-blue-600"
          } disabled:bg-slate-50 disabled:text-slate-500 disabled:cursor-not-allowed ${className}`}
          {...props}
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((opt) => (
            <option key={String(opt.value)} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <p id={errorId} className="text-xs text-red-600 font-medium">
            {error}
          </p>
        )}
        {!error && hint && (
          <p id={hintId} className="text-xs text-slate-500">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";
