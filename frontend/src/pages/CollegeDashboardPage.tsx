import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  getInstitutionSeatDeclarations,
  type CourseSummaryResponse,
  type InstitutionSeatDeclarationResponse,
} from "../api/seats";
import {
  getInstitutionFlags,
} from "../api/justifications";
import type {
  InstitutionFlagsListResponse,
  ValidationFlagDetail,
} from "../types/validation";
import {
  getSubmissionGate,
  getSubmissionReceipt,
} from "../api/submissions";
import type {
  SubmissionGateResponse,
  SubmissionReceiptResponse,
} from "../types/submissions";
import {
  fetchCollegeQueries,
} from "../api/review";
import type { CollegeQueryResponse } from "../types/review";
import {
  getInstitutionNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  type NotificationItem,
} from "../api/institutions";
import {
  downloadCollegeAccreditation,
  downloadCollegeSubmission,
} from "../api/reports";
import { Button } from "../components/ui/Button";
import { FlagBadge, RoleBadge } from "../components/ui/Badge";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/Table";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bell,
  Building2,
  Check,
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  FileCheck,
  FileText,
  FileUp,
  HelpCircle,
  Layers,
  Lock,
  MessageSquare,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  UserPlus,
  Users,
} from "lucide-react";

export function CollegeDashboardPage() {
  useDocumentTitle("College Portal Dashboard");
  const { user } = useAuth();
  const institutionId = user?.institution_id ?? 1;

  // Academic Year State
  const [academicYear, setAcademicYear] = useState<string>("2026-27");

  // Core Data States
  const [seatData, setSeatData] = useState<InstitutionSeatDeclarationResponse | null>(null);
  const [flagsData, setFlagsData] = useState<InstitutionFlagsListResponse | null>(null);
  const [gateData, setGateData] = useState<SubmissionGateResponse | null>(null);
  const [receiptData, setReceiptData] = useState<SubmissionReceiptResponse | null>(null);
  const [queries, setQueries] = useState<CollegeQueryResponse[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  // UI Control States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedFlagLevel, setSelectedFlagLevel] = useState<string>("all");
  const [selectedNotifFilter, setSelectedNotifFilter] = useState<"all" | "unread">("all");
  const [copiedReceipt, setCopiedReceipt] = useState<boolean>(false);
  const [markingReadId, setMarkingReadId] = useState<number | null>(null);
  const [downloadingReport, setDownloadingReport] = useState<string | null>(null);

  const handleDownloadSubmission = async (fmt: "pdf" | "xlsx" | "csv" = "pdf") => {
    setDownloadingReport(`sub_${fmt}`);
    try {
      await downloadCollegeSubmission(institutionId, fmt, academicYear);
    } catch (err: any) {
      alert(err?.message || "Failed to download submission report");
    } finally {
      setDownloadingReport(null);
    }
  };

  const handleDownloadAccreditation = async () => {
    setDownloadingReport("accreditation");
    try {
      await downloadCollegeAccreditation(institutionId, "pdf", academicYear);
    } catch (err: any) {
      alert(err?.message || "Failed to download accreditation snapshot");
    } finally {
      setDownloadingReport(null);
    }
  };

  // Load all dashboard components in parallel
  const loadDashboardData = useCallback(
    async (showLoadingSpinner: boolean = true) => {
      if (showLoadingSpinner) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setErrorMessage(null);

      try {
        const [seatsRes, flagsRes, gateRes, queriesRes, notifsRes] = await Promise.all([
          getInstitutionSeatDeclarations(institutionId, academicYear).catch(() => null),
          getInstitutionFlags(institutionId, { academic_year: academicYear }).catch(() => null),
          getSubmissionGate(institutionId, academicYear).catch(() => null),
          fetchCollegeQueries(institutionId, { academic_year: academicYear }).catch(() => ({ total: 0, items: [] })),
          getInstitutionNotifications(institutionId, 50).catch(() => []),
        ]);

        setSeatData(seatsRes);
        setFlagsData(flagsRes);
        setGateData(gateRes);
        setQueries(queriesRes?.items ?? []);
        setNotifications(notifsRes);

        // If locked/submitted, attempt to fetch official receipt details
        if (gateRes?.is_locked) {
          try {
            const receiptRes = await getSubmissionReceipt(institutionId, academicYear);
            setReceiptData(receiptRes);
          } catch {
            setReceiptData(null);
          }
        } else {
          setReceiptData(null);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load dashboard data.";
        setErrorMessage(msg);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [institutionId, academicYear]
  );

  useEffect(() => {
    loadDashboardData(true);
  }, [loadDashboardData]);

  // Copy receipt number to clipboard
  const handleCopyReceipt = (receiptNo: string) => {
    navigator.clipboard.writeText(receiptNo);
    setCopiedReceipt(true);
    setTimeout(() => setCopiedReceipt(false), 2000);
  };

  // Mark single notification as read
  const handleMarkAsRead = async (notifId: number) => {
    try {
      setMarkingReadId(notifId);
      await markNotificationRead(institutionId, notifId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, read_at: new Date().toISOString() } : n))
      );
    } catch {
      // silently ignore or retry
    } finally {
      setMarkingReadId(null);
    }
  };

  // Mark all notifications as read
  const handleMarkAllAsRead = async () => {
    try {
      await markAllNotificationsRead(institutionId);
      const now = new Date().toISOString();
      setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? now })));
    } catch {
      // ignore
    }
  };

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center">
        <LoadingSpinner size="lg" label="Loading college administration dashboard..." />
      </div>
    );
  }

  if (errorMessage && !seatData && !gateData) {
    return (
      <ErrorState
        title="Failed to Load Dashboard"
        message={errorMessage}
        onRetry={() => loadDashboardData(true)}
      />
    );
  }

  // Calculated Metrics
  const courses = seatData?.courses ?? [];
  const totalApprovedIntake = seatData?.total_approved_intake ?? 0;
  const totalAdmitted = seatData?.total_enrolled ?? 0;
  const totalSupernumeraryAllowed = seatData?.total_supernumerary_allowed ?? 0;
  const capacityPercent = totalApprovedIntake > 0 ? Math.round((totalAdmitted / totalApprovedIntake) * 100) : 0;

  // Pending Queries awaiting college response
  const pendingQueries = queries.filter((q) => q.state === "pending");

  // Notifications filtering
  const unreadNotificationsCount = notifications.filter((n) => !n.read_at).length;
  const filteredNotifications = notifications.filter((n) => {
    if (selectedNotifFilter === "unread") return !n.read_at;
    return true;
  });

  // Filtered Flags
  const flagsList = flagsData?.items ?? [];
  const filteredFlags = flagsList.filter((f) => {
    if (selectedFlagLevel === "all") return true;
    return f.level.toLowerCase() === selectedFlagLevel.toLowerCase();
  });

  const errorCount = flagsData?.summary?.error_count ?? 0;
  const exceptionCount = flagsData?.summary?.exception_count ?? 0;
  const warningCount = flagsData?.summary?.warning_count ?? 0;
  const infoCount = flagsData?.summary?.info_count ?? 0;

  // Submission Status
  const isLocked = Boolean(gateData?.is_locked);
  const submissionStatus = gateData?.current_status ?? "draft";
  const receiptNumber = receiptData?.receipt_no || gateData?.receipt_no;

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Header Banner & Academic Year Selector */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
              Institutional Administration Portal
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
              AICTE Approved
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Institutional Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Institution ID: <span className="font-mono font-semibold text-slate-700">#{institutionId}</span> &bull; Logged in as{" "}
            <span className="font-mono font-medium text-slate-700">{user?.email}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Academic Year Selector */}
          <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1">
            <span className="text-xs font-semibold text-slate-500 px-2.5">Year:</span>
            <select
              aria-label="Academic Year"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-white text-xs font-semibold text-slate-800 border border-slate-300 rounded px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="2026-27">2026-27 (Current Cycle)</option>
              <option value="2025-26">2025-26 (Historical Records)</option>
            </select>
          </div>

          <Button
            size="sm"
            variant="outline"
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />}
            onClick={() => loadDashboardData(false)}
            disabled={isRefreshing}
          >
            Refresh
          </Button>

          {user && <RoleBadge role={user.role} />}

          {!isLocked && (
            <Link to="/college/upload">
              <Button size="sm" variant="primary" leftIcon={<FileUp className="w-3.5 h-3.5" />}>
                Upload Data
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* 2. Top-level KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Approved Courses */}
        <div className="p-5 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Approved Courses</span>
            <Building2 className="w-4 h-4 text-blue-500" />
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-3xl font-bold text-slate-900">{courses.length}</p>
            <span className="text-[11px] font-medium text-slate-500">AICTE Affiliated</span>
          </div>
          <p className="text-xs text-slate-500">
            {totalSupernumeraryAllowed > 0 ? `${totalSupernumeraryAllowed} supernumerary quota` : "Standard intake quota"}
          </p>
        </div>

        {/* Approved Intake & Total Admitted */}
        <div className="p-5 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Admitted</span>
            <Users className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-slate-900">{totalAdmitted}</p>
            <span className="text-xs text-slate-500">/ {totalApprovedIntake} quota</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full ${
                capacityPercent > 100 ? "bg-red-500" : capacityPercent >= 80 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(capacityPercent, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className={capacityPercent > 100 ? "text-red-600 font-semibold" : "text-emerald-700 font-medium"}>
              {capacityPercent}% Capacity Utilized
            </span>
            <span className="text-slate-400">{totalApprovedIntake - totalAdmitted >= 0 ? `${totalApprovedIntake - totalAdmitted} seats open` : "Quota exceeded"}</span>
          </div>
        </div>

        {/* Validation Flags Summary */}
        <div className="p-5 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Validation Flags</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="flex items-center gap-2 pt-1 flex-wrap">
            <FlagBadge level="error" count={errorCount} />
            <FlagBadge level="exception" count={exceptionCount} />
            <FlagBadge level="warning" count={warningCount} />
            <FlagBadge level="info" count={infoCount} />
          </div>
          <p className="text-xs text-slate-500">
            {errorCount > 0 ? (
              <span className="text-red-600 font-semibold">{errorCount} submit-blocking errors</span>
            ) : exceptionCount > 0 ? (
              <span className="text-red-600 font-medium">{exceptionCount} exceptions needing justification</span>
            ) : (
              <span className="text-emerald-600 font-medium">All student records valid</span>
            )}
          </p>
        </div>

        {/* AICTE Queries & Inquiries */}
        <div className="p-5 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">AICTE Inquiries</span>
            <HelpCircle className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-3xl font-bold text-slate-900">{pendingQueries.length}</p>
            {pendingQueries.length > 0 ? (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-100 text-red-800 animate-pulse">
                Action Required
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">
                All Cleared
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            {pendingQueries.length > 0
              ? `${pendingQueries.length} clarification queries awaiting response`
              : "No pending clarification queries"}
          </p>
        </div>
      </div>

      {/* 3. Official Submission Status & Receipt Banner */}
      <div className={`p-6 rounded-xl border shadow-sm ${
        isLocked
          ? "bg-gradient-to-r from-emerald-50 via-teal-50 to-blue-50 border-emerald-200"
          : gateData?.can_submit
          ? "bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200"
          : "bg-slate-50 border-slate-200"
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                Submission Status ({academicYear})
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide ${
                  isLocked || submissionStatus === "submitted" || submissionStatus === "accepted"
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : submissionStatus === "submitted_with_exceptions"
                    ? "bg-amber-100 text-amber-800 border border-amber-300"
                    : submissionStatus === "under_review"
                    ? "bg-blue-100 text-blue-800 border border-blue-300"
                    : submissionStatus === "query_raised"
                    ? "bg-purple-100 text-purple-800 border border-purple-300"
                    : "bg-slate-200 text-slate-800 border border-slate-300"
                }`}
              >
                {submissionStatus.replace(/_/g, " ")}
              </span>
              {isLocked && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-700 text-white shadow-xs">
                  <Lock className="w-3 h-3" /> Data Locked & Read-only
                </span>
              )}
            </div>

            {isLocked ? (
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  Official AICTE Central Repository Receipt
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">
                  Institutional data has been formally verified and submitted. All records are permanently preserved and locked.
                </p>
                {receiptNumber && (
                  <div className="mt-3 inline-flex items-center gap-3 bg-white border border-emerald-200 px-3.5 py-1.5 rounded-lg shadow-xs">
                    <span className="text-xs text-slate-500 font-medium">Receipt No:</span>
                    <span className="font-mono text-sm font-bold text-slate-900">{receiptNumber}</span>
                    <button
                      type="button"
                      onClick={() => handleCopyReceipt(receiptNumber)}
                      className="p-1 text-slate-400 hover:text-emerald-700 transition"
                      title="Copy receipt number"
                      aria-label="Copy receipt number"
                    >
                      {copiedReceipt ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    </button>
                    {copiedReceipt && <span className="text-[11px] font-semibold text-emerald-600">Copied!</span>}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  {gateData?.can_submit ? (
                    <CheckCircle2 className="w-5 h-5 text-blue-600" />
                  ) : (
                    <ShieldAlert className="w-5 h-5 text-amber-600" />
                  )}
                  {gateData?.can_submit ? "Ready for Final Statutory Submission" : "Submission Blocked by Validation Issues"}
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">
                  {gateData?.can_submit
                    ? "All courses satisfy admission quotas and open exceptions are properly justified. The head of institution can complete submission."
                    : `${gateData?.blockers?.length ?? errorCount} blocker(s) must be addressed before the final declaration can be signed.`}
                </p>
                {gateData?.blockers && gateData.blockers.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-red-700">
                    {gateData.blockers.slice(0, 3).map((b, idx) => (
                      <li key={idx} className="flex items-center gap-1.5 font-medium">
                        <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                        <span>{typeof b === "string" ? b : b.message || b.reason}</span>
                      </li>
                    ))}
                    {gateData.blockers.length > 3 && (
                      <li className="text-slate-500 italic text-[11px]">
                        + {gateData.blockers.length - 3} more blockers (view details on Submit screen)
                      </li>
                    )}
                  </ul>
                )}
              </div>
            )}
          </div>

          <div className="shrink-0 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleDownloadSubmission("pdf")}
              disabled={downloadingReport !== null}
              leftIcon={<Download className="w-3.5 h-3.5 text-blue-600" />}
            >
              {downloadingReport === "sub_pdf" ? "Downloading..." : "Submission PDF"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleDownloadAccreditation}
              disabled={downloadingReport !== null}
              leftIcon={<Download className="w-3.5 h-3.5 text-indigo-600" />}
            >
              {downloadingReport === "accreditation" ? "Downloading..." : "Accreditation PDF"}
            </Button>
            {isLocked ? (
              <Link to="/college/submit">
                <Button size="sm" variant="outline" leftIcon={<FileCheck className="w-4 h-4 text-emerald-600" />}>
                  View Receipt Details
                </Button>
              </Link>
            ) : (
              <Link to="/college/submit">
                <Button
                  size="sm"
                  variant={gateData?.can_submit ? "primary" : "secondary"}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  {gateData?.can_submit ? "Proceed to Submit Gate" : "Review Submission Blockers"}
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* 4. Course Summary Table (SPEC.md Section 13) */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-600" />
                Course Summary Table
              </h2>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                Academic Year {academicYear}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              AICTE approved courses, sanctioned intake limits (read-only), and active student admission totals.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/college/seats">
              <Button size="sm" variant="outline" leftIcon={<FileText className="w-3.5 h-3.5" />}>
                Seat Breakdown
              </Button>
            </Link>
            {!isLocked && (
              <Link to="/college/students/new">
                <Button size="sm" variant="secondary" leftIcon={<UserPlus className="w-3.5 h-3.5" />}>
                  Add Student
                </Button>
              </Link>
            )}
          </div>
        </div>

        {courses.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No Approved Courses Found"
              description={`There are no affiliated courses recorded for academic year ${academicYear}.`}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/4">Course & Discipline</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead className="text-right">
                    <span className="inline-flex items-center gap-1">
                      <Lock className="w-3 h-3 text-slate-400" /> Approved Intake
                    </span>
                  </TableHead>
                  <TableHead className="text-right">Regular Admitted</TableHead>
                  <TableHead className="text-right">Supernumerary</TableHead>
                  <TableHead className="text-right font-bold">Total Admitted</TableHead>
                  <TableHead className="text-center">Intake Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {courses.map((course: CourseSummaryResponse) => {
                  const isOverRegular = course.regular_admitted > course.approved_intake;
                  const regularOvershoot = course.regular_admitted - course.approved_intake;
                  const isOverSupernum =
                    course.supernumerary_seats_allowed > 0 &&
                    course.supernumerary_admitted > course.supernumerary_seats_allowed;

                  return (
                    <TableRow key={course.course_id} className="hover:bg-slate-50/70 transition">
                      <TableCell>
                        <div className="font-semibold text-slate-900">{course.course_name}</div>
                        <div className="text-xs text-slate-500 font-mono">{course.branch}</div>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                          {course.level || "UG"} &bull; {course.duration_years || 4}Y
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold text-slate-800">
                        <span className="inline-flex items-center gap-1 justify-end" title="AICTE-owned read-only intake">
                          <Lock className="w-3 h-3 text-slate-400" />
                          {course.approved_intake}
                        </span>
                      </TableCell>
                      <TableCell className={`text-right font-mono ${isOverRegular ? "font-bold text-red-600" : "text-slate-800"}`}>
                        {course.regular_admitted}
                      </TableCell>
                      <TableCell className="text-right font-mono text-slate-600">
                        {course.supernumerary_admitted}
                        <span className="text-[11px] text-slate-400 font-normal"> / {course.supernumerary_seats_allowed}</span>
                      </TableCell>
                      <TableCell className="text-right font-mono font-bold text-slate-900">
                        {course.calculated_enrolment ?? course.regular_admitted + course.supernumerary_admitted}
                      </TableCell>
                      <TableCell className="text-center">
                        {isOverRegular ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-200">
                            Over by {regularOvershoot}
                          </span>
                        ) : isOverSupernum ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                            Supernum +{course.supernumerary_admitted - course.supernumerary_seats_allowed}
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            Within limit
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            to={`/college/students?course_id=${course.course_id}`}
                            className="text-xs font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition"
                          >
                            Students &rarr;
                          </Link>
                          <Link
                            to="/college/seats"
                            className="text-xs font-medium text-slate-500 hover:text-slate-800 px-2 py-1 rounded hover:bg-slate-100 transition"
                          >
                            Seats
                          </Link>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* 5. Pending Flags Grouped by Level (SPEC.md Section 13) */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Pending Validation Flags
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Active discrepancies detected by the pure validation engine. Errors block submission; exceptions require justification.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/college/validation">
              <Button size="sm" variant="outline" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
                Validation Hub
              </Button>
            </Link>
          </div>
        </div>

        {/* Level Filter Tabs */}
        <div className="px-6 py-3 bg-slate-50/70 border-b border-slate-100 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setSelectedFlagLevel("all")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
              selectedFlagLevel === "all"
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
            }`}
          >
            All Flags ({flagsList.length})
          </button>
          <button
            type="button"
            onClick={() => setSelectedFlagLevel("error")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              selectedFlagLevel === "error"
                ? "bg-red-600 text-white shadow-xs"
                : "bg-white text-red-700 border border-red-200 hover:bg-red-50"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
            Errors ({errorCount})
          </button>
          <button
            type="button"
            onClick={() => setSelectedFlagLevel("exception")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              selectedFlagLevel === "exception"
                ? "bg-red-700 text-white shadow-xs"
                : "bg-white text-red-800 border border-red-300 hover:bg-red-50"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-red-700 inline-block" />
            Exceptions ({exceptionCount})
          </button>
          <button
            type="button"
            onClick={() => setSelectedFlagLevel("warning")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              selectedFlagLevel === "warning"
                ? "bg-amber-600 text-white shadow-xs"
                : "bg-white text-amber-700 border border-amber-200 hover:bg-amber-50"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
            Warnings ({warningCount})
          </button>
          <button
            type="button"
            onClick={() => setSelectedFlagLevel("info")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              selectedFlagLevel === "info"
                ? "bg-slate-700 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
            Info ({infoCount})
          </button>
        </div>

        {filteredFlags.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title={selectedFlagLevel === "all" ? "No Validation Flags" : `No ${selectedFlagLevel} Flags`}
              description="All records are clean and pass the automated validation engine."
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-[460px] overflow-y-auto">
            {filteredFlags.map((flag: ValidationFlagDetail) => (
              <div key={flag.id} className="p-4 hover:bg-slate-50 transition flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <FlagBadge level={flag.level} />
                    <span className="font-mono text-xs font-bold text-slate-800">{flag.rule_code}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                        flag.status === "justified"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {flag.status === "justified" ? "✓ Justified" : "Open"}
                    </span>
                    {flag.field && (
                      <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                        field: {flag.field}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-slate-900">{flag.message}</p>
                  {flag.fix_hint && (
                    <p className="text-xs text-slate-500 flex items-center gap-1">
                      <span className="font-semibold text-slate-600">Fix hint:</span> {flag.fix_hint}
                    </p>
                  )}
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  {flag.student_id ? (
                    <Link
                      to={`/college/students/${flag.student_id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 px-2.5 py-1 rounded bg-blue-50 hover:bg-blue-100 transition"
                    >
                      <span>Row #{flag.student_id}</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  ) : flag.course_id ? (
                    <Link
                      to={`/college/seats?course_id=${flag.course_id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 px-2.5 py-1 rounded bg-blue-50 hover:bg-blue-100 transition"
                    >
                      <span>Course #{flag.course_id}</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  ) : (
                    <Link
                      to={`/college/validation/${flag.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-800 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 transition"
                    >
                      <span>Flag #{flag.id}</span>
                    </Link>
                  )}

                  <Link to={`/college/validation/${flag.id}`}>
                    <Button size="sm" variant={flag.status === "justified" ? "outline" : "secondary"}>
                      {flag.status === "justified" ? "View Justification" : "View Flag"}
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 6. AICTE Clarification Queries (SPEC.md Section 13) */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-indigo-600" />
                AICTE Clarification Inquiries
              </h2>
              {pendingQueries.length > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-200">
                  {pendingQueries.length} Action Needed
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Official inquiry questions issued by AICTE reviewers. Responding with written notes and evidence restores submission review.
            </p>
          </div>
          <Link to="/college/queries">
            <Button size="sm" variant="outline" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
              All Inquiries Hub
            </Button>
          </Link>
        </div>

        {pendingQueries.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No Pending AICTE Inquiries"
              description="No clarification queries are currently awaiting institutional response."
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {pendingQueries.map((query: CollegeQueryResponse) => (
              <div key={query.id} className="p-5 hover:bg-indigo-50/30 transition flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-red-100 text-red-800">
                      Pending Reply
                    </span>
                    <span className="font-mono text-xs font-semibold text-slate-500">Query #{query.id}</span>
                    {query.officer_name && (
                      <span className="text-xs text-slate-500">
                        from <strong className="text-slate-700">{query.officer_name}</strong>
                      </span>
                    )}
                    {query.created_at && (
                      <span className="text-[11px] text-slate-400">
                        &bull; {new Date(query.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  <p className="text-sm font-semibold text-slate-900 bg-white border border-slate-200 p-3 rounded-lg">
                    &ldquo;{query.message}&rdquo;
                  </p>

                  {query.flags && query.flags.length > 0 && (
                    <div className="flex items-center gap-2 pt-1 flex-wrap">
                      <span className="text-xs text-slate-500 font-medium">Linked flags:</span>
                      {query.flags.map((f, i) => (
                        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-[11px] font-mono text-slate-700">
                          {f.rule_code} {f.field ? `(${f.field})` : ""}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="shrink-0">
                  <Link to={`/college/queries?query_id=${query.id}`}>
                    <Button size="sm" variant="primary" leftIcon={<MessageSquare className="w-3.5 h-3.5" />}>
                      Reply to Query
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 7. System Notifications Feed (SPEC.md Section 13) */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Bell className="w-5 h-5 text-blue-600" />
                Institutional Notifications
              </h2>
              {unreadNotificationsCount > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
                  {unreadNotificationsCount} New
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Live alerts for cross-college duplicate enrolments, official intake quota changes, and compliance notices.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-xs">
              <button
                type="button"
                onClick={() => setSelectedNotifFilter("all")}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  selectedNotifFilter === "all" ? "bg-white text-slate-800 shadow-xs" : "text-slate-500"
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setSelectedNotifFilter("unread")}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  selectedNotifFilter === "unread" ? "bg-white text-slate-800 shadow-xs" : "text-slate-500"
                }`}
              >
                Unread ({unreadNotificationsCount})
              </button>
            </div>

            {unreadNotificationsCount > 0 && (
              <Button size="sm" variant="outline" onClick={handleMarkAllAsRead}>
                Mark All Read
              </Button>
            )}
          </div>
        </div>

        {filteredNotifications.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title={selectedNotifFilter === "unread" ? "No Unread Notifications" : "No Notifications"}
              description="Your institution has no system alerts at this time."
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-[460px] overflow-y-auto">
            {filteredNotifications.map((notif: NotificationItem) => {
              const isUnread = !notif.read_at;
              const payload = notif.payload || {};

              return (
                <div
                  key={notif.id}
                  className={`p-4 transition flex flex-col md:flex-row md:items-center md:justify-between gap-4 ${
                    isUnread ? "bg-blue-50/40" : "hover:bg-slate-50"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {isUnread && <span className="w-2 h-2 rounded-full bg-blue-600 shrink-0" title="Unread" />}
                      <span className="font-mono text-xs font-bold text-slate-800">
                        {notif.type.replace(/_/g, " ").toUpperCase()}
                      </span>
                      {notif.created_at && (
                        <span className="text-[11px] text-slate-400">
                          &bull; {new Date(notif.created_at).toLocaleString()}
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-slate-900">
                      {payload.message || payload.directive || payload.reason || "System notice from AICTE."}
                    </p>

                    {/* Detailed contextual metadata preview */}
                    <div className="flex items-center gap-3 text-xs text-slate-500 flex-wrap pt-0.5">
                      {payload.apaar_id && (
                        <span className="font-mono bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                          APAAR: {payload.apaar_id}
                        </span>
                      )}
                      {payload.student_name && <span>Student: <strong>{payload.student_name}</strong></span>}
                      {payload.other_college_name && (
                        <span>Other college: <strong className="text-amber-700">{payload.other_college_name}</strong></span>
                      )}
                      {payload.course_name && <span>Course: {payload.course_name}</span>}
                      {payload.new_intake !== undefined && (
                        <span>New Intake: <strong>{payload.new_intake}</strong></span>
                      )}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-2">
                    {isUnread && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleMarkAsRead(notif.id)}
                        disabled={markingReadId === notif.id}
                      >
                        {markingReadId === notif.id ? "Marking..." : "Mark as read"}
                      </Button>
                    )}
                    {notif.type.includes("duplicate") && (
                      <Link to="/college/students">
                        <Button size="sm" variant="outline">
                          View Student
                        </Button>
                      </Link>
                    )}
                    {notif.type.includes("intake") && (
                      <Link to="/college/seats">
                        <Button size="sm" variant="outline">
                          View Intake
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 8. Sequential Workflow Guide (SPEC.md Section 13) */}
      <div className="bg-slate-100/70 border border-slate-200 rounded-xl p-6 space-y-4">
        <div>
          <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm uppercase tracking-wider text-slate-700">
            <Layers className="w-4 h-4 text-blue-600" />
            Statutory Data Submission Pipeline (Section 13)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Follow the sequential stages to record, validate, justify, and formally sign off on annual enrolment records.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <Link
            to="/college/seats"
            className="p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-xs transition group"
          >
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-blue-600 mb-1">
              <span>Stage 1</span>
              <Building2 className="w-3.5 h-3.5" />
            </div>
            <p className="font-bold text-sm text-slate-800">Seat Declarations</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Breakdown quotas per course</p>
          </Link>

          <Link
            to="/college/students/new"
            className="p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-xs transition group"
          >
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-blue-600 mb-1">
              <span>Stage 2</span>
              <UserPlus className="w-3.5 h-3.5" />
            </div>
            <p className="font-bold text-sm text-slate-800">Individual Entry</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Check and save single APAAR</p>
          </Link>

          <Link
            to="/college/upload"
            className="p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-xs transition group"
          >
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-blue-600 mb-1">
              <span>Stage 3</span>
              <FileUp className="w-3.5 h-3.5" />
            </div>
            <p className="font-bold text-sm text-slate-800">Bulk CSV Upload</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Parse, save drafts & validate</p>
          </Link>

          <Link
            to="/college/validation"
            className="p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-xs transition group"
          >
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-blue-600 mb-1">
              <span>Stage 4</span>
              <AlertTriangle className="w-3.5 h-3.5" />
            </div>
            <p className="font-bold text-sm text-slate-800">Resolve & Justify</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Attach documents for exceptions</p>
          </Link>

          <Link
            to="/college/submit"
            className="p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-xs transition group"
          >
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-blue-600 mb-1">
              <span>Stage 5</span>
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <p className="font-bold text-sm text-slate-800">Submit Gate</p>
            <p className="text-[11px] text-slate-500 mt-0.5">OTP declaration & receipt</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
