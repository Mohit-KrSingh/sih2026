import React, { useEffect, useState } from "react";
import { getAnomalies } from "../api/analytics";
import type { AnomalyScoreItem } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { Button } from "../components/ux4g/Button";
import { FlagBadge } from "../components/ux4g/Badge";
import { Spinner } from "../components/ux4g/Spinner";
import { Icon } from "../components/ux4g/Icon";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

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
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className="text-xs font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border flex items-center gap-1.5"
              style={{
                backgroundColor: "var(--ux4g-color-purple-50)",
                color: "var(--ux4g-color-purple-800)",
                borderColor: "var(--ux4g-color-purple-300)",
              }}
            >
              <Icon name="psychology" size="xs" color="inherit" />
              Machine Learning Oversight
            </span>
            <span className="text-xs ux4g-text-neutral-secondary font-medium">
              &bull; IsolationForest & Statistical Anomaly Rules
            </span>
          </div>
          <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight">
            Intelligent Anomaly Detection & Pattern Recognition
          </h1>
          <p className="text-xs ux4g-text-neutral-secondary mt-1">
            Unsupervised machine learning identifying irregular cohort admissions, sequential APAAR IDs, and quota spikes
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Academic Year Selector */}
          <div className="flex items-center gap-1.5 ux4g-bg-neutral-soft border ux4g-border-neutral-subtle rounded-lg px-2.5 py-1.5 text-xs">
            <Icon name="calendar_month" size="xs" color="inherit" className="ux4g-text-neutral-secondary" />
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold ux4g-text-neutral-primary focus:outline-none cursor-pointer"
              aria-label="Select Academic Year"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26</option>
            </select>
          </div>

          <Button
            size="sm"
            variant="primary"
            onClick={() => loadData(true)}
            disabled={scanning}
            leftIcon={<Icon name="memory" size="xs" color="inherit" />}
          >
            {scanning ? "Evaluating Model..." : "Run ML Model Scan"}
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => loadData(false)}
            leftIcon={<Icon name="refresh" size="xs" color="inherit" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {scanMessage && (
        <div
          className="p-4 rounded-xl border text-xs font-medium flex items-center gap-2"
          style={{
            backgroundColor: "var(--ux4g-color-purple-50)",
            color: "var(--ux4g-color-purple-900)",
            borderColor: "var(--ux4g-color-purple-300)",
          }}
        >
          <Icon name="auto_awesome" size="xs" color="inherit" />
          <span>{scanMessage}</span>
        </div>
      )}

      {/* KPI Overview Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm space-y-1">
          <p className="text-[11px] font-medium ux4g-text-neutral-secondary uppercase tracking-wider">
            Evaluated Cohorts
          </p>
          <p className="text-2xl font-bold ux4g-text-neutral-primary">{anomalies.length}</p>
          <p className="text-[11px] ux4g-text-neutral-secondary">Institution & course pairs</p>
        </div>

        <div
          className="p-4 ux4g-bg-neutral-elevated border rounded-xl shadow-sm space-y-1"
          style={{ borderColor: "var(--ux4g-color-purple-300)" }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--ux4g-color-purple-800)" }}
          >
            Flagged Statistical Anomalies
          </p>
          <p className="text-2xl font-bold" style={{ color: "var(--ux4g-color-purple-700)" }}>
            {totalFlagged}
          </p>
          <p className="text-[11px] font-medium" style={{ color: "var(--ux4g-color-purple-700)" }}>
            IsolationForest score &lt; -0.05
          </p>
        </div>

        <div className="p-4 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm space-y-1">
          <p className="text-[11px] font-medium ux4g-text-neutral-secondary uppercase tracking-wider">
            Evaluated Feature Dimensions
          </p>
          <p className="text-2xl font-bold ux4g-text-brand-primary">6-Dimensional</p>
          <p className="text-[11px] ux4g-text-neutral-secondary">
            YoY Growth, NRI %, Supernum %, DOB Clusters, Admit Day %, Sequential APAAR
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full md:w-80">
          <Icon name="search" size="xs" color="inherit" className="ux4g-text-neutral-secondary absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by college, AICTE ID, course, or insight..."
            className="w-full pl-9 pr-3 py-2 text-xs border ux4g-border-neutral-subtle rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ux4g-bg-neutral-elevated ux4g-text-neutral-primary"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <label className="flex items-center gap-2 cursor-pointer font-medium ux4g-text-neutral-primary">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => setFlaggedOnly(e.target.checked)}
              className="rounded border ux4g-border-neutral-subtle text-primary focus:ring-primary"
            />
            <span>Show Only Flagged Anomalies ({totalFlagged})</span>
          </label>
        </div>
      </div>

      {/* Anomalies List */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm p-4">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <Spinner size="m" />
            <p className="text-xs ux4g-text-neutral-secondary">Computing multidimensional anomaly vectors...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="py-16 text-center ux4g-text-neutral-secondary text-xs">
            <Icon name="verified_user" size="l" color="success" className="mx-auto mb-2" />
            <p className="font-bold ux4g-text-neutral-primary text-sm">No Statistical Anomalies Detected</p>
            <p className="ux4g-text-neutral-secondary mt-1">
              All student cohorts conform to standard baseline admission distributions.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredItems.map((item, idx) => {
              const feat = item.features || {};
              const isNegative = (item.score || 0) < 0;

              return (
                <div
                  key={`${item.institution_id}-${item.course_id}-${idx}`}
                  className="p-4 rounded-xl border transition space-y-3"
                  style={{
                    backgroundColor: item.flagged ? "var(--ux4g-color-purple-50)" : "var(--ux4g-bg-neutral-soft)",
                    borderColor: item.flagged ? "var(--ux4g-color-purple-300)" : "var(--ux4g-border-neutral-subtle)",
                  }}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b ux4g-border-neutral-subtle pb-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-bold ux4g-text-neutral-primary text-sm">
                          {item.institution_name || `Institution #${item.institution_id}`}
                        </h4>
                        <span className="font-mono text-xs ux4g-bg-neutral-elevated ux4g-text-neutral-primary px-2 py-0.5 rounded border ux4g-border-neutral-subtle">
                          {item.aicte_id || "-"}
                        </span>
                        <span className="text-xs font-medium ux4g-text-neutral-secondary">
                          &bull; {item.course_name || `Course #${item.course_id}`}
                        </span>
                      </div>
                      <p className="text-xs ux4g-text-neutral-secondary mt-0.5">
                        Academic Year: <strong>{item.academic_year}</strong> &bull; IsolationForest Score:{" "}
                        <strong
                          style={{
                            color: isNegative
                              ? "var(--ux4g-color-purple-700)"
                              : "var(--ux4g-text-neutral-primary)",
                          }}
                        >
                          {item.score?.toFixed(4)}
                        </strong>
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Anomaly cards use unified FlagBadge */}
                      <FlagBadge
                        level={item.flagged ? "warning" : "info"}
                        label={item.flagged ? "Flagged Anomaly" : "Normal Baseline"}
                      />

                      {item.institution_id && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs"
                          leftIcon={<Icon name="send" size="xs" color="inherit" />}
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
                    <div
                      className="p-3 rounded-lg border text-xs flex items-start gap-2"
                      style={{
                        backgroundColor: "var(--ux4g-bg-neutral-elevated)",
                        borderColor: "var(--ux4g-color-purple-200)",
                        color: "var(--ux4g-color-purple-950)",
                      }}
                    >
                      <Icon name="auto_awesome" size="xs" color="inherit" className="shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Automated Anomaly Insight:</span> {item.summary}
                      </div>
                    </div>
                  )}

                  {/* 6D Feature Badges */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-[11px] pt-1">
                    <div className="p-2 rounded ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle">
                      <span className="ux4g-text-neutral-secondary block text-[10px]">YoY Growth</span>
                      <strong className="ux4g-text-neutral-primary">
                        {feat.yoy_growth !== undefined ? `${(feat.yoy_growth * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle">
                      <span className="ux4g-text-neutral-secondary block text-[10px]">NRI/FN Share</span>
                      <strong className="ux4g-text-neutral-primary">
                        {feat.nri_share !== undefined ? `${(feat.nri_share * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle">
                      <span className="ux4g-text-neutral-secondary block text-[10px]">Supernum. Share</span>
                      <strong className="ux4g-text-neutral-primary">
                        {feat.supernum_share !== undefined ? `${(feat.supernum_share * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle">
                      <span className="ux4g-text-neutral-secondary block text-[10px]">DOB Cluster Ratio</span>
                      <strong className="ux4g-text-neutral-primary">
                        {feat.dob_cluster_ratio !== undefined ? `${(feat.dob_cluster_ratio * 100).toFixed(1)}%` : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle">
                      <span className="ux4g-text-neutral-secondary block text-[10px]">Admit Day Conc.</span>
                      <strong className="ux4g-text-neutral-primary">
                        {feat.admission_day_concentration !== undefined
                          ? `${(feat.admission_day_concentration * 100).toFixed(1)}%`
                          : "-"}
                      </strong>
                    </div>

                    <div className="p-2 rounded ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle">
                      <span className="ux4g-text-neutral-secondary block text-[10px]">Max Sequential APAAR</span>
                      <strong className="ux4g-text-neutral-primary">
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
