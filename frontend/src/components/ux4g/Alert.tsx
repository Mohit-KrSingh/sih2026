import React from "react";
import { Icon } from "./Icon";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "success" | "warning" | "error";
  title?: string;
  onDismiss?: () => void;
  dismissLabel?: string;
  showIcon?: boolean;
}

/**
 * UX4G Alert Component
 * Uses `.ux4g-alert ux4g-alert-{variant}`.
 */
export const Alert: React.FC<AlertProps> = ({
  variant = "info",
  title,
  onDismiss,
  dismissLabel = "Dismiss alert",
  showIcon = true,
  className = "",
  children,
  ...props
}) => {
  const iconName = {
    info: "info",
    success: "check_circle",
    warning: "warning",
    error: "error",
  }[variant];

  const role = variant === "error" || variant === "warning" ? "alert" : "status";

  return (
    <div
      role={role}
      className={`ux4g-alert ux4g-alert-${variant} rounded-md ${className}`.trim()}
      {...props}
    >
      {showIcon && (
        <span className="ux4g-alert-icon shrink-0">
          <Icon name={iconName} size="md" color="inherit" aria-hidden="true" />
        </span>
      )}
      <div className="flex-1 min-w-0">
        {title && <p className="font-semibold text-sm mb-0.5">{title}</p>}
        <div className="text-sm">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label={dismissLabel}
          className="shrink-0 p-1 rounded hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-offset-1"
        >
          <Icon name="close" size="sm" color="inherit" aria-hidden="true" />
        </button>
      )}
    </div>
  );
};

export interface SubmitGateAlertProps extends Omit<AlertProps, "variant" | "title"> {
  canSubmit: boolean;
  title?: string;
  openErrorsCount?: number;
  unjustifiedExceptionsCount?: number;
  unjustifiedWarningsCount?: number;
  blockers?: string[];
  actionLabel?: string;
  onAction?: () => void;
}

/**
 * Alert for submit gate results (Passed, Passed with Exceptions, Blocked).
 * Adheres to SPEC §10 and REBRAND_TASKS R08.
 */
export const SubmitGateAlert: React.FC<SubmitGateAlertProps> = ({
  canSubmit,
  title,
  openErrorsCount = 0,
  unjustifiedExceptionsCount = 0,
  unjustifiedWarningsCount = 0,
  blockers,
  actionLabel,
  onAction,
  children,
  className = "",
  ...props
}) => {
  const hasExceptionsOnly = canSubmit && (unjustifiedExceptionsCount > 0 || unjustifiedWarningsCount > 0);
  const variant: AlertProps["variant"] = canSubmit ? (hasExceptionsOnly ? "warning" : "success") : "error";

  const defaultTitle = canSubmit
    ? (hasExceptionsOnly
        ? "Submit Gate Passed with Exceptions (AICTE Review Required)"
        : "Submit Gate Passed: Ready for Final Submission")
    : "Submit Gate Blocked: Outstanding Compliance Issues";

  return (
    <Alert
      variant={variant}
      title={title || defaultTitle}
      data-testid="submit-gate-alert"
      className={className}
      {...props}
    >
      {children ? (
        children
      ) : canSubmit ? (
        <div className="space-y-1">
          <p>
            {hasExceptionsOnly
              ? "All open exceptions carry approved justifications. Records will enter the AICTE review queue upon declaration."
              : "All courses satisfy approved intake limits and all validation rules passed. Institution admin may complete the statutory declaration."}
          </p>
          {actionLabel && onAction && (
            <button
              type="button"
              onClick={onAction}
              className="mt-2 text-xs font-semibold underline underline-offset-2 hover:opacity-80"
            >
              {actionLabel}
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-1.5">
          <p>
            Final submission is blocked until all format errors are corrected and any compliance exceptions are justified:
          </p>
          <ul className="list-disc pl-5 text-xs space-y-0.5">
            {openErrorsCount > 0 && (
              <li>
                <strong>{openErrorsCount}</strong> open error(s) must be fixed in student records.
              </li>
            )}
            {unjustifiedExceptionsCount > 0 && (
              <li>
                <strong>{unjustifiedExceptionsCount}</strong> compliance exception(s) require written justifications and supporting documents.
              </li>
            )}
            {unjustifiedWarningsCount > 0 && (
              <li>
                <strong>{unjustifiedWarningsCount}</strong> warning(s) require written justifications.
              </li>
            )}
          </ul>
          {blockers && blockers.length > 0 && (
            <ul className="list-disc pl-5 text-xs space-y-0.5 mt-1 opacity-90">
              {blockers.slice(0, 3).map((b, i) => (
                <li key={i}>{b}</li>
              ))}
              {blockers.length > 3 && (
                <li className="italic">+ {blockers.length - 3} additional blockers</li>
              )}
            </ul>
          )}
        </div>
      )}
    </Alert>
  );
};

export interface LockedDataAlertProps extends Omit<AlertProps, "variant"> {
  academicYear?: string;
  receiptNo?: string;
  correctionUrl?: string;
}

/**
 * Alert for locked / immutable central repository student records.
 * Adheres to SPEC §6, §10, and REBRAND_TASKS R08.
 */
export const LockedDataAlert: React.FC<LockedDataAlertProps> = ({
  academicYear,
  receiptNo,
  correctionUrl = "/college/change-requests",
  title = "Central Repository Locked (Read-Only)",
  children,
  className = "",
  ...props
}) => {
  return (
    <Alert
      variant="info"
      title={title}
      data-testid="locked-data-alert"
      className={className}
      {...props}
    >
      {children ? (
        children
      ) : (
        <div className="space-y-1">
          <p>
            Student enrollment records{academicYear ? ` for academic year ${academicYear}` : ""} are permanently locked and read-only
            {receiptNo ? ` under official acknowledgement receipt ${receiptNo}` : ""}.
          </p>
          <p className="text-xs opacity-90">
            Post-submission modifications (such as student withdrawal, transfer, or correction) cannot be edited directly and require a formal{" "}
            <a href={correctionUrl} className="underline underline-offset-2 font-medium hover:opacity-80">
              Change Request
            </a>{" "}
            submitted for AICTE approval.
          </p>
        </div>
      )}
    </Alert>
  );
};

export interface SuspendedApprovalAlertProps extends Omit<AlertProps, "variant"> {
  status?: "suspended" | "withdrawn" | "expired" | string;
  institutionName?: string;
  reason?: string;
}

/**
 * Read-only alert banner for institutions with suspended, withdrawn, or expired AICTE approval.
 * Adheres to SPEC §6, §11, and REBRAND_TASKS R08.
 */
export const SuspendedApprovalAlert: React.FC<SuspendedApprovalAlertProps> = ({
  status = "suspended",
  institutionName,
  reason,
  title,
  children,
  className = "",
  ...props
}) => {
  const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
  const defaultTitle = `AICTE Approval ${statusLabel} — Read-Only Mode`;

  return (
    <Alert
      variant="error"
      title={title || defaultTitle}
      data-testid="suspended-approval-alert"
      className={className}
      {...props}
    >
      {children ? (
        children
      ) : (
        <div className="space-y-1">
          <p>
            {institutionName ? `${institutionName}'s` : "This institution's"} AICTE approval status is currently{" "}
            <strong className="uppercase">{status}</strong>. New student data uploads, single-entry additions, and seat declaration updates are strictly blocked (HTTP 403).
          </p>
          {reason && (
            <p className="text-xs">
              <strong>Official Note:</strong> {reason}
            </p>
          )}
          <p className="text-xs opacity-90">
            All existing institutional records remain in read-only mode for audit compliance. Contact the AICTE Regional Approval Bureau for reinstatement inquiries.
          </p>
        </div>
      )}
    </Alert>
  );
};

export interface DemoModeAlertProps extends Omit<AlertProps, "variant"> {
  customNotice?: string;
}

/**
 * Banner alert indicating the demonstration mode and simulated external dependencies.
 * Adheres to SPEC §2 Rule 10 and REBRAND_TASKS R08.
 */
export const DemoModeAlert: React.FC<DemoModeAlertProps> = ({
  title = "Demonstration Environment (Demo Mode)",
  customNotice,
  children,
  className = "",
  ...props
}) => {
  return (
    <Alert
      variant="info"
      title={title}
      data-testid="demo-mode-alert"
      className={className}
      {...props}
    >
      {children ? (
        children
      ) : (
        <p>
          {customNotice ||
            "Demo mode active: APAAR registry lookups, DigiLocker verification, and OTP SMS/email dispatch are simulated. EduTrace is a hackathon prototype and not an official government service."}
        </p>
      )}
    </Alert>
  );
};
