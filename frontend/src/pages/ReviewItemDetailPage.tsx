import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  fetchReviewItemDetail,
  submitReviewDecision,
  getReviewDocumentDownloadUrl,
} from "../api/review";
import type { ReviewDecision, ReviewItemDetailResponse } from "../types/review";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { ErrorState } from "../components/ui/ErrorState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  HelpCircle,
  MessageSquare,
  ShieldAlert,
  User,
} from "lucide-react";

export function ReviewItemDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detailItem, setDetailItem] = useState<ReviewItemDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Decision state
  const [decisionType, setDecisionType] = useState<ReviewDecision>("accept");
  const [decisionNote, setDecisionNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);

  useDocumentTitle(detailItem ? `Review Item #${detailItem.id} - ${detailItem.institution_name}` : "Review Item Inspection");

  const loadItem = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchReviewItemDetail(parseInt(id, 10));
      setDetailItem(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load review item details.");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadItem();
  }, [loadItem]);

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detailItem) return;
    if (decisionType !== "accept" && (!decisionNote.trim() || decisionNote.trim().length < 5)) {
      setDecisionError("Please provide an explanatory note of at least 5 characters for queries or escalation.");
      return;
    }

    setSubmitting(true);
    setDecisionError(null);
    setDecisionSuccess(null);
    try {
      await submitReviewDecision(detailItem.id, {
        decision: decisionType,
        note: decisionNote.trim(),
      });
      setDecisionSuccess(`Decision '${decisionType.toUpperCase()}' applied successfully.`);
      setDecisionNote("");
      await loadItem();
    } catch (err) {
      setDecisionError(err instanceof Error ? err.message : "Failed to apply review decision.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadEvidence = (justificationId: number) => {
    if (!detailItem) return;
    const url = getReviewDocumentDownloadUrl(detailItem.id, justificationId);
    window.open(url, "_blank");
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-slate-600">Loading review inspection details...</p>
      </div>
    );
  }

  if (error || !detailItem) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ErrorState
          title="Review Item Not Found"
          message={error || "The review item could not be found."}
          onRetry={() => navigate("/aicte/review")}
        />
        <div className="mt-4">
          <Link to="/aicte/review" className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1.5">
            <ArrowLeft className="w-4 h-4" /> Back to Review Queue
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 space-y-6">
      {/* Header Bar */}
      <div className="border-b border-slate-200 pb-4">
        <Link
          to="/aicte/review"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition mb-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Review Queue
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Review Item #{detailItem.id}</h1>
              <Badge
                variant={
                  detailItem.status === "accepted"
                    ? "success"
                    : detailItem.status === "query_raised"
                    ? "warning"
                    : detailItem.status === "escalated"
                    ? "danger"
                    : "neutral"
                }
              >
                {detailItem.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Institution: <span className="font-semibold text-slate-800">{detailItem.institution_name}</span> &bull; AICTE ID:{" "}
              <span className="font-mono">{detailItem.aicte_id}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link to={`/aicte/submissions/${detailItem.submission_id}`}>
              <Button variant="outline" size="sm">
                View Formal Submission
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Grid: Submission Overview & Institution Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs border-b border-slate-100 pb-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            <span>Institution Overview</span>
          </div>
          <div className="text-xs space-y-2">
            <div>
              <span className="text-slate-500 block">Institution Name</span>
              <span className="font-semibold text-slate-900">{detailItem.institution_name}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Permanent AICTE ID</span>
              <span className="font-mono text-slate-800">{detailItem.aicte_id}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Academic Year</span>
              <span className="font-medium text-slate-900">{detailItem.academic_year}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs border-b border-slate-100 pb-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <span>Submission Metrics</span>
          </div>
          <div className="text-xs space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-slate-500 block">Flagged Exceptions</span>
                <span className="font-bold text-slate-900 text-sm">{detailItem.flags?.length ?? 0}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Inquiries Raised</span>
                <span className="font-bold text-slate-900 text-sm">{detailItem.queries?.length ?? 0}</span>
              </div>
            </div>
            <div>
              <span className="text-slate-500 block">Submission Status</span>
              <span className="font-bold text-slate-900 text-sm capitalize">{detailItem.submission_status}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Submitted At</span>
              <span className="text-slate-700">{detailItem.submitted_at ? new Date(detailItem.submitted_at).toLocaleString() : "N/A"}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs border-b border-slate-100 pb-2">
            <ShieldAlert className="w-4 h-4 text-blue-600" />
            <span>Flagged Items</span>
          </div>
          <div className="text-xs space-y-2">
            <div>
              <span className="text-slate-500 block">Associated Flags</span>
              <span className="font-bold text-slate-900">{detailItem.flags?.length || 0} items for review</span>
            </div>
            <div>
              <span className="text-slate-500 block">Review Stage</span>
              <span className="font-medium text-blue-700">Central Verification Authority</span>
            </div>
          </div>
        </div>
      </div>

      {/* Flagged Items & Justifications List */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
          <FileCheck2 className="w-5 h-5 text-blue-600" />
          <span>Underlying Validation Issues & Submitted Justifications</span>
        </h2>

        {!detailItem.flags || detailItem.flags.length === 0 ? (
          <p className="text-xs text-slate-500 italic py-4">No validation flags linked to this review item.</p>
        ) : (
          <div className="space-y-4">
            {detailItem.flags.map((flag) => (
              <div key={flag.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-2">
                  <div className="flex items-center gap-2">
                    <FlagBadge level={flag.level} />
                    <span className="font-mono font-bold text-slate-900">{flag.rule_code}</span>
                    {flag.field && <span className="text-slate-500 text-[11px]">field: {flag.field}</span>}
                  </div>
                  <Badge variant={flag.status === "justified" ? "warning" : flag.status === "resolved" ? "success" : "danger"}>
                    {flag.status.toUpperCase()}
                  </Badge>
                </div>

                <p className="text-slate-800 font-medium">{flag.message}</p>

                {flag.student_name && (
                  <div className="flex items-center gap-2 bg-white px-3 py-2 rounded border border-slate-200">
                    <User className="w-3.5 h-3.5 text-blue-600" />
                    <span>Student: <strong className="text-slate-900">{flag.student_name}</strong></span>
                    <span className="text-slate-400">&bull;</span>
                    <span className="font-mono text-slate-600">APAAR: {flag.student_apaar}</span>
                  </div>
                )}

                {flag.justifications && flag.justifications.length > 0 && (
                  <div className="space-y-2 mt-2">
                    <span className="font-semibold text-slate-800 block text-[11px] uppercase tracking-wider">
                      Institution Justification Evidence:
                    </span>
                    {flag.justifications.map((j) => (
                      <div key={j.id} className="bg-white p-3 rounded border border-blue-200 space-y-2">
                        <p className="text-slate-900 leading-relaxed">{j.text}</p>
                        {j.document_filename && (
                          <button
                            onClick={() => handleDownloadEvidence(j.id)}
                            className="inline-flex items-center gap-1.5 text-blue-700 hover:text-blue-900 font-medium text-xs underline"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Download Uploaded Proof ({j.document_filename})
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AICTE Officer Action Panel */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-blue-600" />
          <span>Regulatory Action & Determination</span>
        </h2>

        {decisionError && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{decisionError}</span>
          </div>
        )}
        {decisionSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{decisionSuccess}</span>
          </div>
        )}

        <form onSubmit={handleSubmitDecision} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label
              className={`p-3 border rounded-xl cursor-pointer transition flex items-center gap-3 ${
                decisionType === "accept"
                  ? "border-emerald-500 bg-emerald-50 text-emerald-900 font-semibold ring-2 ring-emerald-500"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              <input
                type="radio"
                name="decisionType"
                value="accept"
                checked={decisionType === "accept"}
                onChange={() => setDecisionType("accept")}
                className="sr-only"
              />
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <div className="text-xs">
                <span className="block">Accept & Certify</span>
                <span className="text-[10px] font-normal text-slate-500">Issue verifiable credentials</span>
              </div>
            </label>

            <label
              className={`p-3 border rounded-xl cursor-pointer transition flex items-center gap-3 ${
                decisionType === "query"
                  ? "border-amber-500 bg-amber-50 text-amber-900 font-semibold ring-2 ring-amber-500"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              <input
                type="radio"
                name="decisionType"
                value="query"
                checked={decisionType === "query"}
                onChange={() => setDecisionType("query")}
                className="sr-only"
              />
              <HelpCircle className="w-4 h-4 text-amber-600 shrink-0" />
              <div className="text-xs">
                <span className="block">Raise Inquiry</span>
                <span className="text-[10px] font-normal text-slate-500">Request college clarification</span>
              </div>
            </label>

            <label
              className={`p-3 border rounded-xl cursor-pointer transition flex items-center gap-3 ${
                decisionType === "escalate"
                  ? "border-purple-500 bg-purple-50 text-purple-900 font-semibold ring-2 ring-purple-500"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              <input
                type="radio"
                name="decisionType"
                value="escalate"
                checked={decisionType === "escalate"}
                onChange={() => setDecisionType("escalate")}
                className="sr-only"
              />
              <ShieldAlert className="w-4 h-4 text-purple-600 shrink-0" />
              <div className="text-xs">
                <span className="block">Escalate Review</span>
                <span className="text-[10px] font-normal text-slate-500">Escalate to Regional Office</span>
              </div>
            </label>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Decision Note / Directions to Institution
            </label>
            <textarea
              rows={3}
              value={decisionNote}
              onChange={(e) => setDecisionNote(e.target.value)}
              placeholder={
                decisionType === "accept"
                  ? "Optional: Notes for verification audit record..."
                  : "Mandatory: Specify exact missing documents, sanctions, or reasons for this directive..."
              }
              className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Link to="/aicte/review">
              <Button type="button" variant="outline" size="sm">
                Cancel
              </Button>
            </Link>
            <Button type="submit" variant="primary" size="sm" disabled={submitting}>
              {submitting ? "Applying..." : "Submit Determination"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
