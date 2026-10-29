import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { getRules, resetRuleConfig, updateRuleConfig } from "../api/rules";
import type { RuleConfigItem } from "../types/rules";
import { FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertCircle,
  CheckCircle2,
  Filter,
  Lock,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Sliders,
  X,
} from "lucide-react";

export function AicteRulesPage() {
  useDocumentTitle("Validation Rules Configuration");
  const { user } = useAuth();
  const isAdmin = user?.role === "aicte_admin";

  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState<RuleConfigItem[]>([]);
  const [scopeFilter, setScopeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [editingRule, setEditingRule] = useState<RuleConfigItem | null>(null);

  // Form state
  const [editLevel, setEditLevel] = useState<string>("error");
  const [editEnabled, setEditEnabled] = useState<boolean>(true);
  const [editParamsJson, setEditParamsJson] = useState<string>("{}");
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const res = await getRules();
      setRules(res.items || []);
    } catch (err) {
      console.error("Failed to load validation rules:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function startEditing(rule: RuleConfigItem) {
    if (!isAdmin) return;
    setEditingRule(rule);
    setEditLevel(rule.current_level);
    setEditEnabled(rule.enabled);
    setEditParamsJson(JSON.stringify(rule.current_params || {}, null, 2));
    setFeedback(null);
  }

  async function handleSaveOverride(e: React.FormEvent) {
    e.preventDefault();
    if (!editingRule) return;

    let parsedParams = {};
    try {
      parsedParams = JSON.parse(editParamsJson);
    } catch {
      setFeedback({ type: "error", message: "Invalid JSON format in parameters editor" });
      return;
    }

    setSaving(true);
    setFeedback(null);
    try {
      const updated = await updateRuleConfig(editingRule.rule_code, {
        level: editLevel as any,
        enabled: editEnabled,
        params: parsedParams,
      });

      setRules((prev) =>
        prev.map((r) => (r.rule_code === updated.rule_code ? updated : r))
      );
      setFeedback({ type: "success", message: `Policy override saved for ${editingRule.rule_code}.` });
      setTimeout(() => {
        setEditingRule(null);
        setFeedback(null);
      }, 1200);
    } catch (err: any) {
      setFeedback({ type: "error", message: err?.message || "Failed to update rule configuration." });
    } finally {
      setSaving(false);
    }
  }

  async function handleResetRule(ruleCode: string) {
    if (!isAdmin) return;
    setSaving(true);
    try {
      const reset = await resetRuleConfig(ruleCode);
      setRules((prev) =>
        prev.map((r) => (r.rule_code === reset.rule_code ? reset : r))
      );
      if (editingRule?.rule_code === ruleCode) {
        setEditingRule(null);
      }
    } catch (err) {
      console.error("Failed to reset rule:", err);
    } finally {
      setSaving(false);
    }
  }

  const filteredRules = rules.filter((r) => {
    if (scopeFilter && r.scope !== scopeFilter) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      r.rule_code.toLowerCase().includes(q) ||
      r.meaning.toLowerCase().includes(q) ||
      r.scope.toLowerCase().includes(q)
    );
  });

  const overriddenCount = rules.filter((r) => r.is_overridden).length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5" />
              Policy & Validation Control
            </span>
            <span className="text-xs text-slate-500 font-medium">&bull; Spec Section 9.2 & 9.3</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Validation Rules & Policy Customization
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Configure validation severity levels, custom thresholds, and activation status at runtime without code deployment
          </p>
        </div>

        <div className="flex items-center gap-3">
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

      {/* Role Banner */}
      {!isAdmin && (
        <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2">
          <Lock className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>Read-Only Mode:</strong> Logged in as <span className="font-mono">{user?.role}</span>. Validation policy customization requires <span className="font-semibold">aicte_admin</span> administrative privileges.
          </span>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Catalogued Rules</p>
          <p className="text-2xl font-bold text-slate-900">{rules.length}</p>
          <p className="text-[11px] text-slate-400">Total validation checks</p>
        </div>

        <div className="p-4 bg-white border border-indigo-200 bg-indigo-50/20 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-indigo-700 font-semibold">Active Policy Overrides</p>
          <p className="text-2xl font-bold text-indigo-700">{overriddenCount}</p>
          <p className="text-[11px] text-indigo-600 font-medium">Customized in rule_config</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Engine Integration</p>
          <p className="text-2xl font-bold text-emerald-600">Immediate</p>
          <p className="text-[11px] text-slate-400">Single entry, CSV & API</p>
        </div>
      </div>

      {/* Search and Scope Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by rule code or meaning..."
            aria-label="Search rules"
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            aria-label="Filter rules by scope"
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 focus:outline-none"
          >
            <option value="">All Scopes (file, row, course, cross, anomaly)</option>
            <option value="file">File Scope Rules</option>
            <option value="row">Row Scope Rules</option>
            <option value="course">Course Scope Rules</option>
            <option value="cross">Cross-College Scope Rules</option>
            <option value="anomaly">Anomaly Scope Rules</option>
          </select>
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <LoadingSpinner size="md" />
            <p className="text-xs text-slate-500">Loading validation rule registry catalogue...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">Rule Code</th>
                  <th className="py-3 px-4">Scope</th>
                  <th className="py-3 px-4">Default Level</th>
                  <th className="py-3 px-4">Active Level</th>
                  <th className="py-3 px-4">Regulatory Meaning</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRules.map((rule) => {
                  const isModified = rule.is_overridden;
                  return (
                    <tr
                      key={rule.rule_code}
                      className={`hover:bg-slate-50 transition ${
                        isModified ? "bg-indigo-50/20" : ""
                      }`}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {rule.rule_code}
                        {isModified && (
                          <span className="ml-2 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-indigo-100 text-indigo-700">
                            Custom
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-600 border border-slate-200">
                          {rule.scope}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <FlagBadge level={rule.default_level as any} />
                      </td>
                      <td className="py-3 px-4">
                        <FlagBadge level={rule.current_level as any} />
                      </td>
                      <td className="py-3 px-4 text-slate-600 max-w-sm">
                        {rule.meaning}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            rule.enabled
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-slate-100 text-slate-400 border border-slate-200 line-through"
                          }`}
                        >
                          {rule.enabled ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {isModified && isAdmin && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-[11px] h-7 px-2 text-slate-500 hover:text-rose-600"
                              leftIcon={<RotateCcw className="w-3 h-3" />}
                              onClick={() => handleResetRule(rule.rule_code)}
                            >
                              Reset
                            </Button>
                          )}
                          {isAdmin && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-[11px] h-7 px-2.5"
                              onClick={() => startEditing(rule)}
                            >
                              Configure
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rule Edit Modal */}
      {editingRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-indigo-700" />
                  Configure policy: {editingRule.rule_code}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Scope: <span className="font-mono font-semibold uppercase">{editingRule.scope}</span>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditingRule(null)}
                aria-label="Close dialog"
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveOverride} className="p-6 space-y-4 text-xs">
              {feedback && (
                <div
                  className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                    feedback.type === "success"
                      ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
                      : "bg-rose-50 border border-rose-200 text-rose-800"
                  }`}
                >
                  {feedback.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                  )}
                  <span>{feedback.message}</span>
                </div>
              )}

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-600">
                <p>
                  <strong>Catalogue Meaning:</strong> {editingRule.meaning}
                </p>
                <p className="mt-1">
                  <strong>Catalogue Default Level:</strong>{" "}
                  <span className="font-mono uppercase font-bold text-slate-800">
                    {editingRule.default_level}
                  </span>
                </p>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Override Validation Level
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(["error", "exception", "warning", "info"] as const).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      aria-label={`Set severity to ${lvl}`}
                      onClick={() => setEditLevel(lvl)}
                      className={`py-2 px-2 rounded-lg border text-center font-bold capitalize transition ${
                        editLevel === lvl
                          ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                          : "border-slate-200 text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={editEnabled}
                    onChange={(e) => setEditEnabled(e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
                  />
                  <span>Rule Enabled for Automated Engine Execution</span>
                </label>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Custom Parameters (JSON)
                </label>
                <textarea
                  rows={4}
                  value={editParamsJson}
                  onChange={(e) => setEditParamsJson(e.target.value)}
                  className="w-full font-mono text-[11px] p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Example: {JSON.stringify(editingRule.default_params || {})}
                </p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleResetRule(editingRule.rule_code)}
                  leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                  disabled={saving}
                >
                  Reset default
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setEditingRule(null)}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    className="bg-indigo-900 hover:bg-indigo-950 text-white"
                    isLoading={saving}
                    leftIcon={<Save className="w-3.5 h-3.5" />}
                  >
                    Save policy override
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
