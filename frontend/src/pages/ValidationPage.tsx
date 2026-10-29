import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Download,
  FileCheck,
  FileText,
  Filter,
  Info,
  Paperclip,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import {
  createJustification,
  deleteJustification,
  downloadJustificationDocument,
  getInstitutionFlags,
} from "../api/justifications";
import type {
  FlagLevel,
  InstitutionFlagsListResponse,
  ValidationFlagDetail,
} from "../types/validation";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { EmptyState } from "../components/ui/EmptyState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function ValidationPage() {
  useDocumentTitle("Validation Flags");
  const { user } = useAuth();
  const institutionId = user?.institution_id ?? 1;

  // Filters State
  const [academicYear, setAcademicYear] = useState<string>("2026-27");
  const [selectedLevel, setSelectedLevel] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Data State
  const [data, setData] = useState<InstitutionFlagsListResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Modal State
  const [activeFlag, setActiveFlag] = useState<ValidationFlagDetail | null>(null);
  const [justificationText, setJustificationText] = useState<string>("");
  const [selectedDocument, setSelectedDocument] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Fetch flags
  const loadFlags = useCallback(
    async (showLoading = true) => {
      if (showLoading) setIsLoading(true);
      setErrorMessage(null);
      try {
        const filters = {
          academic_year: academicYear,
          level: selectedLevel !== "all" ? selectedLevel : undefined,
          status: selectedStatus !== "all" ? selectedStatus : undefined,
          search: searchTerm ? searchTerm.trim() : undefined,
        };
        const res = await getInstitutionFlags(institutionId, filters);
        setData(res);
      } catch (err) {
        setErrorMessage(
          err instanceof Error ? err.message : "Failed to load validation flags."
        );
      } finally {
        if (showLoading) setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [institutionId, academicYear, selectedLevel, selectedStatus, searchTerm]
  );

  useEffect(() => {
    loadFlags(true);
  }, [loadFlags]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadFlags(false);
  };

  // Open modal
  const handleOpenJustificationModal = (flag: ValidationFlagDetail) => {
    setActiveFlag(flag);
    setJustificationText("");
    setSelectedDocument(null);
    setModalError(null);
  };

  // Close modal
  const handleCloseModal = () => {
    setActiveFlag(null);
    setJustificationText("");
    setSelectedDocument(null);
    setModalError(null);
  };

  // Submit justification
  const handleSubmitJustification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeFlag) return;

    if (!justificationText.trim() || justificationText.trim().length < 5) {
      setModalError("Justification text must be at least 5 characters long.");
      return;
    }

    setIsSubmitting(true);
    setModalError(null);

    try {
      await createJustification(
        institutionId,
        activeFlag.id,
        justificationText.trim(),
        selectedDocument
      );
      setSuccessToast(
        `Justification submitted successfully for flag ${activeFlag.rule_code}.`
      );
      handleCloseModal();
      await loadFlags(false);
      setTimeout(() => setSuccessToast(null), 5000);
    } catch (err) {
      setModalError(
        err instanceof Error
          ? err.message
          : "Failed to submit justification. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Download document
  const handleDownloadDocument = async (justificationId: number) => {
    try {
      const { blob, filename } = await downloadJustificationDocument(
        institutionId,
        justificationId
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to download document");
    }
  };

  // Delete justification
  const handleDeleteJustification = async (justificationId: number) => {
    if (!confirm("Are you sure you want to remove this justification?")) return;
    try {
      await deleteJustification(institutionId, justificationId);
      await loadFlags(false);
      if (activeFlag) {
        setActiveFlag((prev) =>
          prev
            ? {
                ...prev,
                justifications: prev.justifications.filter((j) => j.id !== justificationId),
                status: prev.justifications.length <= 1 ? "open" : prev.status,
              }
            : null
        );
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete justification");
    }
  };

  const summary = data?.summary;
  const isCollegeStaffOrAdmin =
    user?.role === "college_admin" || user?.role === "college_staff";

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {successToast && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-3 bg-emerald-600 text-white px-5 py-3 rounded-lg shadow-xl animate-bounce">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span className="font-medium text-sm">{successToast}</span>
        </div>
      )}

      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Validation Flags & Justifications
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Review statutory flags, justify compliance exceptions with supporting documents, and resolve gate blockers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            aria-label="Filter by academic year"
            className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="2026-27">Academic Year 2026-27</option>
            <option value="2025-26">Academic Year 2025-26</option>
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          <Link to="/college/submit">
            <Button
              variant="primary"
              size="sm"
              className="flex items-center gap-2"
            >
              Go to final submit gate
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Total Flags
              </span>
              <Filter className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">
              {summary.total_flags}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {summary.resolved_count} resolved
            </div>
          </div>

          <div
            className={`p-4 rounded-xl border shadow-sm ${
              summary.blocking_count > 0
                ? "bg-red-50/70 border-red-200"
                : "bg-emerald-50/70 border-emerald-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span
                className={`text-xs font-semibold uppercase tracking-wider ${
                  summary.blocking_count > 0 ? "text-red-700" : "text-emerald-700"
                }`}
              >
                Submit Blockers
              </span>
              {summary.blocking_count > 0 ? (
                <AlertCircle className="w-4 h-4 text-red-600" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              )}
            </div>
            <div
              className={`text-2xl font-bold mt-2 ${
                summary.blocking_count > 0 ? "text-red-900" : "text-emerald-900"
              }`}
            >
              {summary.blocking_count}
            </div>
            <div
              className={`text-xs mt-1 ${
                summary.blocking_count > 0 ? "text-red-600" : "text-emerald-600"
              }`}
            >
              {summary.blocking_count > 0
                ? `${summary.error_count} errors, ${summary.exception_count - summary.justified_count > 0 ? summary.exception_count - summary.justified_count : 0} unjustified`
                : "All gates cleared"}
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Justified
              </span>
              <FileCheck className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-emerald-700 mt-2">
              {summary.justified_count}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Accepted for review
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Warnings & Notices
              </span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-amber-800 mt-2">
              {summary.warning_count}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {summary.info_count} informational
            </div>
          </div>
        </div>
      )}

      {/* Submission Gate Banner */}
      {summary && (
        <div
          className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            summary.can_submit
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-red-50 border-red-200 text-red-900"
          }`}
        >
          <div className="flex items-start gap-3">
            {summary.can_submit ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <h3 className="font-semibold text-sm">
                {summary.can_submit
                  ? "Submission Gate: Permitted (submitted_with_exceptions or clean)"
                  : `Submission Gate: BLOCKED (${summary.blocking_count} Unresolved Item${summary.blocking_count > 1 ? "s" : ""})`}
              </h3>
              <p className="text-xs mt-0.5 opacity-90">
                {summary.can_submit
                  ? "All error-level issues have been corrected and all exceptions carry valid written justifications. You may proceed to submit."
                  : "Per SPEC.md Section 10, final submission is blocked while any error is open, or while compliance exceptions lack written justification."}
              </p>
            </div>
          </div>

          {summary.can_submit ? (
            <Link to="/college/submit" className="flex-shrink-0">
              <Button size="sm" variant="primary" className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2">
                Proceed to final submit
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          ) : (
            <div className="flex items-center gap-2 text-xs font-medium text-red-700 bg-red-100/60 px-3 py-1.5 rounded-lg border border-red-200 flex-shrink-0">
              Fix errors or justify exceptions below
            </div>
          )}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Level Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: "all", label: "All Levels" },
              { id: "error", label: "Errors", count: summary?.error_count },
              { id: "exception", label: "Exceptions", count: summary?.exception_count },
              { id: "warning", label: "Warnings", count: summary?.warning_count },
              { id: "info", label: "Info", count: summary?.info_count },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedLevel(tab.id)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition whitespace-nowrap ${
                  selectedLevel === tab.id
                    ? "bg-slate-900 text-white shadow"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span
                    className={`ml-1.5 px-1.5 py-0.2 rounded-full text-[10px] ${
                      selectedLevel === tab.id
                        ? "bg-slate-700 text-white"
                        : "bg-slate-200 text-slate-800"
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Search & Status Filters */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1 md:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search APAAR, rule, text..."
                aria-label="Search flags by APAAR, rule, or text"
                className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm("")}
                  aria-label="Clear search input"
                  className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              aria-label="Filter by flag status"
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="justified">Justified</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Flags Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <LoadingSpinner size="lg" />
            <p className="text-sm text-slate-500 mt-3">Loading validation flags...</p>
          </div>
        ) : errorMessage ? (
          <div className="p-8 text-center text-red-600">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-red-500" />
            <p className="font-semibold text-sm">{errorMessage}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadFlags(true)}
              className="mt-4"
            >
              Retry
            </Button>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-10">
            <EmptyState
              title="No validation flags found"
              description="No flags match your current filter criteria. Great job on clean data!"
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Level</th>
                  <th className="py-3 px-4">Rule Code</th>
                  <th className="py-3 px-4">Target Entity</th>
                  <th className="py-3 px-4">Message & Hint</th>
                  <th className="py-3 px-4">Justification</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {data.items.map((flag) => {
                  const hasJustification =
                    flag.status === "justified" || flag.justifications.length > 0;
                  const isError = flag.level === "error";

                  return (
                    <tr
                      key={flag.id}
                      className={`hover:bg-slate-50/80 transition ${
                        flag.status === "resolved" ? "bg-slate-50/70 text-slate-600" : ""
                      }`}
                    >
                      {/* Level */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <FlagBadge level={flag.level as FlagLevel} />
                      </td>

                      {/* Rule Code & Field */}
                      <td className="py-3.5 px-4 font-mono font-medium text-slate-900 whitespace-nowrap">
                        <Link
                          to={`/college/validation/${flag.id}`}
                          className="hover:text-blue-600 hover:underline font-bold"
                          title="View flag details and regulatory justification"
                        >
                          {flag.rule_code}
                        </Link>
                        {flag.field && (
                          <div className="text-[11px] font-sans font-normal text-slate-500">
                            field: <code className="text-slate-700">{flag.field}</code>
                          </div>
                        )}
                      </td>

                      {/* Target Student or Course */}
                      <td className="py-3.5 px-4">
                        {flag.student ? (
                          <Link
                            to={`/college/students/${flag.student.id}`}
                            className="group block hover:text-blue-600"
                            title="Open student record"
                          >
                            <div className="font-semibold text-slate-900 group-hover:text-blue-600 underline decoration-slate-300">
                              {flag.student.name}
                            </div>
                            <div className="font-mono text-[11px] text-slate-500">
                              APAAR: {flag.student.apaar_id}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              Enrol: {flag.student.enrolment_no || "N/A"}
                            </div>
                          </Link>
                        ) : flag.course ? (
                          <div>
                            <div className="font-semibold text-slate-900">
                              {flag.course.name}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              {flag.course.branch} ({flag.course.level})
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Institutional</span>
                        )}
                      </td>

                      {/* Message and Fix Hint */}
                      <td className="py-3.5 px-4 max-w-md">
                        <div className="text-slate-900 font-medium leading-relaxed">
                          {flag.message}
                        </div>
                        {flag.fix_hint && (
                          <div className="text-[11px] text-blue-800 bg-blue-50/80 px-2 py-1 rounded border border-blue-100 mt-1.5 flex items-start gap-1.5">
                            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-blue-600" />
                            <span>{flag.fix_hint}</span>
                          </div>
                        )}
                      </td>

                      {/* Status / Justification Badge */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {flag.status === "resolved" ? (
                          <Badge variant="neutral" size="sm">
                            Resolved
                          </Badge>
                        ) : hasJustification ? (
                          <div className="space-y-1">
                            <Badge variant="success" size="sm">
                              Justified
                            </Badge>
                            {flag.justifications.length > 0 &&
                              flag.justifications[0].document_ref && (
                                <div className="flex items-center gap-1 text-[11px] text-emerald-700">
                                  <Paperclip className="w-3 h-3" />
                                  <span>Doc attached</span>
                                </div>
                              )}
                          </div>
                        ) : isError ? (
                          <span className="text-[11px] font-semibold text-red-700 bg-red-100/70 px-2 py-0.5 rounded border border-red-200">
                            Must Fix Data
                          </span>
                        ) : flag.requires_justification ? (
                          <span className="text-[11px] font-semibold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded border border-amber-300">
                            Justification Required
                          </span>
                        ) : (
                          <Badge variant="outline" size="sm">
                            Open
                          </Badge>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        {isError ? (
                          <Link
                            to={
                              flag.student
                                ? `/college/students/${flag.student.id}/edit`
                                : `/college/upload`
                            }
                          >
                            <Button size="sm" variant="outline" className="text-xs">
                              Fix in Record
                            </Button>
                          </Link>
                        ) : (
                          <Button
                            size="sm"
                            variant={hasJustification ? "outline" : "primary"}
                            onClick={() => handleOpenJustificationModal(flag)}
                            disabled={!isCollegeStaffOrAdmin}
                            className="text-xs"
                          >
                            {hasJustification ? "View / Edit Justification" : "Add Justification"}
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Justification Modal / Dialog */}
      {activeFlag && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
          <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center gap-3">
                <FlagBadge level={activeFlag.level as FlagLevel} />
                <h3 className="font-bold text-slate-900 text-base">
                  Statutory Justification & Evidence
                </h3>
              </div>
              <button
                onClick={handleCloseModal}
                aria-label="Close dialog"
                className="text-slate-400 hover:text-slate-600 rounded-lg p-1 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs">
              {/* Flag Context Box */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                <div className="flex items-center justify-between font-mono font-bold text-slate-800">
                  <span>{activeFlag.rule_code}</span>
                  <span className="text-[11px] text-slate-500 font-sans font-normal">
                    Status: <span className="capitalize font-semibold">{activeFlag.status}</span>
                  </span>
                </div>
                <p className="text-slate-700 leading-relaxed font-medium">
                  {activeFlag.message}
                </p>
                {activeFlag.student && (
                  <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200 mt-2">
                    Student: <span className="font-semibold text-slate-800">{activeFlag.student.name}</span> (APAAR: {activeFlag.student.apaar_id})
                  </div>
                )}
                {activeFlag.course && (
                  <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200 mt-2">
                    Course: <span className="font-semibold text-slate-800">{activeFlag.course.name}</span> ({activeFlag.course.branch})
                  </div>
                )}
              </div>

              {/* Existing Justifications History */}
              {activeFlag.justifications && activeFlag.justifications.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-semibold text-slate-800 text-xs uppercase tracking-wider">
                    Existing Justification Records
                  </h4>
                  <div className="space-y-2">
                    {activeFlag.justifications.map((j) => (
                      <div
                        key={j.id}
                        className="bg-emerald-50/50 border border-emerald-200 p-3.5 rounded-xl space-y-2"
                      >
                        <div className="flex items-center justify-between text-[11px] text-emerald-900 font-medium">
                          <span>
                            By {j.author_name || "Institution Staff"} ({j.author_role || "college_staff"})
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-slate-500">
                              {new Date(j.at).toLocaleString()}
                            </span>
                            {isCollegeStaffOrAdmin && (
                              <button
                                type="button"
                                onClick={() => handleDeleteJustification(j.id)}
                                aria-label="Delete justification"
                                className="text-red-500 hover:text-red-700 p-1 transition"
                                title="Delete justification"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>

                        <p className="text-slate-800 leading-relaxed font-sans text-xs">
                          {j.text}
                        </p>

                        {j.document_ref && (
                          <div className="pt-2 flex items-center justify-between border-t border-emerald-200/60 text-[11px]">
                            <div className="flex items-center gap-1.5 text-emerald-800 font-medium">
                              <FileText className="w-4 h-4 text-emerald-600" />
                              <span className="truncate max-w-xs">{j.document_ref}</span>
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDownloadDocument(j.id)}
                              className="text-xs py-1 h-7 flex items-center gap-1 border-emerald-300 text-emerald-800 hover:bg-emerald-100"
                            >
                              <Download className="w-3 h-3" />
                              Download
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Justification Form */}
              <form onSubmit={handleSubmitJustification} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block font-semibold text-slate-800 text-xs">
                    {activeFlag.justifications.length > 0
                      ? "Add Supplementary Justification Statement *"
                      : "Official Justification Statement *"}
                  </label>
                  <textarea
                    rows={4}
                    value={justificationText}
                    onChange={(e) => setJustificationText(e.target.value)}
                    placeholder="State the regulatory basis, court order, state counselling allotment reference, or specific institutional circumstance that justifies this record..."
                    className="w-full p-3 text-xs border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                    required
                  />
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Minimum 5 characters. Written explanations are routed to AICTE review queue.</span>
                    <span>{justificationText.length} chars</span>
                  </div>
                </div>

                {/* File Attachment via Storage Interface */}
                <div className="space-y-1.5">
                  <label className="block font-semibold text-slate-800 text-xs">
                    Attach Supporting Document (Optional / Recommended)
                  </label>
                  <div className="border-2 border-dashed border-slate-300 rounded-xl p-4 text-center hover:border-blue-400 transition bg-slate-50/50">
                    {selectedDocument ? (
                      <div className="flex items-center justify-between bg-white p-2.5 rounded-lg border border-slate-200">
                        <div className="flex items-center gap-2 truncate">
                          <Paperclip className="w-4 h-4 text-blue-600 flex-shrink-0" />
                          <span className="font-medium text-slate-800 truncate">
                            {selectedDocument.name}
                          </span>
                          <span className="text-slate-400 text-[10px]">
                            ({(selectedDocument.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSelectedDocument(null)}
                          aria-label="Remove uploaded document"
                          className="text-slate-400 hover:text-red-500 p-1"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <label className="cursor-pointer block">
                        <Upload className="w-6 h-6 mx-auto text-slate-400 mb-1" />
                        <span className="text-xs font-semibold text-blue-600 hover:text-blue-800">
                          Click to upload evidence file
                        </span>
                        <span className="block text-[11px] text-slate-400 mt-0.5">
                          PDF, PNG, JPG, DOCX, XLSX (max 10MB) stored via secure storage
                        </span>
                        <input
                          type="file"
                          accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.doc,.csv"
                          onChange={(e) => {
                            if (e.target.files && e.target.files[0]) {
                              setSelectedDocument(e.target.files[0]);
                            }
                          }}
                          className="hidden"
                        />
                      </label>
                    )}
                  </div>
                </div>

                {modalError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{modalError}</span>
                  </div>
                )}

                {/* Modal Footer Buttons */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200">
                  <Button
                    type="button"
                    variant="outline"
                    aria-label="Cancel and close dialog"
                    onClick={handleCloseModal}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={isSubmitting}
                    className="flex items-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <LoadingSpinner size="sm" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <FileCheck className="w-4 h-4" />
                        Save Justification
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
