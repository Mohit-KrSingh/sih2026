import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import {
  createJustification,
  deleteJustification,
  downloadJustificationDocument,
  getInstitutionFlags,
} from "../api/justifications";
import type { ValidationFlagDetail } from "../types/validation";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { ErrorState } from "../components/ui/ErrorState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Download,
  Edit,
  ExternalLink,
  FileCheck,
  Info,
  Paperclip,
  Trash2,
  User,
} from "lucide-react";

export function FlagDetailPage() {
  const { flagId } = useParams<{ flagId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const institutionId = user?.institution_id ?? 1;

  const [flag, setFlag] = useState<ValidationFlagDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Justification form state
  const [justificationText, setJustificationText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [justificationError, setJustificationError] = useState<string | null>(null);
  const [justificationSuccess, setJustificationSuccess] = useState<string | null>(null);

  useDocumentTitle(flag ? `Flag: ${flag.rule_code}` : "Validation Flag Details");

  const loadFlag = useCallback(async () => {
    if (!flagId) return;
    setIsLoading(true);
    setError(null);
    try {
      const parsedId = parseInt(flagId, 10);
      const res = await getInstitutionFlags(institutionId);
      const found = res.items.find((f) => f.id === parsedId);
      if (found) {
        setFlag(found);
      } else {
        setError("Validation flag not found or belongs to another institution.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load validation flag.");
    } finally {
      setIsLoading(false);
    }
  }, [flagId, institutionId]);

  useEffect(() => {
    loadFlag();
  }, [loadFlag]);

  const handleSubmitJustification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flag) return;
    if (justificationText.trim().length < 5) {
      setJustificationError("Justification must be at least 5 characters long.");
      return;
    }

    setSubmitting(true);
    setJustificationError(null);
    setJustificationSuccess(null);
    try {
      await createJustification(institutionId, flag.id, justificationText.trim(), selectedFile);
      setJustificationSuccess("Official justification submitted successfully.");
      setJustificationText("");
      setSelectedFile(null);
      await loadFlag();
    } catch (err) {
      setJustificationError(err instanceof Error ? err.message : "Failed to submit justification.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteJustification = async (justificationId: number) => {
    if (!confirm("Are you sure you want to withdraw this justification?")) return;
    try {
      await deleteJustification(institutionId, justificationId);
      await loadFlag();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete justification.");
    }
  };

  const handleDownloadDoc = async (justificationId: number) => {
    try {
      const { blob, filename } = await downloadJustificationDocument(institutionId, justificationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `justification_doc_${justificationId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to download attached document.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-slate-600">Loading flag details...</p>
      </div>
    );
  }

  if (error || !flag) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ErrorState
          title="Flag Not Found"
          message={error || "Validation flag could not be loaded."}
          onRetry={() => navigate("/college/validation")}
        />
        <div className="mt-4">
          <Link to="/college/validation" className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1.5">
            <ArrowLeft className="w-4 h-4" /> Back to Validation Flags
          </Link>
        </div>
      </div>
    );
  }

  const isError = flag.level === "error";

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 space-y-6">
      {/* Header Bar */}
      <div className="border-b border-slate-200 pb-4">
        <Link
          to="/college/validation"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition mb-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Validation Flags
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <FlagBadge level={flag.level} />
            <h1 className="text-2xl font-bold font-mono text-slate-900 tracking-tight">{flag.rule_code}</h1>
            <Badge variant={flag.status === "resolved" ? "success" : flag.status === "justified" ? "warning" : "danger"}>
              {flag.status.toUpperCase()}
            </Badge>
          </div>
          <span className="text-xs text-slate-500">Flag ID #{flag.id}</span>
        </div>
      </div>

      {/* Flag Message & Details Box */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Validation Issue</span>
          <p className="text-base font-semibold text-slate-900 mt-1 leading-relaxed">{flag.message}</p>
          {flag.field && (
            <p className="text-xs text-slate-500 mt-1">
              Violating Field: <code className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded font-mono">{flag.field}</code>
            </p>
          )}
        </div>

        {flag.fix_hint && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-900 flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">Regulatory Guidance:</span>
              <span>{flag.fix_hint}</span>
            </div>
          </div>
        )}

        {/* Affected Target Entity Card */}
        <div className="border-t border-slate-100 pt-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">Affected Entity</span>
          {flag.student ? (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-blue-600" />
                  <Link
                    to={`/college/students/${flag.student.id}`}
                    className="font-bold text-sm text-blue-700 hover:text-blue-900 underline flex items-center gap-1"
                  >
                    {flag.student.name} <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
                <div className="text-xs text-slate-600 space-x-3">
                  <span>APAAR: <span className="font-mono font-medium">{flag.student.apaar_id}</span></span>
                  <span>Enrolment: <span className="font-mono">{flag.student.enrolment_no || "N/A"}</span></span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Link to={`/college/students/${flag.student.id}`}>
                  <Button variant="outline" size="sm">
                    View Student Record
                  </Button>
                </Link>
                <Link to={`/college/students/${flag.student.id}/edit`}>
                  <Button variant="primary" size="sm" className="flex items-center gap-1">
                    <Edit className="w-3.5 h-3.5" /> Correct Data
                  </Button>
                </Link>
              </div>
            </div>
          ) : flag.course ? (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <span className="font-bold text-slate-900 block">{flag.course.name}</span>
              <span className="text-xs text-slate-600">
                {flag.course.branch} &bull; {flag.course.level}
              </span>
            </div>
          ) : (
            <p className="text-xs text-slate-600 italic">Institutional quota or policy level check.</p>
          )}
        </div>
      </div>

      {/* Justifications Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <FileCheck className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Regulatory Justifications</h2>
          </div>
          <span className="text-xs text-slate-500">
            {flag.justifications.length} {flag.justifications.length === 1 ? "submission" : "submissions"}
          </span>
        </div>

        {/* Existing Justifications */}
        {flag.justifications.length > 0 ? (
          <div className="space-y-3">
            {flag.justifications.map((just) => (
              <div key={just.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900">Submitted by Institution</span>
                  <span className="text-slate-500">{new Date(just.created_at).toLocaleDateString()}</span>
                </div>
                <p className="text-slate-700 bg-white p-3 rounded border border-slate-200">{just.text}</p>
                <div className="flex items-center justify-between pt-1">
                  {just.document_ref ? (
                    <button
                      onClick={() => handleDownloadDoc(just.id)}
                      className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Evidence ({just.document_ref})
                    </button>
                  ) : (
                    <span className="text-slate-400 italic">No document attached</span>
                  )}
                  {user?.role === "college_admin" && (
                    <button
                      onClick={() => handleDeleteJustification(just.id)}
                      className="text-red-600 hover:text-red-800 inline-flex items-center gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Withdraw
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic">No justifications on record for this flag.</p>
        )}

        {/* Justification Form or Error Policy Warning */}
        {isError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-xs text-red-900 space-y-2">
            <div className="flex items-center gap-2 font-semibold">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>Hard Rule 9.1: Data Errors Cannot Be Justified</span>
            </div>
            <p className="text-red-800 leading-relaxed">
              This flag is classified as an <strong>ERROR</strong>. Errors represent statutory non-compliance or malformed
              records and <em>must be corrected directly in student data</em>. Justifications are only permitted on Exceptions
              and Warnings.
            </p>
            {flag.student && (
              <Link to={`/college/students/${flag.student.id}/edit`}>
                <Button variant="danger" size="sm" className="mt-2">
                  Edit Student Record Now
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmitJustification} className="space-y-4 border-t border-slate-100 pt-4">
            <span className="text-xs font-semibold text-slate-800 block">Submit Official Regulatory Justification</span>

            {justificationError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{justificationError}</span>
              </div>
            )}
            {justificationSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{justificationSuccess}</span>
              </div>
            )}

            <div>
              <textarea
                value={justificationText}
                onChange={(e) => setJustificationText(e.target.value)}
                placeholder="State the regulatory basis, university sanction, or official justification for this exception..."
                rows={3}
                required
                className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition">
                  <Paperclip className="w-3.5 h-3.5" />
                  <span>{selectedFile ? selectedFile.name : "Attach Sanction Copy / Order (PDF)"}</span>
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </label>
                {selectedFile && (
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                )}
              </div>

              <Button type="submit" variant="primary" size="sm" disabled={submitting}>
                {submitting ? "Submitting..." : "Submit Justification"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
