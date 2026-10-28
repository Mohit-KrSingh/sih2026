import { useEffect, useState } from "react";
import {
  getAicteChangeRequests,
  decideAicteChangeRequest,
  getAicteChangeRequestEvidenceUrl,
} from "../api/changeRequests";
import type { ChangeRequest, ChangeRequestStatus } from "../types/changeRequests";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  FileCheck,
  FileText,
  RefreshCw,
  Search,
  X,
  XCircle,
} from "lucide-react";

export function AicteChangeRequestsPage() {
  useDocumentTitle("Change Requests Approval Queue");
  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Review Drawer / Modal
  const [activeRequest, setActiveRequest] = useState<ChangeRequest | null>(null);
  const [decisionNote, setDecisionNote] = useState<string>("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const loadRequests = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getAicteChangeRequests({
        status: statusFilter === "all" ? undefined : statusFilter,
      });
      setRequests(res.items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load change requests.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, [statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const openDecisionModal = (req: ChangeRequest) => {
    setActiveRequest(req);
    setDecisionNote("");
    setDecisionError(null);
  };

  const handleDecision = async (decision: "approve" | "reject") => {
    if (!activeRequest) return;
    setIsSubmittingDecision(true);
    setDecisionError(null);

    try {
      await decideAicteChangeRequest(activeRequest.id, {
        decision,
        decision_note: decisionNote.trim() || undefined,
      });

      setSuccessBanner(
        `Change request #${activeRequest.id} for ${activeRequest.student?.name} was ${decision}d.`
      );
      setActiveRequest(null);
      await loadRequests();
      setTimeout(() => setSuccessBanner(null), 6000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit decision.";
      setDecisionError(msg);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  // Metrics
  const totalCount = requests.length;
  const pendingCount = requests.filter((r) => r.status === "pending").length;
  const approvedCount = requests.filter((r) => r.status === "approved").length;
  const rejectedCount = requests.filter((r) => r.status === "rejected").length;

  const filteredRequests = requests.filter((r) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const instName = r.institution?.name?.toLowerCase() || "";
    const aicteId = r.institution?.aicte_id?.toLowerCase() || "";
    const studentName = r.student?.name?.toLowerCase() || "";
    const apaarId = r.student?.apaar_id?.toLowerCase() || "";
    const field = r.field.toLowerCase();
    return (
      instName.includes(term) ||
      aicteId.includes(term) ||
      studentName.includes(term) ||
      apaarId.includes(term) ||
      field.includes(term)
    );
  });

  const renderStatusBadge = (status: ChangeRequestStatus) => {
    switch (status) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-300">
            <Clock className="w-3.5 h-3.5" />
            Pending Review
          </span>
        );
      case "approved":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Approved
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-300">
            <XCircle className="w-3.5 h-3.5" />
            Rejected
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl border border-blue-200">
              <FileCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                AICTE Student Change Requests Review
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Review and approve/reject post-lock correction, withdrawal, or transfer requests submitted by colleges.
              </p>
            </div>
          </div>
        </div>

        <Button
          variant="outline"
          onClick={loadRequests}
          disabled={isLoading}
          className="flex items-center gap-2 self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          Refresh Queue
        </Button>
      </div>

      {/* Success Notification */}
      {successBanner && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-3 text-emerald-800 text-sm font-medium">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span>{successBanner}</span>
          </div>
          <button
            onClick={() => setSuccessBanner(null)}
            className="text-emerald-600 hover:text-emerald-800 p-1 rounded-md"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Requests
            </p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</p>
          </div>
          <div className="p-3 bg-slate-100 text-slate-700 rounded-xl">
            <FileText className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Pending Action
            </p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{pendingCount}</p>
          </div>
          <div className="p-3 bg-amber-50 text-amber-700 rounded-xl border border-amber-200">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Approved
            </p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{approvedCount}</p>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Rejected
            </p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{rejectedCount}</p>
          </div>
          <div className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Status Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg w-full md:w-auto overflow-x-auto">
          {[
            { id: "all", label: "All Requests" },
            { id: "pending", label: "Pending Action" },
            { id: "approved", label: "Approved" },
            { id: "rejected", label: "Rejected" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                statusFilter === tab.id
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search college, AICTE ID, student, APAAR..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Main Table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 flex justify-center items-center shadow-sm">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to Load Change Requests"
          message={error}
          onRetry={loadRequests}
        />
      ) : filteredRequests.length === 0 ? (
        <EmptyState
          icon={<FileCheck className="w-6 h-6 text-slate-400" />}
          title="No Change Requests Found"
          description={
            searchTerm || statusFilter !== "all"
              ? "No change requests matched your search criteria."
              : "No post-lock change requests in the AICTE queue."
          }
          actionLabel={statusFilter !== "all" ? "Clear Filters" : undefined}
          onAction={statusFilter !== "all" ? () => setStatusFilter("all") : undefined}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Req #</th>
                  <th className="py-3 px-4">Institution & AICTE ID</th>
                  <th className="py-3 px-4">Student & APAAR</th>
                  <th className="py-3 px-4">Field Changed</th>
                  <th className="py-3 px-4">Old Value</th>
                  <th className="py-3 px-4">Requested Value</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Reason & Evidence</th>
                  <th className="py-3 px-4 text-right">Review Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredRequests.map((cr) => (
                  <tr key={cr.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-900">
                      #{cr.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">
                        {cr.institution?.name || "Institution"}
                      </div>
                      <div className="font-mono text-slate-500 text-[11px] mt-0.5">
                        {cr.institution?.aicte_id || "AICTE ID"} • {cr.institution?.state}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">
                        {cr.student?.name || `Student #${cr.student_id}`}
                      </div>
                      <div className="font-mono text-slate-500 text-[11px] mt-0.5">
                        APAAR: {cr.student?.apaar_id || "—"}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium text-blue-700">
                      {cr.field}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      <span className="line-through bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                        {cr.old_value || "—"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-900">
                      <span className="bg-blue-50 text-blue-800 px-2 py-0.5 rounded border border-blue-200 font-semibold text-[11px]">
                        {cr.new_value}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">{renderStatusBadge(cr.status)}</td>
                    <td className="py-3.5 px-4 max-w-xs">
                      <p className="line-clamp-2 text-slate-700">{cr.reason}</p>
                      {cr.document_ref && (
                        <a
                          href={getAicteChangeRequestEvidenceUrl(cr.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 font-medium mt-1"
                        >
                          <Download className="w-3 h-3" />
                          View Evidence Document
                        </a>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {cr.status === "pending" ? (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => openDecisionModal(cr)}
                        >
                          Review & Decide
                        </Button>
                      ) : (
                        <button
                          onClick={() => openDecisionModal(cr)}
                          className="text-xs text-slate-500 hover:text-slate-800 underline"
                        >
                          View Decision
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Review & Decision Modal */}
      {activeRequest && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-2xl overflow-hidden animate-scaleUp">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <FileCheck className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Review Change Request #{activeRequest.id}
                </h3>
              </div>
              <button
                onClick={() => setActiveRequest(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-5">
              {decisionError && (
                <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{decisionError}</span>
                </div>
              )}

              {/* Institution & Student Context */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 font-semibold uppercase text-[10px] block">
                    Institution
                  </span>
                  <p className="font-bold text-slate-900 mt-0.5">
                    {activeRequest.institution?.name}
                  </p>
                  <p className="text-slate-500 font-mono text-[11px]">
                    AICTE ID: {activeRequest.institution?.aicte_id}
                  </p>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold uppercase text-[10px] block">
                    Student Record
                  </span>
                  <p className="font-bold text-slate-900 mt-0.5">
                    {activeRequest.student?.name}
                  </p>
                  <p className="text-slate-500 font-mono text-[11px]">
                    APAAR ID: {activeRequest.student?.apaar_id}
                  </p>
                </div>
              </div>

              {/* Proposed Change */}
              <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/50 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-blue-900 uppercase tracking-wider">
                    Target Field: <code className="font-mono">{activeRequest.field}</code>
                  </span>
                  {renderStatusBadge(activeRequest.status)}
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 block">Current Value (Old)</span>
                    <span className="font-medium text-slate-700 bg-white px-2.5 py-1 rounded border border-slate-200 block mt-1">
                      {activeRequest.old_value || "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Requested Value (New)</span>
                    <span className="font-bold text-blue-800 bg-white px-2.5 py-1 rounded border border-blue-300 block mt-1">
                      {activeRequest.new_value}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-500 block text-xs">Institution Reason / Justification</span>
                  <p className="text-xs text-slate-800 bg-white p-2.5 rounded border border-slate-200 mt-1">
                    {activeRequest.reason}
                  </p>
                </div>

                {activeRequest.document_ref && (
                  <div>
                    <a
                      href={getAicteChangeRequestEvidenceUrl(activeRequest.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-blue-700 hover:text-blue-900 font-semibold underline"
                    >
                      <Download className="w-3.5 h-3.5" /> Download Uploaded Evidence Document
                    </a>
                  </div>
                )}
              </div>

              {/* Already decided details */}
              {activeRequest.status !== "pending" && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
                  <span className="font-bold text-slate-900 block">Decision Record</span>
                  <p className="text-slate-600">
                    Decided by:{" "}
                    <span className="font-semibold text-slate-800">
                      {activeRequest.decided_by_email || "AICTE Officer"}
                    </span>{" "}
                    at {activeRequest.decided_at ? new Date(activeRequest.decided_at).toLocaleString("en-IN") : "—"}
                  </p>
                  {activeRequest.decision_note && (
                    <p className="text-slate-700">
                      Officer Note: <em>{activeRequest.decision_note}</em>
                    </p>
                  )}
                </div>
              )}

              {/* If pending: Decision Inputs and Actions */}
              {activeRequest.status === "pending" && (
                <div className="space-y-4 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      AICTE Officer Decision Note / Remarks
                    </label>
                    <textarea
                      rows={3}
                      placeholder="Enter verification remarks, reason for approval or grounds for rejection..."
                      value={decisionNote}
                      onChange={(e) => setDecisionNote(e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setActiveRequest(null)}
                      disabled={isSubmittingDecision}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() => handleDecision("reject")}
                      disabled={isSubmittingDecision}
                      className="flex items-center gap-1.5"
                    >
                      <XCircle className="w-4 h-4" /> Reject Request
                    </Button>
                    <Button
                      type="button"
                      variant="primary"
                      onClick={() => handleDecision("approve")}
                      disabled={isSubmittingDecision}
                      className="flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Approve & Apply Change
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
