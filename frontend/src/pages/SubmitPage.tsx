import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileCheck,
  KeyRound,
  Lock,
  RefreshCw,
  Send,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import {
  getSubmissionGate,
  getSubmissionReceipt,
  requestDeclarationOtp,
  submitAnnualData,
} from "../api/submissions";
import type {
  SubmissionGateResponse,
  SubmissionReceiptResponse,
} from "../types/submissions";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { SubmitGateAlert, LockedDataAlert } from "../components/ux4g";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { EmptyState } from "../components/ui/EmptyState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function SubmitPage() {
  useDocumentTitle("Final Data Submission");
  const { user } = useAuth();
  const institutionId = user?.institution_id ?? 1;
  const isCollegeAdmin = user?.role === "college_admin";

  // State
  const [academicYear, setAcademicYear] = useState<string>("2026-27");
  const [gateData, setGateData] = useState<SubmissionGateResponse | null>(null);
  const [receiptData, setReceiptData] = useState<SubmissionReceiptResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Declaration & OTP State
  const [declarationConfirmed, setDeclarationConfirmed] = useState<boolean>(false);
  const [declarationText] = useState<string>(
    "I confirm this data is correct and complete as authorized by the head of the institution."
  );
  const [otpCode, setOtpCode] = useState<string>("");
  const [otpRequested, setOtpRequested] = useState<boolean>(false);
  const [otpRecipient, setOtpRecipient] = useState<string>("");
  const [isRequestingOtp, setIsRequestingOtp] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [copiedReceipt, setCopiedReceipt] = useState<boolean>(false);

  const fetchGateStatus = useCallback(
    async (showLoading = true) => {
      if (showLoading) setIsLoading(true);
      else setIsRefreshing(true);
      setErrorMessage(null);
      setSubmitError(null);

      try {
        const res = await getSubmissionGate(institutionId, academicYear);
        setGateData(res);

        if (res.is_locked) {
          try {
            const r = await getSubmissionReceipt(institutionId, academicYear);
            setReceiptData(r);
          } catch {
            // Receipt endpoint might fallback to gate data
          }
        } else {
          setReceiptData(null);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load submission gate status.";
        setErrorMessage(msg);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [institutionId, academicYear]
  );

  useEffect(() => {
    fetchGateStatus(true);
  }, [fetchGateStatus]);

  const handleRequestOtp = async () => {
    setIsRequestingOtp(true);
    setSubmitError(null);
    try {
      const res = await requestDeclarationOtp(institutionId, academicYear);
      setOtpRequested(true);
      setOtpRecipient(res.recipient);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to request declaration OTP.";
      setSubmitError(msg);
    } finally {
      setIsRequestingOtp(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!declarationConfirmed || !otpCode.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const receipt = await submitAnnualData(institutionId, {
        academic_year: academicYear,
        confirmed_declaration: declarationConfirmed,
        declaration_text: declarationText,
        otp_code: otpCode.trim(),
      });
      setReceiptData(receipt);
      await fetchGateStatus(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submission failed. Please check blockers.";
      setSubmitError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyReceiptToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedReceipt(true);
    setTimeout(() => setCopiedReceipt(false), 2500);
  };

  const isSubmissionFinalized = Boolean(receiptData || gateData?.is_locked);
  const displayReceiptNo = receiptData?.receipt_no || gateData?.receipt_no || "REC-PENDING";
  const displayInstitutionName = receiptData?.institution_name || gateData?.institution_name || "";
  const displayAicteId = receiptData?.aicte_id || gateData?.aicte_id || "";
  const displayYear = receiptData?.academic_year || gateData?.academic_year || academicYear;
  const displayStatus = receiptData?.status || gateData?.current_status || "submitted";
  const displaySubmittedAt = receiptData?.submitted_at || gateData?.submitted_at || null;
  const displaySubmittedBy = receiptData?.submitted_by_email || gateData?.submitted_by_name || "College Admin";
  const displayTotalStudents = receiptData?.total_students ?? gateData?.total_students ?? 0;
  const displayRegularStudents = receiptData?.regular_students ?? gateData?.total_students ?? 0;
  const displaySuperStudents = receiptData?.supernumerary_students ?? 0;
  const displayCoursesCount = receiptData?.courses_count ?? gateData?.total_courses ?? 0;
  const displayJustifiedCount = receiptData?.justified_exceptions_count ?? gateData?.justified_exceptions_count ?? 0;

  if (isLoading) {
    return (
      <div className="flex h-96 flex-col items-center justify-center space-y-4">
        <LoadingSpinner size="lg" />
        <p className="text-sm font-medium text-slate-500">
          Evaluating submission gate requirements...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header & Year Selector */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Final Data Submission
            </h1>
            {isSubmissionFinalized && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                <Lock className="h-3.5 w-3.5" /> Data Locked
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Reconcile enrolled student records, satisfy compliance gates, and lock records into
            the AICTE Central Repository.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label htmlFor="academic-year-select" className="text-xs font-medium text-slate-500">
            Academic Year:
          </label>
          <select
            id="academic-year-select"
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="2026-27">2026-27 (Current)</option>
            <option value="2025-26">2025-26 (History)</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchGateStatus(false)}
            disabled={isRefreshing}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {errorMessage && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-rose-600" />
            <span className="font-semibold">Error:</span>
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* VIEW 1: DATA IS SUBMITTED AND LOCKED (OFFICIAL RECEIPT CARD) */}
      {isSubmissionFinalized && (
        <div className="space-y-6">
          <div className="overflow-hidden rounded-2xl border border-emerald-200 bg-gradient-to-b from-emerald-50/50 via-white to-white shadow-sm">
            <div className="border-b border-emerald-100 bg-emerald-50/80 px-6 py-4 sm:flex sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Official AICTE Submission Receipt
                  </h2>
                  <p className="text-xs text-emerald-800">
                    National Student Central Repository • Confirmed & Immutable
                  </p>
                </div>
              </div>
              <div className="mt-3 sm:mt-0">
                <Badge
                  variant={
                    displayStatus === "submitted_with_exceptions"
                      ? "warning"
                      : "success"
                  }
                  className="px-3 py-1 text-xs uppercase"
                >
                  {displayStatus === "submitted_with_exceptions"
                    ? "Submitted With Exceptions"
                    : "Submitted Clean"}
                </Badge>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Receipt Number Highlight */}
              <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <span className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                    Acknowledgement Receipt Number
                  </span>
                  <div className="font-mono text-xl font-bold tracking-tight text-slate-900">
                    {displayReceiptNo}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyReceiptToClipboard(displayReceiptNo)}
                  className="flex items-center gap-1.5 self-start sm:self-auto"
                >
                  {copiedReceipt ? (
                    <>
                      <Check className="h-4 w-4 text-emerald-600" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4" />
                      Copy Receipt No
                    </>
                  )}
                </Button>
              </div>

              {/* Institution and Submission Details */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                  <div className="text-xs font-medium text-slate-500">Institution</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {displayInstitutionName}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    AICTE ID: {displayAicteId}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                  <div className="text-xs font-medium text-slate-500">Submitted On</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {displaySubmittedAt
                      ? new Date(displaySubmittedAt).toLocaleString("en-IN", {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })
                      : "On File"}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    Academic Year: {displayYear}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                  <div className="text-xs font-medium text-slate-500">Submitted By</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900 truncate">
                    {displaySubmittedBy}
                  </div>
                  <div className="mt-0.5 text-xs text-emerald-600 font-medium">
                    Verified via OTP
                  </div>
                </div>

                <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                  <div className="text-xs font-medium text-slate-500">Repository Status</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {displayStatus === "submitted_with_exceptions"
                      ? "Under AICTE Review"
                      : "Central Verification Active"}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    Immutable Record
                  </div>
                </div>
              </div>

              {/* Student and Quota Breakdown */}
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                  Verified Enrollment Breakdown
                </h3>
                <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
                  <div className="border-r border-slate-100 pr-4">
                    <span className="text-xs text-slate-500">Total Enrolled</span>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {displayTotalStudents}
                    </p>
                  </div>
                  <div className="border-r border-slate-100 pr-4">
                    <span className="text-xs text-slate-500">Regular Seats</span>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {displayRegularStudents}
                    </p>
                  </div>
                  <div className="border-r border-slate-100 pr-4">
                    <span className="text-xs text-slate-500">Supernumerary</span>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {displaySuperStudents}
                    </p>
                  </div>
                  <div className="border-r border-slate-100 pr-4">
                    <span className="text-xs text-slate-500">Approved Courses</span>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {displayCoursesCount}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Exceptions Justified</span>
                    <p className="mt-1 text-2xl font-bold text-indigo-600">
                      {displayJustifiedCount}
                    </p>
                  </div>
                </div>
              </div>

              {/* Official Declaration Note */}
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start gap-3">
                  <FileCheck className="h-5 w-5 text-indigo-600 mt-0.5" />
                  <div className="text-xs text-slate-600">
                    <p className="font-semibold text-slate-800">Affirmed Declaration:</p>
                    <p className="italic mt-0.5">
                      "{receiptData?.declaration_text || gateData?.declaration_ref || declarationText}"
                    </p>
                  </div>
                </div>
              </div>

              {/* Notice regarding post-submission change requests */}
              <LockedDataAlert
                academicYear={displayYear}
                title="Central Repository Locked"
              >
                <p className="text-xs">
                  All student records for academic year {displayYear} are strictly locked and read-only.
                  Any subsequent modifications or status transitions (e.g. Withdrawal, Branch Transfer) require
                  a formal Change Request submitted through the AICTE Approvals portal.
                </p>
              </LockedDataAlert>

              {/* Navigation Actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <Link to="/college/students">
                    <Button variant="outline" size="sm" className="flex items-center gap-1.5">
                      <Users className="h-4 w-4" />
                      View Enrolled Students Directory
                    </Button>
                  </Link>
                  <Link to={`/college/submissions/${receiptData?.submission_id || gateData?.submission_id || 1}`}>
                    <Button variant="outline" size="sm" className="flex items-center gap-1.5 text-blue-700">
                      <FileCheck className="h-4 w-4" />
                      Formal Receipt Page
                    </Button>
                  </Link>
                </div>
                <Link to="/college/validation">
                  <Button variant="ghost" size="sm" className="flex items-center gap-1.5 text-indigo-600">
                    Review Validation Flags Archive
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 2: DRAFT SUBMISSION (GATE CHECK & ACTIONABLE BLOCKERS) */}
      {!isSubmissionFinalized && gateData && (
        <div className="space-y-6">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Enrolled
              </span>
              <p className="mt-2 text-3xl font-extrabold text-slate-900">
                {gateData.total_students}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Across {gateData.total_courses} approved course(s)
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-rose-600 uppercase tracking-wider">
                Open Data Errors
              </span>
              <p className="mt-2 text-3xl font-extrabold text-rose-600">
                {gateData.open_errors_count}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Must be corrected in records
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-amber-600 uppercase tracking-wider">
                Unjustified Exceptions
              </span>
              <p className="mt-2 text-3xl font-extrabold text-amber-600">
                {gateData.unjustified_exceptions_count + gateData.unjustified_warnings_count}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Requires official justification
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">
                Justified Exceptions
              </span>
              <p className="mt-2 text-3xl font-extrabold text-emerald-600">
                {gateData.justified_exceptions_count + gateData.justified_warnings_count}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Evidence document attached
              </p>
            </div>
          </div>

          {/* Gate Status Banner */}
          <SubmitGateAlert
            canSubmit={gateData.can_submit}
            openErrorsCount={gateData.open_errors_count}
            unjustifiedExceptionsCount={gateData.unjustified_exceptions_count}
            unjustifiedWarningsCount={gateData.unjustified_warnings_count}
            title={
              gateData.can_submit
                ? "Submit Gate Passed: Ready for Final Submission"
                : `Submission Gate Blocked (${gateData.blockers.length} Blocker(s))`
            }
          >
            {gateData.can_submit ? (
              <div className="space-y-1">
                <p className="text-sm font-medium">
                  {gateData.gate_reason}
                </p>
                <div className="pt-1">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border border-current">
                    Target Repository Status:{" "}
                    {gateData.target_status === "submitted_with_exceptions"
                      ? "Submitted with Exceptions"
                      : "Submitted Clean"}
                  </span>
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm font-medium">
                  {gateData.gate_reason}
                </p>
                <p className="text-xs opacity-90">
                  Per AICTE verification guidelines (SPEC.md Section 10), final data submission
                  is locked until all underlying data errors are resolved and compliance
                  exceptions are officially justified.
                </p>
              </div>
            )}
          </SubmitGateAlert>

          {/* BLOCKERS TABLE (IF ANY EXIST) */}
          {gateData.blockers.length > 0 && (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 bg-slate-50/80 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                      Actionable Blocker List ({gateData.blockers.length})
                    </h3>
                    <p className="text-xs text-slate-500">
                      Click the action link on each blocker to resolve the error or write a justification.
                    </p>
                  </div>
                  <Badge variant="danger" className="px-2.5 py-0.5 text-xs font-semibold">
                    {gateData.blockers.length} Blocking Issue{gateData.blockers.length === 1 ? "" : "s"}
                  </Badge>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                    <tr>
                      <th className="px-6 py-3">Severity</th>
                      <th className="px-6 py-3">Rule & Blocker</th>
                      <th className="px-6 py-3">Target Record</th>
                      <th className="px-6 py-3">Resolution Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {gateData.blockers.map((b, idx) => (
                      <tr key={`${b.rule_code}-${b.flag_id ?? idx}`} className="hover:bg-slate-50/60">
                        <td className="px-6 py-4 align-top">
                          <FlagBadge level={b.level} />
                        </td>
                        <td className="px-6 py-4 align-top max-w-md">
                          <div className="font-mono text-xs font-bold text-slate-900">
                            {b.rule_code}
                          </div>
                          <div className="text-sm font-medium text-slate-800 mt-0.5">
                            {b.message}
                          </div>
                          {b.fix_hint && (
                            <div className="text-xs text-indigo-700 font-medium mt-1">
                              Fix Hint: {b.fix_hint}
                            </div>
                          )}
                          <div className="text-[11px] text-slate-400 mt-1 italic">
                            Reason: {b.reason}
                          </div>
                        </td>
                        <td className="px-6 py-4 align-top">
                          {b.student_name ? (
                            <div>
                              <div className="font-semibold text-slate-900">{b.student_name}</div>
                              <div className="font-mono text-xs text-slate-500">
                                APAAR: {b.apaar_id}
                              </div>
                              <div className="text-xs text-slate-400">
                                ID: {b.enrolment_no} • {b.course_name}
                              </div>
                            </div>
                          ) : b.course_name ? (
                            <div>
                              <div className="font-semibold text-slate-900">{b.course_name}</div>
                              <div className="text-xs text-slate-400">Institutional Quota</div>
                            </div>
                          ) : (
                            <div className="text-xs text-slate-400">Institutional Data</div>
                          )}
                        </td>
                        <td className="px-6 py-4 align-top">
                          <Link to={b.target_link}>
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                            >
                              Resolve
                              <ExternalLink className="h-3.5 w-3.5" />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* SUBMISSION AFFIRMATION & OTP GATE (WHEN CAN SUBMIT) */}
          {gateData.can_submit && (
            <div className="overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-sm">
              <div className="border-b border-indigo-100 bg-gradient-to-r from-indigo-50/80 via-white to-white px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
                    <KeyRound className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Statutory Declaration & Verification Confirmation
                    </h3>
                    <p className="text-xs text-slate-500">
                      Step 2 of 2: Confirm declaration and verify mock OTP to lock annual records.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Official Declaration Textbox */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Statutory Institutional Declaration
                  </span>
                  <p className="mt-2 text-sm italic text-slate-700">
                    "{declarationText}"
                  </p>
                  <label className="mt-4 flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={declarationConfirmed}
                      onChange={(e) => setDeclarationConfirmed(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-xs font-medium text-slate-700 select-none">
                      I hereby solemnly affirm that all student enrollment details, APAAR IDs, and quota
                      declarations for academic year {gateData.academic_year} are verified against college admission
                      registers and AICTE approval orders.
                    </span>
                  </label>
                </div>

                {/* Mock OTP Section */}
                <div className="space-y-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <label htmlFor="otp-input" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                        Admin Declaration OTP Code
                      </label>
                      <p className="text-xs text-slate-400">
                        Dispatched via registered contact to verify identity. (Demo mode: viewable in dev outbox)
                      </p>
                    </div>

                    {!otpRequested ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleRequestOtp}
                        disabled={isRequestingOtp}
                        className="flex items-center gap-1.5 self-start sm:self-auto"
                      >
                        <Send className="h-3.5 w-3.5" />
                        {isRequestingOtp ? "Requesting OTP..." : "Request Declaration OTP"}
                      </Button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleRequestOtp}
                        disabled={isRequestingOtp}
                        className="text-xs font-semibold text-indigo-600 hover:underline"
                      >
                        Resend OTP code
                      </button>
                    )}
                  </div>

                  {otpRequested && (
                    <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                      <span>
                        Verification OTP delivered to <span className="font-bold">{otpRecipient}</span>.
                        (Valid for 5 minutes)
                      </span>
                    </div>
                  )}

                  <input
                    id="otp-input"
                    type="text"
                    maxLength={6}
                    placeholder="Enter 6-digit OTP"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    disabled={!otpRequested}
                    className="w-full max-w-xs rounded-xl border border-slate-300 px-4 py-2.5 font-mono text-lg tracking-widest text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-400"
                  />
                </div>

                {submitError && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
                      <span>{submitError}</span>
                    </div>
                  </div>
                )}

                {/* Role Restriction Notice */}
                {!isCollegeAdmin && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
                    <div className="flex items-center gap-2 font-semibold">
                      <Lock className="h-4 w-4 text-amber-600" />
                      <span>Role Restriction: College Admin Only</span>
                    </div>
                    <p className="mt-1 text-amber-800">
                      Only users with the <span className="font-mono font-bold">college_admin</span> role
                      are authorized to execute final submission. Your current role is{" "}
                      <span className="font-mono font-bold">{user?.role}</span>.
                    </p>
                  </div>
                )}

                {/* Final Submit Action Button */}
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    disabled={
                      !isCollegeAdmin ||
                      !declarationConfirmed ||
                      otpCode.trim().length !== 6 ||
                      isSubmitting
                    }
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-md"
                  >
                    <Lock className="h-4 w-4" />
                    {isSubmitting
                      ? "Submitting & Locking Data..."
                      : `Submit & Lock Data (${
                          gateData.target_status === "submitted_with_exceptions"
                            ? "With Exceptions"
                            : "Clean"
                        })`}
                  </Button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Empty State when no data is loaded */}
      {!gateData && !isLoading && (
        <EmptyState
          title="No Submission Gate Data"
          description="Could not locate submission records for this academic year."
          actionLabel="Try Again"
          onAction={() => fetchGateStatus(true)}
        />
      )}
    </div>
  );
}
