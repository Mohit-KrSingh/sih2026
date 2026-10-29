import { useEffect, useState } from "react";
import { getAuditLogs, verifyAuditChain } from "../api/audit";
import type {
  AuditChainVerificationResponse,
  AuditLogItem,
} from "../types/audit";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  Eye,
  Filter,
  Fingerprint,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";

export function AicteAuditPage() {
  useDocumentTitle("Cryptographic Audit Chain");
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<AuditChainVerificationResponse | null>(null);
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);

  // Filters
  const [actionFilter, setActionFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [page, setPage] = useState(0);
  const limit = 25;

  // Selected row for inspection modal
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const res = await getAuditLogs({
        action: actionFilter || undefined,
        actor_role: roleFilter || undefined,
        entity: entityFilter || undefined,
        limit,
        offset: page * limit,
      });
      setLogs(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actionFilter, roleFilter, entityFilter, page]);

  async function handleVerifyChain() {
    setVerifying(true);
    try {
      const result = await verifyAuditChain();
      setVerificationResult(result);
    } catch (err) {
      console.error("Failed to verify audit hash chain:", err);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1.5">
              <Fingerprint className="w-3.5 h-3.5" />
              Cryptographic Integrity
            </span>
            <span className="text-xs text-slate-500 font-medium">&bull; Spec Section 15 Audit Trail</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Hash-Chained Audit Trail & Tamper Verification
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Append-only ledger cryptographically chained with SHA-256 hashes linking all state mutations
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            size="sm"
            className="bg-indigo-900 hover:bg-indigo-950 text-white text-xs font-semibold"
            isLoading={verifying}
            leftIcon={<ShieldCheck className="w-4 h-4" />}
            onClick={handleVerifyChain}
          >
            Verify chain integrity
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={loadData}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm ${
            verificationResult.verified
              ? "bg-emerald-50/80 border-emerald-300 text-emerald-950"
              : "bg-rose-50/80 border-rose-300 text-rose-950"
          }`}
        >
          <div className="flex items-start gap-3">
            {verificationResult.verified ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div>
              <h4 className="font-bold text-sm">
                {verificationResult.verified
                  ? "Cryptographic SHA-256 Hash Chain Verified Intact"
                  : "Tamper detected in state ledger"}
              </h4>
              <p className="text-xs mt-0.5 text-slate-600">
                {verificationResult.verified
                  ? `All ${verificationResult.total_records} state transitions verified unbroken. Every block's previous hash perfectly links to the canonical record preceding it.`
                  : `Discrepancy detected at Record ID #${verificationResult.first_broken_id}. Reason: ${verificationResult.reason}`}
              </p>
            </div>
          </div>

          <div className="shrink-0 text-right text-xs">
            <span
              className={`px-3 py-1 rounded-full font-bold uppercase tracking-wider text-[11px] ${
                verificationResult.verified
                  ? "bg-emerald-600 text-white"
                  : "bg-rose-600 text-white"
              }`}
            >
              {verificationResult.verified ? "Verified 100%" : "Broken Chain"}
            </span>
          </div>
        </div>
      )}

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Total Logged State Changes</p>
          <p className="text-2xl font-bold text-slate-900">{total.toLocaleString()}</p>
          <p className="text-[11px] text-slate-400">Append-only PostgreSQL table</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Hash Algorithm</p>
          <p className="text-lg font-bold text-slate-800">SHA-256 (Canonical)</p>
          <p className="text-[11px] text-slate-400">hash = SHA256(prev_hash + canonical_row)</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Privacy Safeguards</p>
          <p className="text-lg font-bold text-emerald-700">DPDP Redacted</p>
          <p className="text-[11px] text-slate-400">Recursive APAAR ID masking</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-500 font-medium">Filter by:</span>

          <input
            type="text"
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(0);
            }}
            placeholder="Action (e.g. auth.login, submit)"
            aria-label="Filter by action"
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs focus:outline-none w-48"
          />

          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(0);
            }}
            aria-label="Filter by actor role"
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 focus:outline-none"
          >
            <option value="">All Roles</option>
            <option value="aicte_admin">aicte_admin</option>
            <option value="aicte_officer">aicte_officer</option>
            <option value="college_admin">college_admin</option>
            <option value="college_staff">college_staff</option>
            <option value="verifier">verifier</option>
          </select>

          <input
            type="text"
            value={entityFilter}
            onChange={(e) => {
              setEntityFilter(e.target.value);
              setPage(0);
            }}
            placeholder="Entity (e.g. user, student)"
            aria-label="Filter by entity"
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs focus:outline-none w-40"
          />
        </div>

        <div className="text-xs text-slate-500">
          Showing {logs.length} of {total} records
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <LoadingSpinner size="md" />
            <p className="text-xs text-slate-500">Querying cryptographic audit records...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <Database className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-700">No audit records match filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Action Event</th>
                  <th className="py-3 px-4">Entity</th>
                  <th className="py-3 px-4">Entity ID</th>
                  <th className="py-3 px-4 font-mono">SHA-256 Hash</th>
                  <th className="py-3 px-4 text-right">Payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-sans text-slate-500 text-[11px] whitespace-nowrap">
                      {new Date(log.ts).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <div className="font-medium text-slate-800">
                        {log.actor_id ? `User #${log.actor_id}` : "System"}
                      </div>
                      {log.actor_role && (
                        <span className="text-[10px] text-slate-400 font-mono">
                          {log.actor_role}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <span className="font-bold text-indigo-700">{log.action}</span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-600 capitalize">
                      {log.entity}
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      {log.entity_id || "-"}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[10px]">
                      <span title={log.hash}>
                        {log.hash?.substring(0, 10)}...{log.hash?.substring(log.hash.length - 8)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-xs h-7 px-2 text-indigo-700 hover:bg-indigo-50"
                        leftIcon={<Eye className="w-3.5 h-3.5" />}
                        onClick={() => setSelectedLog(log)}
                      >
                        Inspect
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Strip */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <span>
            Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page === 0}
              aria-label="Go to previous page"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={(page + 1) * limit >= total}
              aria-label="Go to next page"
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </div>

      {/* Inspect Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Fingerprint className="w-4 h-4 text-indigo-700" />
                  Audit record #{selectedLog.id} detail
                </h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Action: {selectedLog.action} &bull; Entity: {selectedLog.entity} (#{selectedLog.entity_id})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                aria-label="Close dialog"
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs overflow-y-auto max-h-[70vh]">
              {/* Hashes */}
              <div className="p-3 rounded-lg bg-slate-900 text-white font-mono space-y-2 text-[11px]">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">SHA-256 Current Hash</span>
                  <span className="text-emerald-400 break-all">{selectedLog.hash}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Previous Hash Link</span>
                  <span className="text-slate-300 break-all">{selectedLog.prev_hash || "GENESIS_BLOCK"}</span>
                </div>
              </div>

              {/* Actor & Network */}
              <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div>
                  <span className="text-slate-400 block text-[10px]">Actor ID & Role</span>
                  <strong className="text-slate-800">
                    {selectedLog.actor_id || "System"} ({selectedLog.actor_role || "none"})
                  </strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Client IP Address</span>
                  <strong className="text-slate-800 font-mono">{selectedLog.ip || "127.0.0.1"}</strong>
                </div>
              </div>

              {/* Before & After JSON */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="font-semibold text-slate-700 block">Before State</span>
                  <pre className="p-3 rounded-lg bg-slate-50 border border-slate-200 font-mono text-[11px] overflow-x-auto max-h-48 text-slate-700">
                    {selectedLog.before_json
                      ? JSON.stringify(selectedLog.before_json, null, 2)
                      : "<null>"}
                  </pre>
                </div>

                <div className="space-y-1">
                  <span className="font-semibold text-slate-700 block">After State</span>
                  <pre className="p-3 rounded-lg bg-slate-50 border border-slate-200 font-mono text-[11px] overflow-x-auto max-h-48 text-slate-700">
                    {selectedLog.after_json
                      ? JSON.stringify(selectedLog.after_json, null, 2)
                      : "<null>"}
                  </pre>
                </div>
              </div>
            </div>

            <div className="p-3 bg-slate-50 border-t border-slate-100 flex justify-end">
              <Button size="sm" variant="outline" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
