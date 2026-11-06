import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import {
  getComplianceList,
  getCourseMetrics,
  getOverviewMetrics,
  getRecentEvents,
  getStateMetrics,
  subscribeLiveEvents,
} from "../api/analytics";
import type {
  ComplianceViolation,
  CourseMetricsItem,
  OverviewMetrics,
  SSEEventPayload,
  StateMetricsItem,
} from "../types/analytics";
import { StateIntakeChart } from "../charts/StateIntakeChart";
import { SubmissionProgressChart } from "../charts/SubmissionProgressChart";
import { CourseDistributionChart } from "../charts/CourseDistributionChart";
import { NoticeModal } from "../components/action/NoticeModal";
import { Button } from "../components/ux4g/Button";
import { FlagBadge, RoleBadge } from "../components/ux4g/Badge";
import { Spinner } from "../components/ux4g/Spinner";
import { Icon } from "../components/ux4g/Icon";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function AicteOverviewPage() {
  useDocumentTitle("AICTE Central Command Overview");
  const { user } = useAuth();
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [complianceList, setComplianceList] = useState<ComplianceViolation[]>([]);
  const [stateMetrics, setStateMetrics] = useState<StateMetricsItem[]>([]);
  const [courseMetrics, setCourseMetrics] = useState<CourseMetricsItem[]>([]);
  const [liveEvents, setLiveEvents] = useState<SSEEventPayload[]>([]);
  const [sseStatus, setSseStatus] = useState<"live" | "reconnecting">("live");

  const [selectedNoticeCollege, setSelectedNoticeCollege] = useState<{
    id: number;
    name: string;
    aicteId: string;
    overshoot: number;
  } | null>(null);

  // Load analytics data
  async function loadData() {
    setLoading(true);
    try {
      const [ovData, compData, stData, crsData, evData] = await Promise.all([
        getOverviewMetrics(academicYear),
        getComplianceList({ academic_year: academicYear, min_overshoot: 1 }),
        getStateMetrics(academicYear),
        getCourseMetrics(academicYear),
        getRecentEvents({ limit: 12 }),
      ]);
      setOverview(ovData);
      setComplianceList(compData.violations || []);
      setStateMetrics(stData.items || []);
      setCourseMetrics(crsData.items || []);
      setLiveEvents(evData || []);
    } catch (err) {
      console.error("Failed to load AICTE overview metrics:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [academicYear]);

  // Subscribe to real-time live events (SSE)
  useEffect(() => {
    const unsubscribe = subscribeLiveEvents(
      (event) => {
        setLiveEvents((prev) => [event, ...prev.slice(0, 19)]);
        // Refresh high-level aggregates if submission or flag event arrives
        if (
          event.event?.startsWith("submission") ||
          event.event === "flag_resolved"
        ) {
          getOverviewMetrics(academicYear).then(setOverview).catch(() => {});
          getComplianceList({ academic_year: academicYear, min_overshoot: 1 })
            .then((res) => setComplianceList(res.violations || []))
            .catch(() => {});
        }
      },
      () => setSseStatus("reconnecting"),
      (status) => setSseStatus(status)
    );

    return () => {
      unsubscribe();
    };
  }, [academicYear]);

  if (loading && !overview) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-4">
        <Spinner size="lg" />
        <p className="text-sm font-medium ux4g-text-neutral-secondary">
          Aggregating national student enrolment and compliance metrics...
        </p>
      </div>
    );
  }

  const redListColleges = complianceList.filter((v) => v.is_red_list || v.overshoot > 0);

  return (
    <div className="space-y-6">
      {/* 1. Header & Live Connection Status */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wider ux4g-text-brand-primary px-2.5 py-0.5 rounded-full border ux4g-border-neutral-subtle">
              AICTE National Administration
            </span>

            {/* Live SSE Status Chip */}
            <div
              data-testid="sse-status-chip"
              role="status"
              aria-live="polite"
              className="flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold border"
              style={{
                backgroundColor:
                  sseStatus === "live"
                    ? "var(--ux4g-color-green-50)"
                    : "var(--ux4g-color-orange-50)",
                color:
                  sseStatus === "live"
                    ? "var(--ux4g-color-green-900)"
                    : "var(--ux4g-color-orange-900)",
                borderColor:
                  sseStatus === "live"
                    ? "var(--ux4g-color-green-300)"
                    : "var(--ux4g-color-orange-300)",
              }}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor:
                    sseStatus === "live"
                      ? "var(--ux4g-color-green-600)"
                      : "var(--ux4g-color-orange-600)",
                }}
              />
              <span>{sseStatus === "live" ? "Live" : "Reconnecting"}</span>
            </div>
          </div>

          <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight">
            Central Oversight & Analytics Dashboard
          </h1>
          <p className="text-xs ux4g-text-neutral-secondary mt-1">
            Supervisory Console &bull; Real-time Intake Reconciliation, Anomaly & Duplicate Verification
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
              <option value="2025-26">Academic Year 2025-26 (History)</option>
            </select>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={loadData}
            leftIcon={<Icon name="refresh" size="xs" color="inherit" />}
          >
            Refresh
          </Button>

          {user && <RoleBadge role={user.role} />}
        </div>
      </div>

      {/* 2. SPEC Section 12: KPI Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium ux4g-text-neutral-secondary uppercase tracking-wider">
            Colleges
          </p>
          <p className="text-2xl font-bold ux4g-text-neutral-primary">{overview?.total_colleges || 0}</p>
          <p className="text-[11px] font-medium" style={{ color: "var(--ux4g-color-green-700)" }}>
            {overview?.active_colleges || 0} active platforms
          </p>
        </div>

        <div className="p-4 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium ux4g-text-neutral-secondary uppercase tracking-wider">
            Total Enrolled
          </p>
          <p className="text-2xl font-bold ux4g-text-brand-primary">
            {(overview?.total_students_enrolled || 0).toLocaleString()}
          </p>
          <p className="text-[11px] ux4g-text-neutral-secondary">Across verified courses</p>
        </div>

        <div className="p-4 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium ux4g-text-neutral-secondary uppercase tracking-wider">
            Approved Intake
          </p>
          <p className="text-2xl font-bold ux4g-text-neutral-primary">
            {(overview?.total_approved_intake || 0).toLocaleString()}
          </p>
          <p className="text-[11px] ux4g-text-neutral-secondary">Regular quota seats</p>
        </div>

        <div
          className="p-4 ux4g-bg-neutral-elevated border rounded-xl space-y-1 shadow-sm"
          style={{ borderColor: "var(--ux4g-color-red-300)" }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--ux4g-color-red-800)" }}
          >
            Over-Intake Alerts
          </p>
          <p className="text-2xl font-bold" style={{ color: "var(--ux4g-color-red-700)" }}>
            {overview?.over_intake_violations_count || 0}
          </p>
          <p className="text-[11px] font-medium" style={{ color: "var(--ux4g-color-red-700)" }}>
            Red list institutions
          </p>
        </div>

        <div
          className="p-4 ux4g-bg-neutral-elevated border rounded-xl space-y-1 shadow-sm"
          style={{ borderColor: "var(--ux4g-color-orange-300)" }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--ux4g-color-orange-800)" }}
          >
            Duplicates
          </p>
          <p className="text-2xl font-bold" style={{ color: "var(--ux4g-color-orange-800)" }}>
            {overview?.total_duplicate_cases || 0}
          </p>
          <p className="text-[11px] font-medium" style={{ color: "var(--ux4g-color-orange-800)" }}>
            Cross-college alerts
          </p>
        </div>

        <div
          className="p-4 ux4g-bg-neutral-elevated border rounded-xl space-y-1 shadow-sm"
          style={{ borderColor: "var(--ux4g-color-purple-300)" }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--ux4g-color-purple-800)" }}
          >
            ML Anomalies
          </p>
          <p className="text-2xl font-bold" style={{ color: "var(--ux4g-color-purple-700)" }}>
            {overview?.total_anomalies_flagged || 0}
          </p>
          <p className="text-[11px] font-medium" style={{ color: "var(--ux4g-color-purple-700)" }}>
            IsolationForest flags
          </p>
        </div>
      </div>

      {/* 3. Analytical Charts (Order: State Intake, Submission Progress, Course Distribution) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <StateIntakeChart
            data={stateMetrics}
            height={300}
            headerRight={
              <Link
                to="/aicte/explore"
                className="text-xs ux4g-text-brand-primary font-semibold hover:underline flex items-center gap-1"
              >
                <span>Explore states</span>
                <Icon name="chevron_right" size="xs" color="inherit" />
              </Link>
            }
          />
        </div>

        <div>
          {overview?.submission_progress ? (
            <SubmissionProgressChart
              counts={overview.submission_progress}
              height={300}
              headerRight={
                <Link
                  to="/aicte/review"
                  className="text-xs ux4g-text-brand-primary font-semibold hover:underline"
                >
                  Review queue
                </Link>
              }
            />
          ) : (
            <div className="h-[300px] ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl flex items-center justify-center text-xs ux4g-text-neutral-secondary">
              No submission metrics recorded.
            </div>
          )}
        </div>
      </div>

      {/* Course Discipline Breakdown Chart */}
      <div>
        <CourseDistributionChart
          data={courseMetrics}
          height={280}
          headerRight={<span className="text-xs ux4g-text-neutral-secondary font-medium">Top 8 disciplines</span>}
        />
      </div>

      {/* 4. Tables & Sections: Red List of Over-Intake Colleges & Live System Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Compliance Red List */}
        <div
          className="lg:col-span-7 ux4g-bg-neutral-elevated border-2 rounded-xl shadow-sm overflow-hidden flex flex-col"
          style={{ borderColor: "var(--ux4g-color-red-400)" }}
        >
          <div
            className="border-b px-5 py-3.5 flex items-center justify-between"
            style={{
              backgroundColor: "var(--ux4g-color-red-50)",
              borderColor: "var(--ux4g-color-red-200)",
            }}
          >
            <div className="flex items-center gap-2">
              <span
                className="p-1.5 rounded-lg flex items-center justify-center text-white"
                style={{ backgroundColor: "var(--ux4g-color-red-700)" }}
              >
                <Icon name="warning" size="xs" color="inherit" />
              </span>
              <div>
                <h3 className="font-bold text-sm" style={{ color: "var(--ux4g-color-red-950)" }}>
                  Over-Intake Compliance Red List
                </h3>
                <p className="text-[11px] font-medium" style={{ color: "var(--ux4g-color-red-800)" }}>
                  Institutions admitting regular students beyond approved AICTE quota ({redListColleges.length} detected)
                </p>
              </div>
            </div>
            <Link to="/aicte/compliance">
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
              >
                View all violations
              </Button>
            </Link>
          </div>

          <div className="p-4 flex-1">
            {redListColleges.length === 0 ? (
              <div className="py-12 text-center text-xs ux4g-text-neutral-secondary">
                <Icon name="verified_user" size="lg" color="success" className="mx-auto mb-2" />
                <p className="font-semibold ux4g-text-neutral-primary">No Over-Intake Violations</p>
                <p className="ux4g-text-neutral-secondary">
                  All institutions currently within approved intake limits for {academicYear}.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {redListColleges.slice(0, 4).map((violation, idx) => (
                  <div
                    key={`${violation.institution_id}-${violation.course_id}-${idx}`}
                    className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold ux4g-text-neutral-primary text-xs">
                          {violation.institution_name}
                        </span>
                        <span className="font-mono text-[10px] ux4g-bg-neutral-elevated ux4g-text-neutral-secondary px-1.5 py-0.5 rounded border ux4g-border-neutral-subtle">
                          {violation.aicte_id}
                        </span>
                        <span className="text-[10px] ux4g-text-neutral-secondary font-medium">
                          {violation.state}
                        </span>
                      </div>
                      <p className="text-xs ux4g-text-neutral-secondary">
                        Course: <span className="font-medium ux4g-text-neutral-primary">{violation.course_name}</span>
                      </p>
                      <div className="flex items-center gap-3 text-xs flex-wrap">
                        <span className="ux4g-text-neutral-secondary">
                          Approved Intake: <strong className="ux4g-text-neutral-primary">{violation.approved_intake}</strong>
                        </span>
                        <span className="ux4g-text-neutral-secondary">
                          Admitted: <strong className="font-bold" style={{ color: "var(--ux4g-color-red-700)" }}>{violation.regular_admitted}</strong>
                        </span>
                        {/* Red List uses unified FlagBadge */}
                        <FlagBadge level="exception" label={`+${violation.overshoot} Over Intake`} />
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      <Button
                        size="sm"
                        variant="danger"
                        className="text-xs"
                        leftIcon={<Icon name="send" size="xs" color="inherit" />}
                        onClick={() =>
                          setSelectedNoticeCollege({
                            id: violation.institution_id,
                            name: violation.institution_name,
                            aicteId: violation.aicte_id,
                            overshoot: violation.overshoot,
                          })
                        }
                      >
                        Issue notice
                      </Button>
                      <Link
                        to={`/aicte/explore?state=${encodeURIComponent(violation.state)}&institution_id=${violation.institution_id}`}
                      >
                        <Button size="sm" variant="outline" className="text-xs">
                          Inspect
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}

                {redListColleges.length > 4 && (
                  <p className="text-center text-xs ux4g-text-neutral-secondary pt-1">
                    + {redListColleges.length - 4} more colleges over intake.{" "}
                    <Link to="/aicte/compliance" className="ux4g-text-brand-primary font-semibold hover:underline">
                      See complete compliance monitor &rarr;
                    </Link>
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (5 cols): Real-Time Live Activity Feed (SSE) */}
        <div className="lg:col-span-5 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm overflow-hidden flex flex-col">
          <div className="ux4g-bg-neutral-elevated border-b ux4g-border-neutral-subtle px-5 py-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span
                  className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                  style={{ backgroundColor: "var(--ux4g-color-green-400)" }}
                />
                <span
                  className="relative inline-flex rounded-full h-2.5 w-2.5"
                  style={{ backgroundColor: "var(--ux4g-color-green-500)" }}
                />
              </span>
              <div>
                <h3 className="font-bold text-xs flex items-center gap-1.5 ux4g-text-neutral-primary">
                  <Icon name="sensors" size="xs" color="inherit" />
                  Live System Activity Feed
                </h3>
                <p className="text-[10px] ux4g-text-neutral-secondary">
                  Real-time SSE event stream &bull; Live updates without refresh
                </p>
              </div>
            </div>
            <span
              className="text-[10px] font-mono px-2 py-0.5 rounded border"
              style={{
                backgroundColor: "var(--ux4g-color-green-50)",
                color: "var(--ux4g-color-green-900)",
                borderColor: "var(--ux4g-color-green-300)",
              }}
            >
              CONNECTED
            </span>
          </div>

          <div
            tabIndex={0}
            role="region"
            aria-label="Live event activity feed"
            className="p-3 flex-1 overflow-y-auto max-h-[360px] divide-y ux4g-border-neutral-subtle focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {liveEvents.length === 0 ? (
              <div className="py-12 text-center text-xs ux4g-text-neutral-secondary">
                <Icon name="notifications" size="md" color="inherit" className="mx-auto mb-2 opacity-50" />
                <p>Waiting for real-time submission or flag events...</p>
              </div>
            ) : (
              liveEvents.map((evt) => {
                const isNotice = evt.event === "notice_sent";
                const isResolution = evt.event === "flag_resolved";
                const isAnom = evt.event === "anomaly_detected";
                const isDupe = evt.event === "duplicate_enrolment";
                const isSub = evt.event?.startsWith("submission");

                const badgeBg = isNotice
                  ? "var(--ux4g-color-primary-600)"
                  : isResolution
                  ? "var(--ux4g-color-green-700)"
                  : isAnom
                  ? "var(--ux4g-color-purple-600)"
                  : isDupe
                  ? "var(--ux4g-color-orange-800)"
                  : isSub
                  ? "var(--ux4g-color-blue-600)"
                  : "var(--ux4g-color-neutral-600)";

                return (
                  <div key={evt.id} className="py-2.5 px-2 hover:ux4g-bg-neutral-soft transition text-xs flex items-start gap-2.5">
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-white font-bold text-[10px]"
                      style={{ backgroundColor: badgeBg }}
                    >
                      {isNotice ? "N" : isResolution ? "✓" : isAnom ? "A" : isDupe ? "D" : "S"}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold ux4g-text-neutral-primary truncate capitalize">
                          {evt.event?.replace(/_/g, " ")}
                        </span>
                        <span className="text-[10px] ux4g-text-neutral-secondary shrink-0">
                          {new Date(evt.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                      </div>
                      <p className="text-[11px] ux4g-text-neutral-secondary mt-0.5 truncate">
                        {evt.data?.message ||
                          evt.data?.subject ||
                          evt.data?.rule_code ||
                          evt.data?.status ||
                          JSON.stringify(evt.data)}
                      </p>
                      {evt.data?.institution_name && (
                        <p className="text-[10px] ux4g-text-neutral-secondary truncate">
                          {evt.data.institution_name}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 5. Navigation Quick Access Grid to SPEC Section 12 Modules */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold ux4g-text-neutral-primary text-sm border-b ux4g-border-neutral-subtle pb-3 flex items-center gap-2">
          <Icon name="grid_view" size="xs" color="primary" />
          AICTE central oversight modules
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <Link
            to="/aicte/compliance"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Over-Intake Compliance
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">Colleges over approved intake & red-list tracking</p>
          </Link>

          <Link
            to="/aicte/explore"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Hierarchical Drill-Down
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">State &rarr; College &rarr; Course &rarr; Flagged Students</p>
          </Link>

          <Link
            to="/aicte/duplicates"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Cross-College Duplicates
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">Detect simultaneous enrolments across institutions</p>
          </Link>

          <Link
            to="/aicte/anomalies"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Anomaly Detection
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">IsolationForest scores & plain-English alert insights</p>
          </Link>

          <Link
            to="/aicte/reports"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Reports & Exports
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">Export statutory CSV, Excel (XLSX), and PDF reports</p>
          </Link>

          <Link
            to="/aicte/rules"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Validation Rules Config
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">Customize rule levels, params, and toggles (Admin)</p>
          </Link>

          <Link
            to="/aicte/audit"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Audit Log & Hash Chain
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">Cryptographic tamper-evident SHA-256 verification</p>
          </Link>

          <Link
            to="/aicte/approvals"
            className="p-3.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft hover:ux4g-bg-neutral-subtle transition group"
          >
            <p className="font-bold ux4g-text-neutral-primary flex items-center justify-between">
              Approvals Queue
              <Icon name="open_in_new" size="xs" color="inherit" className="opacity-60 group-hover:opacity-100" />
            </p>
            <p className="ux4g-text-neutral-secondary mt-1">Review college activation requests & letters</p>
          </Link>
        </div>
      </div>

      {/* Notice Action Modal */}
      {selectedNoticeCollege && (
        <NoticeModal
          isOpen={true}
          onClose={() => setSelectedNoticeCollege(null)}
          institutionId={selectedNoticeCollege.id}
          institutionName={selectedNoticeCollege.name}
          aicteId={selectedNoticeCollege.aicteId}
          defaultSubject={`Immediate Clarification Required: Over-Intake of +${selectedNoticeCollege.overshoot} Students`}
          defaultMessage={`Upon automated validation against approved AICTE records for academic year ${academicYear}, your institution has exceeded approved regular intake quota by +${selectedNoticeCollege.overshoot} students. You are required to submit an official explanation or rectify records within 5 statutory working days.`}
          onSuccess={loadData}
        />
      )}
    </div>
  );
}
