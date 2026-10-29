import { useState } from "react";
import { Button } from "../ui/Button";
import { resolveFlag } from "../../api/analytics";
import { AlertCircle, CheckCircle2, ShieldCheck, X } from "lucide-react";

interface ResolveFlagModalProps {
  isOpen: boolean;
  onClose: () => void;
  flagId: number;
  ruleCode: string;
  flagMessage: string;
  studentName?: string;
  apaarId?: string;
  onSuccess?: () => void;
}

export function ResolveFlagModal({
  isOpen,
  onClose,
  flagId,
  ruleCode,
  flagMessage,
  studentName,
  apaarId,
  onSuccess,
}: ResolveFlagModalProps) {
  const [action, setAction] = useState<"resolve" | "dismiss">("resolve");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await resolveFlag({
        flag_id: flagId,
        action,
        note,
      });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
        if (onSuccess) onSuccess();
      }, 1500);
    } catch (err: any) {
      setError(err?.message || "Failed to resolve flag. Please check permissions.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Administrative flag resolution
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Flag ID: <span className="font-mono">#{flagId}</span> &bull; Rule: <span className="font-mono font-medium">{ruleCode}</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto animate-bounce" />
            <h4 className="font-bold text-slate-900 text-lg">Flag status updated</h4>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              Flag has been {action === "resolve" ? "resolved" : "dismissed"}. The student status has been updated in the central registry.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
              {studentName && (
                <p className="text-slate-700">
                  <span className="font-semibold text-slate-500">Student:</span> {studentName} {apaarId && <span className="font-mono">({apaarId})</span>}
                </p>
              )}
              <p className="text-slate-700">
                <span className="font-semibold text-slate-500">Flag Detail:</span> {flagMessage}
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Resolution Action
              </label>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => setAction("resolve")}
                  className={`py-2 px-3 rounded-lg border text-center font-medium transition ${
                    action === "resolve"
                      ? "border-emerald-600 bg-emerald-50 text-emerald-700 font-semibold"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Mark Resolved (Compliant)
                </button>
                <button
                  type="button"
                  onClick={() => setAction("dismiss")}
                  className={`py-2 px-3 rounded-lg border text-center font-medium transition ${
                    action === "dismiss"
                      ? "border-slate-700 bg-slate-100 text-slate-900 font-semibold"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Dismiss Flag (Officer Discretion)
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Officer Resolution Note <span className="text-rose-600">*</span>
              </label>
              <textarea
                required
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="State reason for resolution or administrative sign-off..."
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                This note will be recorded in the cryptographic audit log and visible in the college review thread.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                className="bg-emerald-700 hover:bg-emerald-800 text-white"
                isLoading={loading}
              >
                Confirm resolution
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
