import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getSubmissionReceipt, getSubmissionGate } from "../api/submissions";
import { downloadCollegeSubmission } from "../api/reports";
import type { SubmissionReceiptResponse, SubmissionGateResponse } from "../types/submissions";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { ErrorState } from "../components/ui/ErrorState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  ArrowLeft,
  Building2,
  Copy,
  Download,
  FileCheck2,
  Lock,
  ShieldCheck,
  User,
} from "lucide-react";

export function SubmissionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, isAicte } = useAuth();

  // Institution ID: if college user, use user's institution; if AICTE, default or from submission
  const institutionId = user?.institution_id ?? 1;

  const [receipt, setReceipt] = useState<SubmissionReceiptResponse | null>(null);
  const [gate, setGate] = useState<SubmissionGateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState(false);

  useDocumentTitle(receipt ? `Receipt: ${receipt.receipt_no}` : "Submission Details");

  useEffect(() => {
    let isMounted = true;
    async function loadReceipt() {
      setIsLoading(true);
      setError(null);
      try {
        const [receiptData, gateData] = await Promise.all([
          getSubmissionReceipt(institutionId).catch(() => null),
          getSubmissionGate(institutionId).catch(() => null),
        ]);

        if (isMounted) {
          if (receiptData) {
            setReceipt(receiptData);
          }
          if (gateData) {
            setGate(gateData);
          }
          if (!receiptData && !gateData) {
            setError("No submission record found for this institution.");
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load submission receipt.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadReceipt();
    return () => {
      isMounted = false;
    };
  }, [institutionId, id]);

  const copyReceiptToken = () => {
    const token = receipt?.receipt_no || gate?.receipt_no;
    if (!token) return;
    navigator.clipboard.writeText(token);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2000);
  };

  const handleDownloadReport = async () => {
    try {
      await downloadCollegeSubmission(institutionId, "pdf", receipt?.academic_year || "2026-27");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to download submission summary.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-slate-600">Loading submission details...</p>
      </div>
    );
  }

  const backLink = isAicte ? "/aicte/review" : "/college/submit";
  const backText = isAicte ? "Back to Review Queue" : "Back to Submission Gate";

  if (error && !receipt && !gate) {
    return (
      <div className="max-w-4xl mx-auto py-6 px-4 space-y-6">
        <Link
          to={backLink}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition mb-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> {backText}
        </Link>
        <ErrorState title="Submission Not Found" message={error} />
      </div>
    );
  }

  const receiptNo = receipt?.receipt_no || gate?.receipt_no || `REC-2026-${institutionId}-${id}`;
  const instName = receipt?.institution_name || gate?.institution_name || "Institution";
  const aicteId = receipt?.aicte_id || gate?.aicte_id || "AICTE-INST";
  const academicYear = receipt?.academic_year || gate?.academic_year || "2026-27";
  const totalStudents = receipt?.total_students ?? gate?.total_students ?? 0;
  const regularStudents = receipt?.regular_students ?? 0;
  const supernumeraryStudents = receipt?.supernumerary_students ?? 0;
  const submittedAt = receipt?.submitted_at || gate?.submitted_at || "Recent";

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 space-y-6">
      {/* Breadcrumb / Back Link */}
      <div className="border-b border-slate-200 pb-4">
        <Link
          to={backLink}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition mb-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> {backText}
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Submission Receipt</h1>
              <Badge variant="success">LOCKED & SUBMITTED</Badge>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Receipt Reference: <span className="font-mono font-bold text-slate-800">{receiptNo}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadReport}
              className="flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" /> Download Summary PDF
            </Button>
          </div>
        </div>
      </div>

      {/* Official Government Verification Certificate Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-950 to-slate-900 text-white rounded-xl p-6 shadow-md space-y-4">
        <div className="flex items-center justify-between border-b border-blue-800/60 pb-3">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <div>
              <span className="font-bold text-sm tracking-wide uppercase">AICTE Statutory Filing Confirmation</span>
              <p className="text-[11px] text-blue-200">Ministry of Education, Government of India</p>
            </div>
          </div>
          <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 rounded-full font-medium">
            Legally Binding Declaration
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-1">
          <div>
            <span className="text-blue-300 block text-[11px]">Institution</span>
            <span className="font-semibold text-white text-sm">{instName}</span>
            <span className="font-mono text-blue-200 block text-[11px]">AICTE ID: {aicteId}</span>
          </div>
          <div>
            <span className="text-blue-300 block text-[11px]">Formal Receipt Token</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-mono font-bold text-white tracking-wider">{receiptNo}</span>
              <button
                onClick={copyReceiptToken}
                title="Copy Receipt Token"
                className="p-1 hover:bg-blue-800/60 rounded text-blue-300 hover:text-white"
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
              {copiedToken && <span className="text-[10px] text-emerald-300">Copied!</span>}
            </div>
            <span className="text-blue-300 text-[11px] block mt-1">Filing Timestamp: {new Date(submittedAt).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Intake & Quota Summary Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs border-b border-slate-100 pb-2">
            <User className="w-4 h-4 text-blue-600" />
            <span>Admitted Student Enrolment</span>
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-500">Total Admitted:</span>
              <span className="font-bold text-slate-900">{totalStudents}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Regular Intake Seats:</span>
              <span className="font-medium text-slate-900">{regularStudents}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Supernumerary Quotas:</span>
              <span className="font-medium text-slate-900">{supernumeraryStudents}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs border-b border-slate-100 pb-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            <span>Approved Courses</span>
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-500">Academic Year:</span>
              <span className="font-bold text-slate-900">{academicYear}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Locking Status:</span>
              <span className="text-emerald-700 font-bold flex items-center gap-1">
                <Lock className="w-3 h-3" /> Locked
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs border-b border-slate-100 pb-2">
            <FileCheck2 className="w-4 h-4 text-blue-600" />
            <span>Statutory Declaration</span>
          </div>
          <p className="text-[11px] text-slate-600 italic bg-slate-50 p-2.5 rounded border border-slate-200">
            "{receipt?.declaration_text || "I confirm this data is correct and complete as authorized by the head of the institution."}"
          </p>
        </div>
      </div>
    </div>
  );
}
