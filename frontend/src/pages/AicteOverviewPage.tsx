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
import { Button } from "../components/ui/Button";
import { RoleBadge } from "../components/ui/Badge";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertTriangle,
  Bell,
  Building2,
  Calendar,
  ChevronRight,
  ExternalLink,
  FileCheck2,
  Radio,
  RefreshCw,
  Send,
  Shield,
  Users,
} from "lucide-react";

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
    const unsubscribe = subscribeLiveEvents((event) => {
      setLiveEvents((prev) => [event, ...prev.slice(0, 19)]);
      // Refresh high-level aggregates if submission or flag event arrives
      if (
        event.event === "submission_created" ||
        event.event === "submission_promoted" ||
        event.event === "flag_resolved"
      ) {
        getOverviewMetrics(academicYear).then(setOverview).catch(() => {});
        getComplianceList({ academic_year: academicYear, min_overshoot: 1 })
          .then((res) => setComplianceList(res.violations || []))
          .catch(() => {});
      }
    });

    return () => {
      unsubscribe();
    };
  }, [academicYear]);

  if (loading && !overview) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-4">
        <LoadingSpinner size="lg" />
        <p className="text-sm font-medium text-slate-600">
          Aggregating national student enrolment and compliance metrics...
        </p>
      </div>
    );
  }

  const redListColleges = complianceList.filter((v) => v.is_red_list || v.overshoot > 0);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
              AICTE National Administration
            </span>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Live Monitoring Engine Active</span>
            </div>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Central Oversight & Analytics Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Supervisory Console &bull; Real-time Intake Reconciliation, Anomaly & Duplicate Verification
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Academic Year selector */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26 (History)</option>
            </select>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={loadData}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>

          {user && <RoleBadge role={user.role} />}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Colleges</p>
          <p className="text-2xl font-bold text-slate-900">{overview?.total_colleges || 0}</p>
          <p className="text-[11px] text-emerald-600 font-medium">
            {overview?.active_colleges || 0} active platforms
          </p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Total Enrolled</p>
          <p className="text-2xl font-bold text-indigo-700">
            {(overview?.total_students_enrolled || 0).toLocaleString()}
          </p>
          <p className="text-[11px] text-slate-500">Across verified courses</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Approved Intake</p>
          <p className="text-2xl font-bold text-slate-900">
            {(overview?.total_approved_intake || 0).toLocaleString()}
          </p>
          <p className="text-[11px] text-slate-500">Regular quota seats</p>
        </div>

        <div className="p-4 bg-white border border-rose-200 bg-rose-50/20 rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium text-rose-700 uppercase tracking-wider">Over-Intake Alerts</p>
          <p className="text-2xl font-bold text-rose-600">
            {overview?.over_intake_violations_count || 0}
          </p>
          <p className="text-[11px] text-rose-600 font-medium">Red list institutions</p>
        </div>

        <div className="p-4 bg-white border border-amber-200 bg-amber-50/20 rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium text-amber-700 uppercase tracking-wider">Duplicates</p>
          <p className="text-2xl font-bold text-amber-600">
            {overview?.total_duplicate_cases || 0}
          </p>
          <p className="text-[11px] text-amber-600 font-medium">Cross-college alerts</p>
        </div>

        <div className="p-4 bg-white border border-purple-200 bg-purple-50/20 rounded-xl space-y-1 shadow-sm">
          <p className="text-[11px] font-medium text-purple-700 uppercase tracking-wider">ML Anomalies</p>
          <p className="text-2xl font-bold text-purple-600">
            {overview?.total_anomalies_flagged || 0}
          </p>
          <p className="text-[11px] text-purple-600 font-medium">IsolationForest flags</p>
        </div>
      </div>

      {/* PROMINENT SECTION 1: RED LIST OF OVER-INTAKE COLLEGES & PROMINENT SECTION 2: LIVE SSE FEED */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): The Red List of Over-Intake Colleges */}
        <div className="lg:col-span-7 bg-white border-2 border-rose-300 rounded-xl shadow-sm overflow-hidden flex flex-col">
          <div className="bg-rose-50 border-b border-rose-200 px-5 py-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-rose-600 text-white">
                <AlertTriangle className="w-4 h-4" />
              </span>
              <div>
                <h3 className="font-bold text-rose-950 text-sm">
                  Over-Intake Compliance Red List
                </h3>
                <p className="text-[11px] text-rose-700 font-medium">
                  Institutions admitting regular students beyond approved AICTE quota ({redListColleges.length} detected)
                </p>
              </div>
            </div>
            <Link to="/aicte/compliance">
              <Button size="sm" variant="outline" className="text-xs border-rose-300 text-rose-700 hover:bg-rose-100">
                View all violations
              </Button>
            </Link>
          </div>

          <div className="p-4 flex-1">
            {redListColleges.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                <Shield className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <p className="font-semibold text-slate-700">No Over-Intake Violations</p>
                <p className="text-slate-500">All institutions currently within approved intake limits for {academicYear}.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {redListColleges.slice(0, 4).map((violation, idx) => (
                  <div
                    key={`${violation.institution_id}-${violation.course_id}-${idx}`}
                    className="p-3.5 rounded-lg border border-rose-200 bg-rose-50/40 hover:bg-rose-50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-xs">
                          {violation.institution_name}
                        </span>
                        <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
                          {violation.aicte_id}
                        </span>
                        <span className="text-[10px] text-slate-500 font-medium">
                          {violation.state}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">
                        Course: <span className="font-medium text-slate-800">{violation.course_name}</span>
                      </p>
                      <div className="flex items-center gap-3 text-xs">
                        <span className="text-slate-500">
                          Approved Intake: <strong className="text-slate-700">{violation.approved_intake}</strong>
                        </span>
                        <span className="text-slate-500">
                          Admitted: <strong className="text-rose-700 font-bold">{violation.regular_admitted}</strong>
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-rose-600 text-white font-bold text-[11px]">
                          +{violation.overshoot} Over Intake
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      <Button
                        size="sm"
                        variant="danger"
                        className="text-xs"
                        leftIcon={<Send className="w-3.5 h-3.5" />}
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
                      <Link to={`/aicte/explore?state=${encodeURIComponent(violation.state)}&institution_id=${violation.institution_id}`}>
                        <Button size="sm" variant="outline" className="text-xs">
                          Inspect
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}

                {redListColleges.length > 4 && (
                  <p className="text-center text-xs text-slate-500 pt-1">
                    + {redListColleges.length - 4} more colleges over intake.{" "}
                    <Link to="/aicte/compliance" className="text-indigo-600 font-semibold hover:underline">
                      See complete compliance monitor &rarr;
                    </Link>
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (5 cols): PROMINENT Real-time Live Feed (SSE) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
          <div className="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <div>
                <h3 className="font-bold text-xs flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5 text-emerald-400" />
                  Live System Activity Feed
                </h3>
                <p className="text-[10px] text-slate-400">
                  Real-time SSE event stream &bull; Live updates without refresh
                </p>
              </div>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
              CONNECTED
            </span>
          </div>

          <div className="p-3 flex-1 overflow-y-auto max-h-[360px] divide-y divide-slate-100">
            {liveEvents.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                <Bell className="w-6 h-6 text-slate-300 mx-auto mb-2" />
                <p>Waiting for real-time submission or flag events...</p>
              </div>
            ) : (
              liveEvents.map((evt) => {
                const isNotice = evt.event === "notice_sent";
                const isResolution = evt.event === "flag_resolved";
                const isAnom = evt.event === "anomaly_detected";
                const isDupe = evt.event === "duplicate_enrolment";
                const isSub = evt.event?.startsWith("submission");

                return (
                  <div key={evt.id} className="py-2.5 px-2 hover:bg-slate-50 transition text-xs flex items-start gap-2.5">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-white font-bold text-[10px] ${
                        isNotice
                          ? "bg-indigo-600"
                          : isResolution
                          ? "bg-emerald-600"
                          : isAnom
                          ? "bg-purple-600"
                          : isDupe
                          ? "bg-amber-600"
                          : isSub
                          ? "bg-blue-600"
                          : "bg-slate-500"
                      }`}
                    >
                      {isNotice ? "N" : isResolution ? "✓" : isAnom ? "A" : isDupe ? "D" : "S"}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-slate-800 truncate capitalize">
                          {evt.event?.replace(/_/g, " ")}
                        </span>
                        <span className="text-[10px] text-slate-400 shrink-0">
                          {new Date(evt.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-0.5 truncate">
                        {evt.data?.message || evt.data?.subject || evt.data?.rule_code || evt.data?.status || JSON.stringify(evt.data)}
                      </p>
                      {evt.data?.institution_name && (
                        <p className="text-[10px] text-slate-400 truncate">
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

      {/* ECHARTS SECTION: 3 Analytical Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* State Capacity & Intake vs Enrolment Chart */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Building2 className="w-4 h-4 text-indigo-700" />
                State-Level Intake vs Actual Enrolment
              </h3>
              <p className="text-xs text-slate-500">
                Comparative analysis of approved seat capacity against actual admissions
              </p>
            </div>
            <Link to="/aicte/explore" className="text-xs text-indigo-600 font-semibold hover:underline flex items-center gap-1">
              Explore states <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <StateIntakeChart data={stateMetrics} height={300} />
        </div>

        {/* Submission Lifecycle Progress Donut Chart */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-blue-600" />
                Submission Progress
              </h3>
              <p className="text-xs text-slate-500">Status across {overview?.total_colleges} institutions</p>
            </div>
            <Link to="/aicte/review" className="text-xs text-indigo-600 font-semibold hover:underline">
              Review queue
            </Link>
          </div>
          {overview?.submission_progress ? (
            <SubmissionProgressChart counts={overview.submission_progress} height={300} />
          ) : (
            <div className="h-[300px] flex items-center justify-center text-xs text-slate-400">
              No submission metrics recorded.
            </div>
          )}
        </div>
      </div>

      {/* Course Discipline Breakdown */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-600" />
              Course Discipline Seat Capacity & Enrolment
            </h3>
            <p className="text-xs text-slate-500">
              Distribution across top academic disciplines and engineering programs
            </p>
          </div>
          <span className="text-xs text-slate-500 font-medium">Top 8 disciplines</span>
        </div>
        <CourseDistributionChart data={courseMetrics} height={280} />
      </div>

      {/* Navigation Quick Access Grid */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-3 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-indigo-700" />
          AICTE Central Oversight Modules
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <Link
            to="/aicte/compliance"
            className="p-3.5 rounded-lg border border-rose-200 bg-rose-50/30 hover:bg-rose-50 hover:border-rose-400 transition group"
          >
            <p className="font-bold text-rose-950 flex items-center justify-between">
              Over-Intake Compliance
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Colleges over approved intake & red-list tracking</p>
          </Link>

          <Link
            to="/aicte/explore"
            className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition group"
          >
            <p className="font-bold text-slate-900 flex items-center justify-between">
              Hierarchical Drill-Down
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">State &rarr; College &rarr; Course &rarr; Flagged Students</p>
          </Link>

          <Link
            to="/aicte/duplicates"
            className="p-3.5 rounded-lg border border-amber-200 bg-amber-50/30 hover:bg-amber-50 hover:border-amber-400 transition group"
          >
            <p className="font-bold text-amber-950 flex items-center justify-between">
              Cross-College Duplicates
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Detect simultaneous enrolments across institutions</p>
          </Link>

          <Link
            to="/aicte/anomalies"
            className="p-3.5 rounded-lg border border-purple-200 bg-purple-50/30 hover:bg-purple-50 hover:border-purple-400 transition group"
          >
            <p className="font-bold text-purple-950 flex items-center justify-between">
              Anomaly Detection
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">IsolationForest scores & plain-English alert insights</p>
          </Link>

          <Link
            to="/aicte/reports"
            className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition group"
          >
            <p className="font-bold text-slate-900 flex items-center justify-between">
              Reports & Exports
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Export statutory CSV, Excel (XLSX), and PDF reports</p>
          </Link>

          <Link
            to="/aicte/rules"
            className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition group"
          >
            <p className="font-bold text-slate-900 flex items-center justify-between">
              Validation Rules Config
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Customize rule levels, params, and toggles (Admin)</p>
          </Link>

          <Link
            to="/aicte/audit"
            className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition group"
          >
            <p className="font-bold text-slate-900 flex items-center justify-between">
              Audit Log & Hash Chain
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Cryptographic tamper-evident SHA-256 verification</p>
          </Link>

          <Link
            to="/aicte/approvals"
            className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition group"
          >
            <p className="font-bold text-slate-900 flex items-center justify-between">
              Approvals Queue
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Review college activation requests & letters</p>
          </Link>

          <Link
            to="/aicte/intake"
            className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition group"
          >
            <p className="font-bold text-slate-900 flex items-center justify-between">
              Intake Quota Control
              <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            </p>
            <p className="text-slate-600 mt-1">Edit approved quotas & audit historical changes</p>
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
