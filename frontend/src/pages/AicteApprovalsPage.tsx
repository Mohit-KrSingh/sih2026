import React, { useEffect, useState, useMemo } from "react";
import {
  listActivationRequests,
  approveActivation,
  rejectActivation,
  type ActivationRequestResponse,
  type ActivationDecisionResponse,
} from "../api/institutions";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ui/Table";
import {
  CheckCircle2,
  Download,
  FileText,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";

export function AicteApprovalsPage() {
  useDocumentTitle("Institution Approvals Queue");
  const [requests, setRequests] = useState<ActivationRequestResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal State
  const [selectedRequest, setSelectedRequest] = useState<ActivationRequestResponse | null>(null);
  const [modalMode, setModalMode] = useState<"view" | "approve" | "reject" | "success">("view");

  // Approval form state
  const [adminEmail, setAdminEmail] = useState("");
  const [approvalNotes, setApprovalNotes] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  // Rejection form state
  const [rejectReason, setRejectReason] = useState("");

  // Approval success result state
  const [approvalResult, setApprovalResult] = useState<ActivationDecisionResponse | null>(null);

  const fetchRequests = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listActivationRequests();
      setRequests(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load activation requests";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const isPending = (status: string) =>
    status.toLowerCase() === "pending" || status.toLowerCase() === "pending_approval";

  const filteredRequests = useMemo(() => {
    return requests.filter((r) => {
      let matchesStatus = true;
      if (statusFilter === "pending" || statusFilter === "pending_approval") {
        matchesStatus = isPending(r.status);
      } else if (statusFilter !== "all") {
        matchesStatus = r.status.toLowerCase() === statusFilter.toLowerCase();
      }
      const matchesSearch =
        !searchQuery.trim() ||
        r.institution_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.institution_aicte_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.signatory_name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [requests, statusFilter, searchQuery]);

  const pendingCount = useMemo(() => {
    return requests.filter((r) => isPending(r.status)).length;
  }, [requests]);

  const openReviewModal = (req: ActivationRequestResponse) => {
    setSelectedRequest(req);
    setModalMode("view");
    setAdminEmail("");
    setApprovalNotes("");
    setRejectReason("");
    setDecisionError(null);
    setApprovalResult(null);
  };

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequest) return;
    setIsSubmittingDecision(true);
    setDecisionError(null);

    try {
      const res = await approveActivation(selectedRequest.id, {
        admin_email: adminEmail.trim() || undefined,
        notes: approvalNotes.trim() || undefined,
      });
      setApprovalResult(res);
      setModalMode("success");
      fetchRequests(); // Refresh table
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to approve activation claim";
      setDecisionError(msg);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequest) return;
    if (!rejectReason.trim()) {
      setDecisionError("Rejection reason is required");
      return;
    }
    setIsSubmittingDecision(true);
    setDecisionError(null);

    try {
      await rejectActivation(selectedRequest.id, {
        reason: rejectReason.trim(),
      });
      setSelectedRequest(null);
      fetchRequests();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject activation claim";
      setDecisionError(msg);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Institution Approvals Queue
            </h1>
            {pendingCount > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                {pendingCount} Pending
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Review institution activation claims, verify signatory credentials, and authorize primary administrator accounts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchRequests}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />}
          >
            Refresh queue
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg text-xs font-medium w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setStatusFilter("all")}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              statusFilter === "all"
                ? "bg-white text-slate-900 shadow-sm font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            All claims ({requests.length})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("pending")}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              statusFilter === "pending" || statusFilter === "pending_approval"
                ? "bg-white text-blue-700 shadow-sm font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Pending ({pendingCount})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("approved")}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              statusFilter === "approved"
                ? "bg-white text-emerald-700 shadow-sm font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Approved
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("rejected")}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              statusFilter === "rejected"
                ? "bg-white text-red-700 shadow-sm font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Rejected
          </button>
        </div>

        <div className="w-full sm:w-72">
          <Input
            placeholder="Search by college or AICTE ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Main Table / State */}
      {isLoading ? (
        <div className="py-16 text-center">
          <LoadingSpinner size="lg" label="Loading activation queue..." />
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to Load Queue"
          message={error}
          onRetry={fetchRequests}
        />
      ) : filteredRequests.length === 0 ? (
        <EmptyState
          title="No Activation Claims Found"
          description={
            statusFilter !== "all"
              ? `There are no activation requests matching status '${statusFilter}'.`
              : "No institution activation claims have been filed yet."
          }
        />
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Claim ID</TableHead>
                <TableHead>AICTE ID</TableHead>
                <TableHead>Institution Name</TableHead>
                <TableHead>Authorized Signatory</TableHead>
                <TableHead>Signatory Ref</TableHead>
                <TableHead>Submitted At</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRequests.map((req) => (
                <TableRow key={req.id}>
                  <TableCell className="font-mono text-xs font-semibold text-slate-700">
                    #{req.id}
                  </TableCell>
                  <TableCell className="font-mono text-xs font-medium text-slate-900">
                    {req.institution_aicte_id}
                  </TableCell>
                  <TableCell className="font-medium text-slate-900 max-w-xs truncate">
                    {req.institution_name}
                  </TableCell>
                  <TableCell className="text-slate-700 text-xs">{req.signatory_name}</TableCell>
                  <TableCell className="font-mono text-[11px] text-slate-500">
                    {req.signatory_ref}
                  </TableCell>
                  <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                    {new Date(req.created_at).toLocaleDateString()} {new Date(req.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                        req.status === "approved"
                          ? "bg-emerald-100 text-emerald-800"
                          : req.status === "rejected"
                            ? "bg-red-100 text-red-800"
                            : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {isPending(req.status) ? "Pending Approval" : req.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <a
                        href={`/api/v1/institutions/activation/requests/${req.id}/letter`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
                        title="View Authorisation Letter"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Letter</span>
                      </a>
                      <Button
                        size="sm"
                        variant={isPending(req.status) ? "primary" : "secondary"}
                        onClick={() => openReviewModal(req)}
                      >
                        {isPending(req.status) ? "Review claim" : "View details"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Review & Decision Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-xs font-mono font-semibold text-blue-600">
                  CLAIM #{selectedRequest.id}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                  Institution Activation Review
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedRequest(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg text-sm"
              >
                ✕
              </button>
            </div>

            {/* Success state: credentials issued */}
            {modalMode === "success" && approvalResult ? (
              <div className="space-y-4 animate-fadeIn">
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center space-y-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                  <h4 className="font-bold text-emerald-900 text-base">Institution Claim Approved</h4>
                  <p className="text-xs text-emerald-800">
                    Primary college administrator account created with mandatory MFA enforced.
                  </p>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2 text-xs">
                  <div className="flex justify-between border-b border-slate-200 pb-1.5">
                    <span className="text-slate-500">Administrator Email:</span>
                    <span className="font-mono font-bold text-slate-900">
                      {approvalResult.admin_email}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200 pb-1.5">
                    <span className="text-slate-500">Initial Temporary Password:</span>
                    <span className="font-mono font-bold text-slate-900">
                      {approvalResult.initial_password}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200 pb-1.5">
                    <span className="text-slate-500">TOTP MFA Enabled:</span>
                    <span className="font-semibold text-emerald-700">Enforced</span>
                  </div>
                  {approvalResult.mfa_secret && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">MFA Secret Seed:</span>
                      <span className="font-mono text-slate-900">{approvalResult.mfa_secret}</span>
                    </div>
                  )}
                </div>

                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-start gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-700 shrink-0 mt-0.5" />
                  <span>
                    Initial credentials have been recorded in the immutable audit log. The institution
                    can now access the portal via College Login.
                  </span>
                </div>

                <div className="flex justify-end pt-2">
                  <Button variant="primary" onClick={() => setSelectedRequest(null)}>
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              /* Claim details and review actions */
              <div className="space-y-4">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5 text-xs">
                  <div>
                    <span className="text-slate-500">Institution:</span>
                    <p className="font-bold text-slate-900 text-sm">
                      {selectedRequest.institution_name}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-slate-700">
                    <div>
                      <span className="text-slate-500">AICTE ID:</span>
                      <p className="font-mono font-semibold text-slate-900">
                        {selectedRequest.institution_aicte_id}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">Current Queue Status:</span>
                      <p className="font-semibold capitalize text-slate-900">
                        {selectedRequest.status.replace("_", " ")}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">Authorized Signatory:</span>
                      <p className="font-semibold text-slate-900">
                        {selectedRequest.signatory_name}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">DigiLocker Identity Ref:</span>
                      <p className="font-mono text-slate-900">{selectedRequest.signatory_ref}</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                    <span className="text-slate-500">Authorisation Letter:</span>
                    <a
                      href={`/api/v1/institutions/activation/requests/${selectedRequest.id}/letter`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-blue-600 hover:underline font-semibold"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download attached document</span>
                    </a>
                  </div>
                </div>

                {decisionError && (
                  <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-500 shrink-0" />
                    <span>{decisionError}</span>
                  </div>
                )}

                {/* Approve Form View */}
                {modalMode === "approve" && (
                  <form onSubmit={handleApprove} className="space-y-4 border-t border-slate-200 pt-3">
                    <h4 className="text-sm font-bold text-slate-900">Approve Activation Claim</h4>
                    <p className="text-xs text-slate-500">
                      Approval activates the college account and issues a primary administrator credential.
                    </p>

                    <Input
                      label="Primary Administrator Email (optional, defaults to institution official contact)"
                      placeholder="admin@college.edu.in"
                      value={adminEmail}
                      onChange={(e) => setAdminEmail(e.target.value)}
                    />

                    <Input
                      label="AICTE Officer Review Notes (optional)"
                      placeholder="e.g. Verified via official AICTE state council records"
                      value={approvalNotes}
                      onChange={(e) => setApprovalNotes(e.target.value)}
                    />

                    <div className="flex justify-end gap-2 pt-2">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setModalMode("view")}
                      >
                        Back
                      </Button>
                      <Button
                        type="submit"
                        variant="primary"
                        isLoading={isSubmittingDecision}
                        loadingText="Approving..."
                        leftIcon={<CheckCircle2 className="w-4 h-4" />}
                      >
                        Confirm approval
                      </Button>
                    </div>
                  </form>
                )}

                {/* Reject Form View */}
                {modalMode === "reject" && (
                  <form onSubmit={handleReject} className="space-y-4 border-t border-slate-200 pt-3">
                    <h4 className="text-sm font-bold text-red-800">Reject Activation Claim</h4>
                    <p className="text-xs text-slate-500">
                      Provide a clear reason for rejection. This will be visible to the institution in their claim tracker.
                    </p>

                    <div className="space-y-1">
                      <label className="block text-xs font-semibold text-slate-700">
                        Reason for Rejection <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        rows={3}
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="e.g. Authorisation letter does not contain the official seal of the institution head."
                        className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-red-500"
                        required
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setModalMode("view")}
                      >
                        Back
                      </Button>
                      <Button
                        type="submit"
                        variant="danger"
                        isLoading={isSubmittingDecision}
                        loadingText="Rejecting..."
                        leftIcon={<XCircle className="w-4 h-4" />}
                      >
                        Confirm rejection
                      </Button>
                    </div>
                  </form>
                )}

                {/* Default View Mode */}
                {modalMode === "view" && (
                  <div className="flex items-center justify-between border-t border-slate-200 pt-4">
                    <Button variant="secondary" onClick={() => setSelectedRequest(null)}>
                      Close
                    </Button>

                    {isPending(selectedRequest.status) ? (
                      <div className="flex items-center gap-2">
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setModalMode("reject")}
                          leftIcon={<XCircle className="w-4 h-4" />}
                        >
                          Reject claim
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => setModalMode("approve")}
                          leftIcon={<CheckCircle2 className="w-4 h-4" />}
                        >
                          Approve claim
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500">
                        This claim is already resolved ({selectedRequest.status}).
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
