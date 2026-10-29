import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchReviewItems,
  fetchReviewItemDetail,
  submitReviewDecision,
  getReviewDocumentDownloadUrl,
} from "../api/review";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import type {
  ReviewDecision,
  ReviewItemDetailResponse,
  ReviewItemListResponse,
} from "../types/review";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { FlagBadge } from "../components/ui/Badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ui/Table";
import {
  AlertCircle,
  AlertTriangle,
  Building2,
  CheckCircle2,
  Download,
  FileCheck2,
  FileQuestion,
  HelpCircle,
  History,
  MessageSquare,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  X,
} from "lucide-react";

export function AicteReviewPage() {
  useDocumentTitle("AICTE Submission Review Queue");
  const [data, setData] = useState<ReviewItemListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [academicYear, setAcademicYear] = useState<string>("2026-27");
  const [searchQuery, setSearchQuery] = useState("");

  // Inspection Drawer / Modal
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [detailItem, setDetailItem] = useState<ReviewItemDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Decision Form State
  const [decisionType, setDecisionType] = useState<ReviewDecision>("accept");
  const [decisionNote, setDecisionNote] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [decisionSuccessMsg, setDecisionSuccessMsg] = useState<string | null>(null);
  const [decisionFormError, setDecisionFormError] = useState<string | null>(null);

  const loadReviewQueue = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchReviewItems({
        status: statusFilter,
        academic_year: academicYear,
        search: searchQuery,
      });
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load review items.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReviewQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, academicYear]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadReviewQueue();
  };

  const openItemDetail = async (id: number) => {
    setSelectedItemId(id);
    setIsLoadingDetail(true);
    setDetailError(null);
    setDecisionSuccessMsg(null);
    setDecisionFormError(null);
    setDecisionNote("");
    try {
      const detail = await fetchReviewItemDetail(id);
      setDetailItem(detail);
      // Default decision type based on current status
      if (detail.status === "query_raised") {
        setDecisionType("accept");
      } else {
        setDecisionType("accept");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load details.";
      setDetailError(msg);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const closeDetail = () => {
    setSelectedItemId(null);
    setDetailItem(null);
    setDecisionSuccessMsg(null);
    setDecisionFormError(null);
    setDecisionNote("");
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detailItem || !selectedItemId) return;

    if (!decisionNote.trim() || decisionNote.trim().length < 3) {
      setDecisionFormError("Official decision note must be at least 3 characters.");
      return;
    }

    setIsSubmittingDecision(true);
    setDecisionFormError(null);
    try {
      const updated = await submitReviewDecision(selectedItemId, {
        decision: decisionType,
        note: decisionNote.trim(),
      });
      setDetailItem(updated);
      setDecisionSuccessMsg(
        decisionType === "accept"
          ? "Exceptions successfully accepted and resolved."
          : decisionType === "query"
          ? "Clarification query successfully dispatched to institution."
          : "Case successfully escalated to standing authority.",
      );
      setDecisionNote("");
      // Refresh list in background
      loadReviewQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit review decision.";
      setDecisionFormError(msg);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "accepted":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Accepted
          </span>
        );
      case "query_raised":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <HelpCircle className="w-3.5 h-3.5" />
            Query Raised
          </span>
        );
      case "escalated":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <ShieldAlert className="w-3.5 h-3.5" />
            Escalated
          </span>
        );
      case "under_review":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />
            Under Review
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <History className="w-3.5 h-3.5" />
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              AICTE Submission Review Queue
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
              SPEC Section 10 & 12
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Review submissions with exception-level flags, inspect written justifications and
            statutory evidence documents, and issue compliance decisions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            aria-label="Filter by academic year"
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="2026-27">AY 2026-27 (Current)</option>
            <option value="2025-26">AY 2025-26 (History)</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            onClick={loadReviewQueue}
            disabled={isLoading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Total in Queue</span>
              <FileCheck2 className="w-4 h-4 text-slate-400" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{data.total}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-blue-600">Pending Review</span>
              <RefreshCw className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-bold text-blue-700 mt-2">
              {data.pending_count + data.under_review_count}
            </p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-amber-600">Queries Raised</span>
              <FileQuestion className="w-4 h-4 text-amber-500" />
            </div>
            <p className="text-2xl font-bold text-amber-700 mt-2">{data.queries_raised_count}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-purple-600">Escalated</span>
              <ShieldAlert className="w-4 h-4 text-purple-500" />
            </div>
            <p className="text-2xl font-bold text-purple-700 mt-2">{data.escalated_count}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-emerald-600">Accepted</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <p className="text-2xl font-bold text-emerald-700 mt-2">{data.accepted_count}</p>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Filter Pills */}
        <div className="flex flex-wrap gap-2 w-full md:w-auto">
          {[
            { id: "all", label: "All Items" },
            { id: "under_review", label: "Under Review" },
            { id: "pending", label: "Pending" },
            { id: "query_raised", label: "Queries Raised" },
            { id: "escalated", label: "Escalated" },
            { id: "accepted", label: "Accepted" },
          ].map((tab) => (
            <button
              key={tab.id}
              aria-label={`Filter by ${tab.label}`}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                statusFilter === tab.id
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <form onSubmit={handleSearch} className="flex gap-2 w-full md:w-80">
          <Input
            placeholder="Search institution, AICTE ID, receipt..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="text-xs"
          />
          <Button type="submit" size="sm" variant="outline" className="px-3" aria-label="Search submissions">
            <Search className="w-4 h-4" />
          </Button>
        </form>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center shadow-sm">
          <LoadingSpinner className="mx-auto" />
          <p className="text-sm text-slate-500 mt-4">Loading review queue items...</p>
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to Load Review Queue"
          message={error}
          onRetry={loadReviewQueue}
        />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No Review Items Found"
          description="There are currently no submissions with open exceptions matching the selected filters."
          actionLabel="Clear Filters"
          onAction={() => {
            setStatusFilter("all");
            setSearchQuery("");
          }}
        />
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead className="font-semibold text-xs">Institution & AICTE ID</TableHead>
                <TableHead className="font-semibold text-xs">Location</TableHead>
                <TableHead className="font-semibold text-xs">Flag Rule Codes</TableHead>
                <TableHead className="font-semibold text-xs">Receipt Number</TableHead>
                <TableHead className="font-semibold text-xs">Status</TableHead>
                <TableHead className="font-semibold text-xs">Submitted / Updated</TableHead>
                <TableHead className="font-semibold text-xs text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((item) => (
                <TableRow key={item.id} className="hover:bg-slate-50/80 transition-colors">
                  <TableCell>
                    <Link
                      to={`/aicte/review/${item.id}`}
                      className="font-semibold text-sm text-slate-900 hover:text-blue-600 block underline decoration-slate-300"
                    >
                      {item.institution_name}
                    </Link>
                    <div className="text-xs font-mono text-slate-500 flex items-center gap-1 mt-0.5">
                      <Building2 className="w-3 h-3 text-slate-400" />
                      {item.aicte_id}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-xs text-slate-700">{item.state}</div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {item.rule_codes.length > 0 ? (
                        item.rule_codes.map((rc) => (
                          <FlagBadge key={rc} level="exception" label={rc} />
                        ))
                      ) : (
                        <span className="text-xs text-slate-400">{item.flag_count} exception(s)</span>
                      )}
                    </div>
                    {item.pending_queries_count > 0 && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 mt-1 font-medium">
                        <MessageSquare className="w-2.5 h-2.5" />
                        {item.pending_queries_count} query awaiting reply
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-xs font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                      {item.receipt_no || "—"}
                    </span>
                  </TableCell>
                  <TableCell>{statusBadge(item.status)}</TableCell>
                  <TableCell>
                    <div className="text-xs text-slate-500">
                      {new Date(item.created_at).toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/aicte/review/${item.id}`}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium hover:underline"
                      >
                        Inspect Page
                      </Link>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openItemDetail(item.id)}
                        className="font-medium text-xs"
                      >
                        Review Item
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Modal / Inspection Drawer for Review Item */}
      {selectedItemId && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-200 bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100 text-blue-700">
                  <FileCheck2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    {detailItem ? detailItem.institution_name : "Review item details"}
                  </h2>
                  {detailItem && (
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                      <span className="font-mono text-slate-700">ID: {detailItem.aicte_id}</span>
                      <span>•</span>
                      <span>AY {detailItem.academic_year}</span>
                      <span>•</span>
                      <span className="font-mono">Receipt: {detailItem.receipt_no}</span>
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={closeDetail}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {isLoadingDetail ? (
                <div className="py-16 text-center">
                  <LoadingSpinner className="mx-auto" />
                  <p className="text-sm text-slate-500 mt-4">Loading exception data and documents...</p>
                </div>
              ) : detailError ? (
                <ErrorState
                  title="Failed to Load Details"
                  message={detailError}
                  onRetry={() => openItemDetail(selectedItemId)}
                />
              ) : detailItem ? (
                <>
                  {/* Status Banner */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="flex items-center gap-3">
                      <div>
                        <div className="text-xs text-slate-500">Current Review Status</div>
                        <div className="mt-1">{statusBadge(detailItem.status)}</div>
                      </div>
                      {detailItem.decision && (
                        <div className="border-l border-slate-200 pl-3">
                          <div className="text-xs text-slate-500">Recorded Decision</div>
                          <div className="text-xs font-semibold uppercase text-slate-800 mt-1">
                            {detailItem.decision}
                          </div>
                        </div>
                      )}
                    </div>
                    {detailItem.decision_note && (
                      <div className="text-xs text-slate-600 max-w-md bg-white p-2.5 rounded border border-slate-200">
                        <span className="font-semibold text-slate-700">Officer Note: </span>
                        {detailItem.decision_note}
                      </div>
                    )}
                  </div>

                  {/* Exceptions and Attached Justifications */}
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-600" />
                      Exception flags and written justifications ({detailItem.flags.length})
                    </h3>

                    {detailItem.flags.map((fl) => (
                      <div
                        key={fl.id}
                        className="rounded-lg border border-red-200 bg-red-50/20 p-4 space-y-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-red-100 pb-2">
                          <div className="flex items-center gap-2">
                            <FlagBadge level="exception" label={fl.rule_code} />
                            {fl.course_name && (
                              <span className="text-xs font-medium text-slate-700">
                                {fl.course_name} {fl.branch ? `(${fl.branch})` : ""}
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-slate-500 font-mono">Flag #{fl.id}</span>
                        </div>

                        <div className="space-y-1">
                          <p className="text-sm font-medium text-slate-900">{fl.message}</p>
                          {fl.fix_hint && (
                            <p className="text-xs text-slate-500 italic">Hint: {fl.fix_hint}</p>
                          )}
                        </div>

                        {/* Student Info if flag is row-level */}
                        {fl.student_name && (
                          <div className="bg-white/80 p-3 rounded border border-slate-200 text-xs flex flex-wrap gap-4 text-slate-600">
                            <div>
                              <span className="font-semibold text-slate-700">Student: </span>
                              {fl.student_name}
                            </div>
                            {fl.student_apaar && (
                              <div>
                                <span className="font-semibold text-slate-700">APAAR ID: </span>
                                <span className="font-mono">{fl.student_apaar}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Justifications Attached */}
                        {fl.justifications.length > 0 ? (
                          <div className="space-y-2 mt-3 pt-2 border-t border-slate-200">
                            <span className="text-xs font-semibold text-slate-700 block">
                              Institution Justification & Supporting Evidence:
                            </span>
                            {fl.justifications.map((just) => (
                              <div
                                key={just.id}
                                className="bg-white p-3 rounded-lg border border-slate-200 space-y-2"
                              >
                                <p className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">
                                  "{just.text}"
                                </p>
                                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500">
                                  <span>
                                    Submitted by {just.by_user_email || "College Staff"} on{" "}
                                    {new Date(just.at).toLocaleString("en-IN")}
                                  </span>
                                  {just.document_ref && (
                                    <a
                                      href={getReviewDocumentDownloadUrl(detailItem.id, just.id)}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 font-medium transition-colors"
                                    >
                                      <Download className="w-3.5 h-3.5" />
                                      Download Document ({just.document_filename || "Attachment"})
                                    </a>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded border border-amber-200">
                            No written justification attached for this flag.
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Query Thread History if any */}
                  {detailItem.queries.length > 0 && (
                    <div className="space-y-3 pt-3 border-t border-slate-200">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-blue-600" />
                        Clarification thread ({detailItem.queries.length})
                      </h3>
                      <div className="space-y-3">
                        {detailItem.queries.map((q) => (
                          <div
                            key={q.id}
                            className="bg-slate-50 rounded-lg p-3.5 border border-slate-200 space-y-2.5"
                          >
                            <div className="flex items-center justify-between text-xs text-slate-500">
                              <span className="font-semibold text-slate-800">
                                AICTE Inquiry (by {q.created_by_email || "Officer"}):
                              </span>
                              <span>{new Date(q.created_at).toLocaleString("en-IN")}</span>
                            </div>
                            <p className="text-xs text-slate-700 bg-white p-2.5 rounded border border-slate-200">
                              {q.message}
                            </p>

                            {q.response ? (
                              <div className="mt-2 pt-2 border-t border-slate-200 pl-4 border-l-2 border-l-emerald-500">
                                <div className="flex items-center justify-between text-xs text-emerald-800 font-semibold mb-1">
                                  <span>Institution Clarification Response:</span>
                                  <span className="text-[11px] text-slate-400 font-normal">
                                    {q.responded_at
                                      ? new Date(q.responded_at).toLocaleString("en-IN")
                                      : ""}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-800 bg-emerald-50/50 p-2.5 rounded border border-emerald-200 whitespace-pre-wrap">
                                  {q.response}
                                </p>
                              </div>
                            ) : (
                              <div className="text-xs text-amber-700 italic flex items-center gap-1.5 pt-1">
                                <HelpCircle className="w-3.5 h-3.5" />
                                Awaiting response from institution staff
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Decision Form */}
                  <form
                    onSubmit={handleDecisionSubmit}
                    className="pt-4 border-t border-slate-200 space-y-4 bg-slate-50/80 -mx-6 -mb-6 p-6"
                  >
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Send className="w-4 h-4 text-blue-600" />
                      Take Review Action
                    </h3>

                    {decisionSuccessMsg && (
                      <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                        <span>{decisionSuccessMsg}</span>
                      </div>
                    )}

                    {decisionFormError && (
                      <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span>{decisionFormError}</span>
                      </div>
                    )}

                    {/* Action Selector */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <label
                        htmlFor="decision-radio-accept"
                        className={`cursor-pointer rounded-lg p-3 border flex flex-col gap-1 transition-all ${
                          decisionType === "accept"
                            ? "bg-emerald-50 border-emerald-500 shadow-sm"
                            : "bg-white border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            id="decision-radio-accept"
                            aria-label="Accept Exception"
                            type="radio"
                            name="decisionType"
                            value="accept"
                            checked={decisionType === "accept"}
                            onChange={() => setDecisionType("accept")}
                            className="text-emerald-600 focus:ring-emerald-500"
                          />
                          <span className="text-xs font-bold text-emerald-900">
                            Accept Exception
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500 pl-5">
                          Approve exceptions as compliant under submitted evidence.
                        </span>
                      </label>

                      <label
                        htmlFor="decision-radio-query"
                        className={`cursor-pointer rounded-lg p-3 border flex flex-col gap-1 transition-all ${
                          decisionType === "query"
                            ? "bg-amber-50 border-amber-500 shadow-sm"
                            : "bg-white border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            id="decision-radio-query"
                            aria-label="Raise Clarification Query"
                            type="radio"
                            name="decisionType"
                            value="query"
                            checked={decisionType === "query"}
                            onChange={() => setDecisionType("query")}
                            className="text-amber-600 focus:ring-amber-500"
                          />
                          <span className="text-xs font-bold text-amber-900">
                            Raise Clarification Query
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500 pl-5">
                          Re-open items and request explanation from college.
                        </span>
                      </label>

                      <label
                        htmlFor="decision-radio-escalate"
                        className={`cursor-pointer rounded-lg p-3 border flex flex-col gap-1 transition-all ${
                          decisionType === "escalate"
                            ? "bg-purple-50 border-purple-500 shadow-sm"
                            : "bg-white border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            id="decision-radio-escalate"
                            aria-label="Escalate to Committee"
                            type="radio"
                            name="decisionType"
                            value="escalate"
                            checked={decisionType === "escalate"}
                            onChange={() => setDecisionType("escalate")}
                            className="text-purple-600 focus:ring-purple-500"
                          />
                          <span className="text-xs font-bold text-purple-900">
                            Escalate to Committee
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500 pl-5">
                          Refer case to AICTE standing appellate council.
                        </span>
                      </label>
                    </div>

                    {/* Decision Note Textarea */}
                    <div>
                      <label htmlFor="review-decision-note" className="block text-xs font-medium text-slate-700 mb-1">
                        {decisionType === "accept"
                          ? "Approval Rationale Note"
                          : decisionType === "query"
                          ? "Clarification Inquiry / Question for Institution"
                          : "Escalation Reason & Notes"}
                        <span className="text-red-500 ml-1">*</span>
                      </label>
                      <textarea
                        id="review-decision-note"
                        aria-label="Officer Decision Note & Statutory Rationale"
                        rows={3}
                        required
                        value={decisionNote}
                        onChange={(e) => setDecisionNote(e.target.value)}
                        placeholder={
                          decisionType === "accept"
                            ? "e.g. Verified court order WP/2026/89 approving additional seats; quota reconciled."
                            : decisionType === "query"
                            ? "e.g. Please provide a legible certified copy of the state allotment letter."
                            : "e.g. Enrolment jump of 45% requires central vigilance committee inspection."
                        }
                        className="w-full rounded-md border border-slate-300 p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                      />
                    </div>

                    {/* Submit Button */}
                    <div className="flex justify-end gap-3 pt-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={closeDetail}
                        disabled={isSubmittingDecision}
                      >
                        Close
                      </Button>
                      <Button
                        type="submit"
                        size="sm"
                        disabled={isSubmittingDecision || decisionNote.trim().length < 3}
                        className={
                          decisionType === "accept"
                            ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                            : decisionType === "query"
                            ? "bg-amber-600 hover:bg-amber-700 text-white"
                            : "bg-purple-600 hover:bg-purple-700 text-white"
                        }
                      >
                        {isSubmittingDecision ? (
                          <div className="flex items-center gap-2">
                            <LoadingSpinner size="sm" />
                            Recording Decision...
                          </div>
                        ) : decisionType === "accept" ? (
                          "Accept & Resolve Exceptions"
                        ) : decisionType === "query" ? (
                          "Dispatch Query to College"
                        ) : (
                          "Confirm Escalation"
                        )}
                      </Button>
                    </div>
                  </form>
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
