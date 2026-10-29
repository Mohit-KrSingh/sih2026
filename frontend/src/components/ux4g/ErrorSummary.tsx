import React, { useEffect, useRef } from "react";
import { Icon } from "./Icon";

export interface ErrorItem {
  fieldId: string;
  message: string;
}

export interface ErrorSummaryProps {
  errors: ErrorItem[];
  title?: string;
  autoFocus?: boolean;
  className?: string;
}

/**
 * UX4G Error Summary Component
 *
 * Placed at the top of a form when validation errors occur.
 * Focus is programmatically moved to this component, and each item
 * links directly to the corresponding invalid input field.
 */
export const ErrorSummary: React.FC<ErrorSummaryProps> = ({
  errors,
  title = "There is a problem with your submission",
  autoFocus = true,
  className = "",
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoFocus && errors.length > 0 && containerRef.current) {
      containerRef.current.focus();
    }
  }, [autoFocus, errors]);

  if (errors.length === 0) return null;

  const handleLinkClick = (e: React.MouseEvent<HTMLAnchorElement>, fieldId: string) => {
    e.preventDefault();
    const targetElement = document.getElementById(fieldId);
    if (targetElement) {
      targetElement.focus();
      targetElement.scrollIntoView?.({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div
      ref={containerRef}
      id="error-summary"
      data-testid="error-summary"
      tabIndex={-1}
      role="alert"
      aria-labelledby="error-summary-heading"
      className={`ux4g-alert ux4g-alert-error rounded-md p-4 outline-none focus:ring-2 ${className}`.trim()}
    >
      <div className="w-full">
        <div className="flex items-center gap-2 mb-2">
          <Icon name="error" size="md" color="error" aria-hidden="true" />
          <h2 id="error-summary-heading" className="text-base font-bold">
            {title}
          </h2>
        </div>
        <ul className="list-disc list-inside space-y-1 text-sm pl-2">
          {errors.map((err, idx) => (
            <li key={idx}>
              <a
                href={`#${err.fieldId}`}
                onClick={(e) => handleLinkClick(e, err.fieldId)}
                className="font-medium underline hover:opacity-80 focus:outline-none focus:ring-1 rounded px-0.5"
              >
                {err.message}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
