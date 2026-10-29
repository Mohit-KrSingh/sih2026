import { useState } from "react";
import { Button } from "../ui/Button";
import { sendNotice } from "../../api/analytics";
import { AlertCircle, CheckCircle2, Send, X } from "lucide-react";

interface NoticeModalProps {
  isOpen: boolean;
  onClose: () => void;
  institutionId: number;
  institutionName: string;
  aicteId: string;
  defaultSubject?: string;
  defaultMessage?: string;
  onSuccess?: () => void;
}

export function NoticeModal({
  isOpen,
  onClose,
  institutionId,
  institutionName,
  aicteId,
  defaultSubject = "",
  defaultMessage = "",
  onSuccess,
}: NoticeModalProps) {
  const [subject, setSubject] = useState(defaultSubject || `AICTE Compliance Notice: ${aicteId}`);
  const [message, setMessage] = useState(defaultMessage);
  const [urgency, setUrgency] = useState<"normal" | "warning" | "urgent">("warning");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await sendNotice({
        institution_id: institutionId,
        subject,
        message,
        urgency,
      });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
        if (onSuccess) onSuccess();
      }, 1500);
    } catch (err: any) {
      setError(err?.message || "Failed to dispatch official notice. Please try again.");
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
              <Send className="w-4 h-4 text-indigo-700" />
              Dispatch Official Notice
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {institutionName} (<span className="font-mono">{aicteId}</span>)
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
            <h4 className="font-bold text-slate-900 text-lg">Notice dispatched</h4>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              The compliance notice has been recorded in the central audit log and delivered to the institution's dashboard.
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

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Notice Subject
              </label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Action Required: Intake Limit Exceeded"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Notice Urgency Level
              </label>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <button
                  type="button"
                  aria-label="Select informational urgency"
                  onClick={() => setUrgency("normal")}
                  className={`py-2 px-3 rounded-lg border text-center font-medium transition ${
                    urgency === "normal"
                      ? "border-blue-600 bg-blue-50 text-blue-700 font-semibold"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Informational
                </button>
                <button
                  type="button"
                  aria-label="Select warning urgency"
                  onClick={() => setUrgency("warning")}
                  className={`py-2 px-3 rounded-lg border text-center font-medium transition ${
                    urgency === "warning"
                      ? "border-amber-600 bg-amber-50 text-amber-700 font-semibold"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Warning
                </button>
                <button
                  type="button"
                  aria-label="Select statutory urgent level"
                  onClick={() => setUrgency("urgent")}
                  className={`py-2 px-3 rounded-lg border text-center font-medium transition ${
                    urgency === "urgent"
                      ? "border-rose-600 bg-rose-50 text-rose-700 font-semibold"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Statutory Urgent
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Official Directive / Inquiry Message
              </label>
              <textarea
                required
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Specify regulatory directive, discrepancies observed, and required response timeline..."
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                This notice will be stored permanently in the AICTE audit ledger and broadcasted to the institution administrator.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                className="bg-indigo-900 hover:bg-indigo-950 text-white"
                isLoading={loading}
              >
                Send official notice
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
