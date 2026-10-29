import { useEffect, useState } from "react";
import { getAnomalies } from "../api/analytics";
import type { AnomalyScoreItem } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  Brain,
  Calendar,
  Cpu,
  RefreshCw,
  Search,
  Send,
  Shield,
  Sparkles,
} from "lucide-react";

export function AicteAnomaliesPage() {
  useDocumentTitle("AICTE Statistical Anomaly Detection");
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [flaggedOnly, setFlaggedOnly] = useState(true);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [anomalies, setAnomalies] = useState<AnomalyScoreItem[]>([]);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const [selectedNoticeCollege, setSelectedNoticeCollege] = useState<{
    id: number;
    name: string;
    aicteId: string;
    summary: string;
  } | null>(null);

  async function loadData(scanNow = false) {
    if (scanNow) setScanning(true);
    else setLoading(true);

    try {
      const res = await getAnomalies({
        academic_year: academicYear,
        flagged_only: flaggedOnly,
        scan_now: scanNow,
      });
      setAnomalies(res.items || []);
      if (scanNow) {
        setScanMessage(`IsolationForest scan completed: ${res.flagged_count} statistical anomalies identified.`);
        setTimeout(() => setScanMessage(null), 4000);
      }
    } catch (err) {
      console.error("Failed to load ML anomaly detection scores:", err);
    } finally {
      setLoading(false);
      setScanning(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [academicYear, flaggedOnly]);

  const filteredItems = anomalies.filter((item) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (item.institution_name && item.institution_name.toLowerCase().includes(q)) ||
      (item.aicte_id && item.aicte_id.toLowerCase().includes(q)) ||
      (item.course_name && item.course_name.toLowerCase().includes(q)) ||
      (item.summary && item.summary.toLowerCase().includes(q))
    );
  });

  const totalFlagged = anomalies.filter((a) => a.flagged).length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-0.5 rounded-full border border-purple-200 flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5" />
              Machine Learning Oversight
            </span>
            <span className="text-xs text-slate-500 font-medium">
              &bull; IsolationForest & Statistical Anomaly Rules
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Intelligent Anomaly Detection & Pattern Recognition
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Unsupervised machine learning identifying irregular cohort admissions, sequential APAAR IDs, and quota spikes
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26</option>
            </select>
          </div>

          <Button
            size="sm"
            className="bg-purple-900 hover:bg-purple-950 text-white text-xs"
            isLoading={scanning}
            leftIcon={<Cpu className="w-3.5 h-3.5" />}
            onClick={() => loadData(true)}
          >
            Scan now (ML)
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => loadData(false)}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {scanMessage && (
        <div className="p-3.5 rounded-xl bg-purple-50 border border-purple-200 text-purple-900 text-xs flex items-center gap-2 animate-in fade-in duration-200">
          <Sparkles className="w-4 h-4 text-purple-600 shrink-0" />
          <span className="font-medium">{scanMessage}</span>
        </div>
      )}

      {/* Model Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Evaluated Cohorts</p>
          <p className="text-2xl font-bold text-slate-900">{anomalies.length}</p>
          <p className="text-[11px] text-slate-500">Course-institution streams</p>
        </div>

        <div className="p-4 bg-white border border-purple-200 bg-purple-50/20 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-purple-700 font-semibold">Flagged Anomalies</p>
          <p className="text-2xl font-bold text-purple-700">{totalFlagged}</p>
          <p className="text-[11px] text-purple-600 font-medium">Contamination threshold &gt; 0.08</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Algorithm</p>
          <p className="text-lg font-bold text-slate-800">IsolationForest</p>
          <p className="text-[11px] text-slate-400">100 estimators, 6D standardized</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-xs text-slate-500">Regulatory Impact</p>
          <p className="text-lg font-bold text-emerald-700">Non-Blocking</p>
          <p className="text-[11px] text-slate-400">Audience: AICTE supervisory only</p>
        </div>
      </div>

      {/* Search & Flagged Filter */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by college, AICTE ID, or anomaly insight..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 select-none">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => setFlaggedOnly(e.target.checked)}
              className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-slate-300 cursor-pointer"
            >
            </input>
            <span>Show Flagged Anomalies Only</span>
          </label>
        </div>
      </div>

      {/* Anomaly Alerts List */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <LoadingSpinner size="md" />
            <p className="text-xs text-slate-500">Evaluating 6-dimensional institutional cohorts with scikit-learn...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <Shield className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
            <p className="font-bold text-slate-800 text-sm">No Statistical Anomalies Detected</p>
            <p className="text-slate-500 mt-1">
              All institutional cohorts conform to normative growth and distribution patterns.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredItems.map((item) => {
              const feat = item.features || {};
              const isNegative = item.score < 0;

              return (
                <div key={item.id} className="p-5 hover:bg-slate-50/50 transition space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-slate-900 text-sm">
                          {item.institution_name || `Institution #${item.institution_id}`}
                        </h4>
                        <span className="font-mono text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                          {item.aicte_id || "-"}
                        </span>
                        <span className="text-xs font-medium text-slate-600">
                          &bull; {item.course_name || `Course #${item.course_id}`}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Academic Year: <strong>{item.academic_year}</strong> &bull; IsolationForest Score:{" "}
                        <strong className={isNegative ? "text-purple-700 font-bold" : "text-slate-700"}>
                          {item.score?.toFixed(4)}
                        </strong>
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                          item.flagged
                            ? "bg-purple-100 text-purple-900 border border-purple-300"
                            : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {item.flagged ? "Flagged Anomaly" : "Normal Baseline"}
                      </span>

                      {item.institution_id && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs text-purple-900 hover:bg-purple-50 border-purple-200"
                          leftIcon={<Send className="w-3.5 h-3.5" />}
                          onClick={() =>
                            setSelectedNoticeCollege({
                              id: item.institution_id,
                              name: item.institution_name || "Institution",
                              aicteId: item.aicte_id || "",
                              summary: item.summary || "Unusual cohort deviation detected",
                            })
                          }
                        >
                          Clarification notice
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Plain-English Explanation Card */}
                  {item.summary && (
                    <div className="p-3 rounded-lg bg-purple-50/60 border border-purple-200 text-xs text-purple-950 flex items-start gap-2">
                      <Sparkles className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Automated Anomaly Insight:</span> {item.summary}
                      </div>
                    </div>
                  )}

                  {/* 6D Feature Badges */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-[11px] pt-1">
                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">YoY Growth</span>
                      <strong className="text-slate-800">
                        {feat.yoy_growth !== undefined ? `${(feat.yoy_growth * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">NRI/FN Share</span>
                      <strong className="text-slate-800">
                        {feat.nri_share !== undefined ? `${(feat.nri_share * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">Supernum. Share</span>
                      <strong className="text-slate-800">
                        {feat.supernum_share !== undefined ? `${(feat.supernum_share * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">DOB Cluster Ratio</span>
                      <strong className="text-slate-800">
                        {feat.dob_cluster_ratio !== undefined ? `${(feat.dob_cluster_ratio * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">Admit Day Conc.</span>
                      <strong className="text-slate-800">
                        {feat.admission_day_concentration !== undefined
                          ? `${(feat.admission_day_concentration * 100).toFixed(1)}%`
                          : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-400 block text-[10px]">Max Sequential APAAR</span>
                      <strong className="text-slate-800">
                        {feat.max_apaar_sequence_run !== undefined ? `${feat.max_apaar_sequence_run} IDs` : "-"}
                      </strong>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Notice Action Modal */}
      {selectedNoticeCollege && (
        <NoticeModal
          isOpen={true}
          onClose={() => setSelectedNoticeCollege(null)}
          institutionId={selectedNoticeCollege.id}
          institutionName={selectedNoticeCollege.name}
          aicteId={selectedNoticeCollege.aicteId}
          defaultSubject={`Inquiry Regarding Statistical Admission Anomaly`}
          defaultMessage={`National AICTE surveillance algorithms have identified a statistical anomaly in your admissions: ${selectedNoticeCollege.summary}. Please provide administrative clarification regarding this pattern.`}
          onSuccess={() => loadData(false)}
        />
      )}
    </div>
  );
}
