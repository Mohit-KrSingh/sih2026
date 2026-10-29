import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  listApiKeys,
  createApiKey,
  rotateApiKey,
  revokeApiKey,
  type ApiKeyItem,
} from "../api/apiKeys";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
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
  Key,
  Plus,
  RefreshCw,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
  Code2,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";

export const ApiKeyManagementPage: React.FC = () => {
  useDocumentTitle("Integration API Keys");
  const { user } = useAuth();
  const institutionId = user?.institution_id;

  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    "students:write",
    "students:read",
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Secret display modal state (shown once upon creation or rotation)
  const [generatedKey, setGeneratedKey] = useState<{
    rawKey: string;
    name: string;
    action: "created" | "rotated";
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // Confirmation modal states
  const [rotatingKeyId, setRotatingKeyId] = useState<number | null>(null);
  const [revokingKeyId, setRevokingKeyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    if (!institutionId) {
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const res = await listApiKeys(institutionId);
      setKeys(res.items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load API keys";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [institutionId]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleToggleScope = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institutionId || !newKeyName.trim() || selectedScopes.length === 0) return;

    try {
      setIsSubmitting(true);
      setActionError(null);
      const res = await createApiKey(institutionId, {
        name: newKeyName.trim(),
        scopes: selectedScopes,
      });
      setIsCreateModalOpen(false);
      setNewKeyName("");
      setSelectedScopes(["students:write", "students:read"]);
      setGeneratedKey({
        rawKey: res.raw_key,
        name: res.name,
        action: "created",
      });
      await fetchKeys();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create API key";
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRotateKey = async () => {
    if (!institutionId || rotatingKeyId === null) return;
    try {
      setIsSubmitting(true);
      setActionError(null);
      const res = await rotateApiKey(institutionId, rotatingKeyId);
      setRotatingKeyId(null);
      setGeneratedKey({
        rawKey: res.raw_key,
        name: res.name,
        action: "rotated",
      });
      await fetchKeys();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to rotate API key";
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokeKey = async () => {
    if (!institutionId || revokingKeyId === null) return;
    try {
      setIsSubmitting(true);
      setActionError(null);
      await revokeApiKey(institutionId, revokingKeyId);
      setRevokingKeyId(null);
      await fetchKeys();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to revoke API key";
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!institutionId && !loading) {
    return (
      <div className="p-8">
        <ErrorState
          title="Institution Required"
          message="Your account is not linked to an approved institution."
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Key className="w-6 h-6 text-blue-600" />
            Integration API Keys
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage scoped API credentials for campus ERP, Student Information Systems (SIS), and automated batch uploads.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Code2 className="w-4 h-4 text-gray-500" />
            OpenAPI Docs
            <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
          </a>
          <Button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            Generate New API Key
          </Button>
        </div>
      </div>

      {/* Main Table or Loading/Error */}
      {loading ? (
        <div className="flex justify-center items-center py-16">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <ErrorState
          title="Error Loading API Keys"
          message={error}
          onRetry={fetchKeys}
        />
      ) : keys.length === 0 ? (
        <EmptyState
          icon={<Key className="w-12 h-12 text-gray-400" />}
          title="No API Keys Generated Yet"
          description="Generate an API key to connect your college ERP or student information system directly with AICTE EduTrace."
          actionLabel="Generate First API Key"
          onAction={() => setIsCreateModalOpen(true)}
        />
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900">Configured API Credentials</h2>
            <span className="text-xs text-gray-500 font-medium">
              {keys.filter((k) => k.is_active).length} Active Keys ({keys.length} Total)
            </span>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key Name</TableHead>
                  <TableHead>Prefix Preview</TableHead>
                  <TableHead>Granted Scopes</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((k) => (
                  <TableRow key={k.id} className={!k.is_active ? "bg-gray-50/60 opacity-75" : ""}>
                    <TableCell className="font-medium text-gray-900">
                      <div>
                        <span>{k.name}</span>
                        <span className="ml-2 text-xs text-gray-400 font-mono">#{k.id}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-gray-600">
                      {k.key_prefix}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {k.scopes.map((s) => (
                          <span
                            key={s}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {k.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-600"></span>
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
                          <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                          Revoked
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-gray-500">
                      {formatDate(k.last_used_at)}
                    </TableCell>
                    <TableCell className="text-xs text-gray-500">
                      {formatDate(k.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      {k.is_active ? (
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setRotatingKeyId(k.id)}
                            className="flex items-center gap-1 text-xs"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                            Rotate
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => setRevokingKeyId(k.id)}
                            className="flex items-center gap-1 text-xs"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Revoke
                          </Button>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 italic">No actions available</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Integration Quickstart & OpenAPI Guide */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
          <ShieldCheck className="w-5 h-5 text-blue-600" />
          <h3 className="text-base font-semibold text-gray-900">ERP Integration Quickstart</h3>
        </div>
        <p className="text-sm text-gray-600">
          External systems authenticate using the <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">X-API-Key</code> header or standard <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">Authorization: Bearer &lt;key&gt;</code>. Include an <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">Idempotency-Key</code> header to prevent duplicate submissions during network retries.
        </p>

        <div className="bg-gray-900 text-gray-100 p-4 rounded-md font-mono text-xs overflow-x-auto space-y-2">
          <div className="text-gray-400"># Sample bulk student push request via curl</div>
          <div>
            <span className="text-emerald-400">curl</span> -X POST http://127.0.0.1:8000/api/v1/integration/students/bulk \
          </div>
          <div className="pl-4">
            -H <span className="text-amber-300">"X-API-Key: apaar_live_YOUR_KEY"</span> \
          </div>
          <div className="pl-4">
            -H <span className="text-amber-300">"Idempotency-Key: ERP-BATCH-2026-001"</span> \
          </div>
          <div className="pl-4">
            -H <span className="text-amber-300">"Content-Type: application/json"</span> \
          </div>
          <div className="pl-4">
            -d <span className="text-amber-300">'{JSON.stringify({ academic_year: "2026-27", students: [{ apaar_id: "900012345678", name: "Rahul Sharma", dob: "2004-05-15", gender: "Male", course: "Computer Science and Engineering", enrolment_no: "ENR-001", admission_date: "2026-07-15" }] })}'</span>
          </div>
        </div>

        <div className="text-xs text-gray-500 flex items-center justify-between pt-2">
          <span>Executable Python ERP reference client available at <code className="text-gray-800 font-mono">demo/erp_client.py</code>.</span>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
          >
            Explore Interactive OpenAPI Spec
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Modal 1: Generate New Key */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Key className="w-5 h-5 text-blue-600" />
              Generate Integration API Key
            </h3>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                {actionError}
              </div>
            )}

            <form onSubmit={handleCreateKey} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Key Name / Client Identifier
                </label>
                <Input
                  type="text"
                  placeholder="e.g. Campus ERP Production"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  required
                  autoFocus
                />
                <p className="mt-1 text-xs text-gray-500">
                  Descriptive label to identify which external system uses this credential.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Allowed Scopes
                </label>
                <div className="space-y-2 border border-gray-200 rounded-md p-3 bg-gray-50">
                  <label className="flex items-start gap-2 cursor-pointer text-sm text-gray-800">
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes("students:write")}
                      onChange={() => handleToggleScope("students:write")}
                      className="mt-1 rounded text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-semibold text-gray-900">students:write</span>
                      <p className="text-xs text-gray-500">Push student records in bulk via JSON endpoint</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer text-sm text-gray-800">
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes("students:read")}
                      onChange={() => handleToggleScope("students:read")}
                      className="mt-1 rounded text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-semibold text-gray-900">students:read</span>
                      <p className="text-xs text-gray-500">Query student submission status and validation flags</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer text-sm text-gray-800">
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes("courses:read")}
                      onChange={() => handleToggleScope("courses:read")}
                      className="mt-1 rounded text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-semibold text-gray-900">courses:read</span>
                      <p className="text-xs text-gray-500">Read approved programmes and intake allocations</p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting || !newKeyName.trim() || selectedScopes.length === 0}
                >
                  {isSubmitting ? "Generating..." : "Generate Secret Key"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Generated Secret Key Display (Shown once) */}
      {generatedKey && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-lg w-full p-6 space-y-4 border-2 border-emerald-500">
            <div className="flex items-center gap-2 text-emerald-700">
              <ShieldCheck className="w-6 h-6" />
              <h3 className="text-lg font-bold">
                API Key {generatedKey.action === "created" ? "Created" : "Rotated"} Successfully!
              </h3>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-300 rounded-md text-xs text-amber-900 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong>Important Security Notice:</strong> Make sure to copy this secret key right now.
                For your security, AICTE never stores raw keys in plaintext and you will <strong>never</strong> be able to view it again.
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Secret API Key for <span className="text-blue-700">"{generatedKey.name}"</span>
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={generatedKey.rawKey}
                  className="w-full bg-gray-50 border border-gray-300 font-mono text-xs px-3 py-2 rounded text-gray-900 select-all focus:outline-none"
                />
                <Button
                  type="button"
                  onClick={() => copyToClipboard(generatedKey.rawKey)}
                  className="flex items-center gap-1.5 flex-shrink-0"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-300" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      Copy Key
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-200 flex justify-end">
              <Button
                type="button"
                onClick={() => setGeneratedKey(null)}
              >
                I have saved this key
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal 3: Rotate Confirmation */}
      {rotatingKeyId !== null && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-blue-600" />
              Rotate API Key
            </h3>
            <p className="text-sm text-gray-600">
              Rotating this API key will <strong>immediately invalidate</strong> the current key. Any external ERP systems using this secret will fail authentication until updated with the newly generated secret.
            </p>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                {actionError}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setRotatingKeyId(null)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleRotateKey}
                disabled={isSubmitting}
              >
                {isSubmitting ? "Rotating..." : "Rotate Key Now"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal 4: Revoke Confirmation */}
      {revokingKeyId !== null && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Revoke API Key
            </h3>
            <p className="text-sm text-gray-600">
              Are you sure you want to permanently revoke this API key? This credential will immediately lose access and cannot be reactivated.
            </p>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                {actionError}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setRevokingKeyId(null)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={handleRevokeKey}
                disabled={isSubmitting}
              >
                {isSubmitting ? "Revoking..." : "Revoke Key"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
