import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { fetchCollegeQueries, respondToCollegeQuery } from "../api/review";
import type { CollegeQueryResponse } from "../types/review";
import { Button } from "../components/ui/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { FlagBadge } from "../components/ui/Badge";
import {
  AlertCircle,
  CheckCircle2,
  FileQuestion,
  HelpCircle,
  MessageSquare,
  Paperclip,
  RefreshCw,
  Send,
} from "lucide-react";

export function CollegeQueriesPage() {
  useDocumentTitle("AICTE Inquiries & Directives");
  const { user } = useAuth();
  const institutionId = user?.institution_id;

  const [queries, setQueries] = useState<CollegeQueryResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [academicYear, setAcademicYear] = useState<string>("2026-27");

  // Response Form States (per query id)
  const [activeQueryId, setActiveQueryId] = useState<number | null>(null);
  const [responseText, setResponseText] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadQueries = async () => {
    if (!institutionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchCollegeQueries(institutionId, {
        state: stateFilter,
        academic_year: academicYear,
      });
      setQueries(res.items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load queries.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (institutionId) {
      loadQueries();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [institutionId, stateFilter, academicYear]);

  const handleOpenResponse = (query: CollegeQueryResponse) => {
    setActiveQueryId(query.id);
    setResponseText(query.response || "");
    setSelectedFile(null);
    setFormError(null);
    setSuccessMsg(null);
  };

  const handleCancelResponse = () => {
    setActiveQueryId(null);
    setResponseText("");
    setSelectedFile(null);
    setFormError(null);
    setSuccessMsg(null);
  };

  const handleSubmitResponse = async (e: React.FormEvent, queryId: number) => {
    e.preventDefault();
    if (!institutionId) return;

    if (!responseText.trim() || responseText.trim().length < 5) {
      setFormError("Response clarification must be at least 5 characters long.");
      return;
    }

    setIsSubmitting(true);
    setFormError(null);
    try {
      await respondToCollegeQuery(institutionId, queryId, {
        response: responseText.trim(),
        document: selectedFile || undefined,
      });
      setSuccessMsg("Clarification successfully submitted. Submission returned to Under Review.");
      setActiveQueryId(null);
      setResponseText("");
      setSelectedFile(null);
      // Reload queries
      loadQueries();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit response.";
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const pendingQueries = queries.filter((q) => q.state === "pending");
  const answeredQueries = queries.filter((q) => q.state === "answered");

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              AICTE Clarification Queries
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
              SPEC Section 10 & 13
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Answer clarification inquiries raised by AICTE officers regarding your submitted annual
            exceptions. Answering returns your submission to officer review.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="2026-27">AY 2026-27 (Current)</option>
            <option value="2025-26">AY 2025-26</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            onClick={loadQueries}
            disabled={isLoading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Tabs & Counter */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <button
            aria-label="Filter by all queries"
            onClick={() => setStateFilter("all")}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              stateFilter === "all"
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            All Queries ({queries.length})
          </button>
          <button
            aria-label="Filter by pending response"
            onClick={() => setStateFilter("pending")}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
              stateFilter === "pending"
                ? "bg-amber-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            <span>Pending Response</span>
            {pendingQueries.length > 0 && (
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  stateFilter === "pending"
                    ? "bg-white text-amber-700"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {pendingQueries.length}
              </span>
            )}
          </button>
          <button
            aria-label="Filter by answered queries under review"
            onClick={() => setStateFilter("answered")}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              stateFilter === "answered"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Answered / Under Review ({answeredQueries.length})
          </button>
        </div>

        {pendingQueries.length > 0 && (
          <div className="text-xs text-amber-800 font-medium flex items-center gap-1.5 bg-amber-50 px-3 py-1.5 rounded-md border border-amber-200">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span>Action Required: You have {pendingQueries.length} pending clarification inquiry.</span>
          </div>
        )}
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center shadow-sm">
          <LoadingSpinner className="mx-auto" />
          <p className="text-sm text-slate-500 mt-4">Loading inquiries from AICTE...</p>
        </div>
      ) : error ? (
        <ErrorState title="Failed to Load Queries" message={error} onRetry={loadQueries} />
      ) : queries.length === 0 ? (
        <EmptyState
          title="No Clarification Queries"
          description={
            stateFilter === "pending"
              ? "All official queries have been answered. There are no pending inquiries requiring your attention."
              : "No clarification inquiries have been raised by AICTE for this academic year."
          }
          actionLabel={stateFilter !== "all" ? "View All Queries" : undefined}
          onAction={() => setStateFilter("all")}
        />
      ) : (
        <div className="space-y-4">
          {queries.map((q) => {
            const isPending = q.state === "pending";
            const isResponding = activeQueryId === q.id;

            return (
              <div
                key={q.id}
                className={`bg-white rounded-xl border transition-all shadow-sm overflow-hidden ${
                  isPending
                    ? "border-amber-300 ring-1 ring-amber-100"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                {/* Query Header */}
                <div className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/50">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${
                        isPending
                          ? "bg-amber-100 text-amber-700"
                          : "bg-emerald-100 text-emerald-700"
                      }`}
                    >
                      {isPending ? (
                        <FileQuestion className="w-5 h-5" />
                      ) : (
                        <CheckCircle2 className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">
                          Query #{q.id}
                        </span>
                        <span className="text-xs text-slate-500">
                          from {q.officer_name || "AICTE Officer"}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                        <span>Received {new Date(q.created_at).toLocaleString("en-IN")}</span>
                        {q.receipt_no && (
                          <>
                            <span>•</span>
                            <span className="font-mono">Receipt: {q.receipt_no}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div>
                    {isPending ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                        <HelpCircle className="w-3.5 h-3.5" />
                        Pending Your Response
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                        <RefreshCw className="w-3.5 h-3.5" />
                        Answered / Under Review
                      </span>
                    )}
                  </div>
                </div>

                {/* Query Body */}
                <div className="p-6 space-y-5">
                  {/* Officer Inquiry Message */}
                  <div className="rounded-lg bg-amber-50/60 border border-amber-200 p-4 space-y-1">
                    <div className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5" />
                      AICTE Officer Clarification Inquiry:
                    </div>
                    <p className="text-sm text-slate-900 font-medium whitespace-pre-wrap">
                      {q.message}
                    </p>
                  </div>

                  {/* Related Exception Details */}
                  {q.flags && q.flags.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-slate-700">
                        Related Exception Flags Re-Opened for Clarification:
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {q.flags.map((fl) => (
                          <div
                            key={fl.id}
                            className="p-3 rounded-lg border border-red-200 bg-red-50/30 text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between">
                              <FlagBadge level="exception" label={fl.rule_code} />
                              <span className="text-slate-400 font-mono">Flag #{fl.id}</span>
                            </div>
                            <p className="font-medium text-slate-900">{fl.message}</p>
                            {fl.student_name && (
                              <p className="text-slate-600">
                                Student: <span className="font-semibold">{fl.student_name}</span>
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Existing Response Display if already answered */}
                  {q.response && !isResponding && (
                    <div className="rounded-lg bg-emerald-50/50 border border-emerald-200 p-4 space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-emerald-800">
                        <span>Your Submitted Clarification Response:</span>
                        <span className="text-slate-400 font-normal">
                          {q.responded_at
                            ? `Submitted on ${new Date(q.responded_at).toLocaleString("en-IN")}`
                            : ""}
                        </span>
                      </div>
                      <p className="text-xs text-slate-800 whitespace-pre-wrap bg-white p-3 rounded border border-slate-200">
                        {q.response}
                      </p>
                    </div>
                  )}

                  {/* Response Form or Action Button */}
                  {isPending && !isResponding && (
                    <div className="flex justify-end pt-2">
                      <Button
                        size="sm"
                        onClick={() => handleOpenResponse(q)}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-medium"
                      >
                        <Send className="w-3.5 h-3.5 mr-1.5" />
                        Respond to Inquiry
                      </Button>
                    </div>
                  )}

                  {isResponding && (
                    <form
                      onSubmit={(e) => handleSubmitResponse(e, q.id)}
                      className="border-t border-slate-200 pt-4 space-y-4 bg-slate-50/80 -mx-6 -mb-6 p-6"
                    >
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                        <Send className="w-3.5 h-3.5 text-blue-600" />
                        Submit Official College Clarification
                      </h4>

                      {formError && (
                        <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 flex-shrink-0" />
                          <span>{formError}</span>
                        </div>
                      )}

                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Detailed Written Response / Clarification
                          <span className="text-red-500 ml-1">*</span>
                        </label>
                        <textarea
                          rows={4}
                          required
                          value={responseText}
                          onChange={(e) => setResponseText(e.target.value)}
                          placeholder="Provide clear legal, statutory, or factual details answering the officer's inquiry..."
                          className="w-full rounded-md border border-slate-300 p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                        />
                        <p className="text-[11px] text-slate-500 mt-1">
                          Minimum 5 characters. This explanation will be reviewed by the AICTE officer.
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Optional Supporting Evidence Document (PDF, JPG, PNG up to 10MB)
                        </label>
                        <div className="flex items-center gap-3">
                          <input
                            type="file"
                            accept=".pdf,.png,.jpg,.jpeg"
                            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                            className="text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                          />
                          {selectedFile && (
                            <span className="text-xs text-slate-600 flex items-center gap-1 font-mono">
                              <Paperclip className="w-3.5 h-3.5 text-slate-400" />
                              {selectedFile.name} ({(selectedFile.size / 1024).toFixed(0)} KB)
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex justify-end gap-3 pt-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleCancelResponse}
                          disabled={isSubmitting}
                        >
                          Cancel
                        </Button>
                        <Button
                          type="submit"
                          size="sm"
                          disabled={isSubmitting || responseText.trim().length < 5}
                          className="bg-blue-600 hover:bg-blue-700 text-white"
                        >
                          {isSubmitting ? (
                            <div className="flex items-center gap-2">
                              <LoadingSpinner size="sm" />
                              Submitting Response...
                            </div>
                          ) : (
                            "Submit Response to AICTE"
                          )}
                        </Button>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
