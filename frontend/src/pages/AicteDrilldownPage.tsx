import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getDrilldown } from "../api/analytics";
import type { DrilldownResponse } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { ResolveFlagModal } from "../components/action/ResolveFlagModal";
import { FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  Building2,
  Calendar,
  ChevronRight,
  GraduationCap,
  Home,
  MapPin,
  RefreshCw,
  Search,
  Send,
} from "lucide-react";

export function AicteDrilldownPage() {
  useDocumentTitle("Drill-Down Data Explorer");
  const [searchParams, setSearchParams] = useSearchParams();
  const academicYear = searchParams.get("academic_year") || "2026-27";
  const stateParam = searchParams.get("state") || "";
  const institutionParam = searchParams.get("institution_id")
    ? Number(searchParams.get("institution_id"))
    : undefined;
  const courseParam = searchParams.get("course_id")
    ? Number(searchParams.get("course_id"))
    : undefined;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DrilldownResponse | null>(null);
  const [studentSearch, setStudentSearch] = useState("");

  // Modals state
  const [selectedNoticeCollege, setSelectedNoticeCollege] = useState<{
    id: number;
    name: string;
    aicteId: string;
  } | null>(null);

  const [selectedResolveFlag, setSelectedResolveFlag] = useState<{
    id: number;
    ruleCode: string;
    message: string;
    studentName?: string;
    apaarId?: string;
  } | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const res = await getDrilldown({
        academic_year: academicYear,
        state: stateParam || undefined,
        institution_id: institutionParam,
        course_id: courseParam,
      });
      setData(res);
    } catch (err) {
      console.error("Failed to load hierarchical drilldown:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [academicYear, stateParam, institutionParam, courseParam]);

  function navigateTo(updates: { state?: string; institution_id?: number; course_id?: number }) {
    const next = new URLSearchParams(searchParams);
    if (updates.state !== undefined) {
      if (updates.state) next.set("state", updates.state);
      else next.delete("state");
    }
    if (updates.institution_id !== undefined) {
      if (updates.institution_id) next.set("institution_id", String(updates.institution_id));
      else next.delete("institution_id");
    }
    if (updates.course_id !== undefined) {
      if (updates.course_id) next.set("course_id", String(updates.course_id));
      else next.delete("course_id");
    }
    setSearchParams(next);
  }

  const currentLevel = data?.level || "national";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
              Hierarchical Drill-Down
            </span>
            <span className="text-xs text-slate-500 font-medium">
              &bull; National &rarr; State &rarr; College &rarr; Course &rarr; Flagged Students
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Institutional Data Explorer & Student Auditing
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Navigate through governance tiers down to granular student records and validation flags
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={academicYear}
              onChange={(e) => {
                const next = new URLSearchParams(searchParams);
                next.set("academic_year", e.target.value);
                setSearchParams(next);
              }}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26</option>
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
        </div>
      </div>

      {/* Interactive Breadcrumb Bar */}
      <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex items-center flex-wrap gap-2 text-xs">
        <button
          type="button"
          onClick={() => navigateTo({ state: "", institution_id: 0, course_id: 0 })}
          className={`flex items-center gap-1 font-semibold transition ${
            currentLevel === "national"
              ? "text-indigo-700 font-bold bg-indigo-50 px-2.5 py-1 rounded-md"
              : "text-slate-600 hover:text-indigo-600"
          }`}
        >
          <Home className="w-3.5 h-3.5" />
          <span>All States (National)</span>
        </button>

        {stateParam && (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <button
              type="button"
              onClick={() => navigateTo({ institution_id: 0, course_id: 0 })}
              className={`flex items-center gap-1 font-semibold transition ${
                currentLevel === "state"
                  ? "text-indigo-700 font-bold bg-indigo-50 px-2.5 py-1 rounded-md"
                  : "text-slate-600 hover:text-indigo-600"
              }`}
            >
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              <span>{stateParam}</span>
            </button>
          </>
        )}

        {data?.institution && (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <button
              type="button"
              onClick={() => navigateTo({ course_id: 0 })}
              className={`flex items-center gap-1 font-semibold transition ${
                currentLevel === "college"
                  ? "text-indigo-700 font-bold bg-indigo-50 px-2.5 py-1 rounded-md"
                  : "text-slate-600 hover:text-indigo-600"
              }`}
            >
              <Building2 className="w-3.5 h-3.5 text-slate-400" />
              <span>{data.institution.name}</span>
            </button>
          </>
        )}

        {data?.course && (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="flex items-center gap-1 font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-md">
              <GraduationCap className="w-3.5 h-3.5 text-indigo-600" />
              <span>{data.course.name}</span>
            </span>
          </>
        )}
      </div>

      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3 bg-white border border-slate-200 rounded-xl shadow-sm">
          <LoadingSpinner size="md" />
          <p className="text-xs text-slate-500">Querying hierarchy level: {currentLevel}...</p>
        </div>
      ) : (
        <>
          {/* LEVEL 1: NATIONAL / STATES TABLE */}
          {currentLevel === "national" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <h3 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                  State-Level Enrolment & Compliance Breakdown
                </h3>
                <span className="text-xs text-slate-500">{data?.states?.length || 0} States Registered</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                      <th className="py-3 px-4">State Jurisdiction</th>
                      <th className="py-3 px-4 text-center">Approved Colleges</th>
                      <th className="py-3 px-4 text-center">Approved Intake</th>
                      <th className="py-3 px-4 text-center">Total Enrolled</th>
                      <th className="py-3 px-4 text-center">Over-Intake Colleges</th>
                      <th className="py-3 px-4 text-right">Drill Down</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data?.states?.map((st) => (
                      <tr
                        key={st.state}
                        onClick={() => navigateTo({ state: st.state })}
                        className="hover:bg-indigo-50/30 cursor-pointer transition"
                      >
                        <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                          <MapPin className="w-3.5 h-3.5 text-slate-400" />
                          {st.state}
                        </td>
                        <td className="py-3.5 px-4 text-center font-medium text-slate-700">
                          {st.colleges_count}
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-slate-700">
                          {st.approved_intake?.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-indigo-700">
                          {st.total_enrolled?.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {st.over_intake_colleges > 0 ? (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              {st.over_intake_colleges} Violations
                            </span>
                          ) : (
                            <span className="text-slate-400 font-medium">None</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <Button size="sm" variant="ghost" className="text-xs text-indigo-700">
                            Explore state &rarr;
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* LEVEL 2: COLLEGES IN SELECTED STATE */}
          {currentLevel === "state" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                    Institutions in {stateParam}
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Select a college to view approved course streams and enrolled cohorts
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => navigateTo({ state: "" })}>
                  &larr; Back to all states
                </Button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                      <th className="py-3 px-4">Institution Name & AICTE ID</th>
                      <th className="py-3 px-4">District</th>
                      <th className="py-3 px-4 text-center">Approved Intake</th>
                      <th className="py-3 px-4 text-center">Admitted Regular</th>
                      <th className="py-3 px-4 text-center">Compliance Status</th>
                      <th className="py-3 px-4 text-center">Flags Raised</th>
                      <th className="py-3 px-4 text-right">Directives</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data?.colleges?.map((col) => (
                      <tr key={col.institution_id} className="hover:bg-indigo-50/30 transition">
                        <td
                          className="py-3.5 px-4 cursor-pointer"
                          onClick={() => navigateTo({ institution_id: col.institution_id })}
                        >
                          <div className="font-bold text-slate-900">{col.name}</div>
                          <div className="font-mono text-[10px] text-slate-500">{col.aicte_id}</div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">{col.district || "-"}</td>
                        <td className="py-3.5 px-4 text-center font-bold text-slate-700">
                          {col.approved_intake}
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-slate-900">
                          {col.regular_admitted}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {col.overshoot > 0 ? (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              +{col.overshoot} Over Intake
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Compliant
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {col.total_flags > 0 ? (
                            <span className="font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                              {col.total_flags}
                            </span>
                          ) : (
                            <span className="text-slate-400">0</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs"
                              onClick={() =>
                                setSelectedNoticeCollege({
                                  id: col.institution_id,
                                  name: col.name,
                                  aicteId: col.aicte_id,
                                })
                              }
                            >
                              Notice
                            </Button>
                            <Button
                              size="sm"
                              variant="primary"
                              className="text-xs bg-indigo-900"
                              onClick={() => navigateTo({ institution_id: col.institution_id })}
                            >
                              Inspect courses &rarr;
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* LEVEL 3: COURSES IN SELECTED COLLEGE */}
          {currentLevel === "college" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">
                    {data?.institution?.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    AICTE ID: {data?.institution?.aicte_id} &bull; {data?.institution?.state}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="danger"
                    leftIcon={<Send className="w-3.5 h-3.5" />}
                    onClick={() =>
                      data?.institution &&
                      setSelectedNoticeCollege({
                        id: data.institution.institution_id,
                        name: data.institution.name,
                        aicteId: data.institution.aicte_id,
                      })
                    }
                  >
                    Issue college notice
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigateTo({ institution_id: 0 })}
                  >
                    &larr; Back to {stateParam}
                  </Button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                      <th className="py-3 px-4">Approved Course Stream</th>
                      <th className="py-3 px-4">Level</th>
                      <th className="py-3 px-4 text-center">Approved Regular</th>
                      <th className="py-3 px-4 text-center">Admitted Regular</th>
                      <th className="py-3 px-4 text-center">Supernumerary (Adm/Max)</th>
                      <th className="py-3 px-4 text-center">Quota Status</th>
                      <th className="py-3 px-4 text-center">Flagged Students</th>
                      <th className="py-3 px-4 text-right">Student Cohort</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data?.courses?.map((c) => (
                      <tr key={c.course_id} className="hover:bg-indigo-50/30 transition">
                        <td
                          className="py-3.5 px-4 font-bold text-slate-900 cursor-pointer"
                          onClick={() => navigateTo({ course_id: c.course_id })}
                        >
                          {c.name}
                          {c.branch && <span className="block text-[11px] font-normal text-slate-500">{c.branch}</span>}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 font-medium text-slate-700 border border-slate-200">
                            {c.level}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-slate-700">
                          {c.approved_intake}
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-slate-900">
                          {c.regular_admitted}
                        </td>
                        <td className="py-3.5 px-4 text-center text-slate-600">
                          <span className="font-semibold text-slate-800">{c.supernumerary_admitted}</span>
                          <span className="text-slate-400"> / {c.supernumerary_allowed}</span>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {c.overshoot > 0 ? (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              +{c.overshoot} Over Intake
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Within Limit
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {c.flagged_students_count > 0 ? (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                              {c.flagged_students_count} Students
                            </span>
                          ) : (
                            <span className="text-slate-400">0</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <Button
                            size="sm"
                            variant="primary"
                            className="text-xs bg-indigo-900"
                            onClick={() => navigateTo({ course_id: c.course_id })}
                          >
                            Inspect students &rarr;
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* LEVEL 4: STUDENTS IN SELECTED COURSE */}
          {currentLevel === "course" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden space-y-4">
              <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 font-bold text-xs uppercase">
                      {data?.course?.level}
                    </span>
                    <h3 className="font-bold text-slate-900 text-base">{data?.course?.name}</h3>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {data?.institution?.name} &bull; Approved Intake:{" "}
                    <strong>{data?.course?.approved_intake}</strong> &bull; Total Enrolled:{" "}
                    <strong>{data?.students?.length || 0}</strong>
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigateTo({ course_id: 0 })}
                  >
                    &larr; Back to courses
                  </Button>
                </div>
              </div>

              {/* Student Search and Filters */}
              <div className="px-5 flex items-center justify-between gap-3 text-xs">
                <div className="relative w-full sm:w-72">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={studentSearch}
                    onChange={(e) => setStudentSearch(e.target.value)}
                    placeholder="Search student by name, APAAR ID, or enrolment ID..."
                    className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <span className="text-xs text-slate-500">
                  Showing {data?.students?.length || 0} enrolled records
                </span>
              </div>

              {/* Students Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                      <th className="py-3 px-4">Student & APAAR ID</th>
                      <th className="py-3 px-4">Enrolment ID</th>
                      <th className="py-3 px-4">Admission Mode</th>
                      <th className="py-3 px-4">Seat Type</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Active Validation Flags & Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data?.students
                      ?.filter((s) => {
                        if (!studentSearch.trim()) return true;
                        const q = studentSearch.toLowerCase();
                        return (
                          s.name.toLowerCase().includes(q) ||
                          s.apaar_id.includes(q) ||
                          s.enrolment_no.toLowerCase().includes(q)
                        );
                      })
                      .map((st) => (
                        <tr key={st.id} className="hover:bg-slate-50/40 transition">
                          <td className="py-3 px-4">
                            <div className="font-bold text-slate-900">{st.name}</div>
                            <div className="font-mono text-[11px] text-slate-500">{st.apaar_id}</div>
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-600">{st.enrolment_no}</td>
                          <td className="py-3 px-4 text-slate-700">{st.admission_mode}</td>
                          <td className="py-3 px-4 font-medium text-slate-800">{st.seat_type}</td>
                          <td className="py-3 px-4 text-slate-600">{st.reservation_category}</td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                st.status === "valid" || st.status === "verified"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {st.status}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {st.flags && st.flags.length > 0 ? (
                              <div className="space-y-1.5">
                                {st.flags.map((f) => (
                                  <div
                                    key={f.id}
                                    className="p-1.5 rounded-md border border-slate-200 bg-slate-50/70 text-[11px] flex items-start justify-between gap-2"
                                  >
                                    <div>
                                      <div className="flex items-center gap-1.5">
                                        <FlagBadge level={f.level as any} />
                                        <span className="font-mono font-bold text-slate-800">
                                          {f.rule_code}
                                        </span>
                                      </div>
                                      <p className="text-slate-600 mt-0.5">{f.message}</p>
                                    </div>

                                    {f.status === "open" && (
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="text-[10px] py-0.5 px-1.5 h-6 shrink-0 text-emerald-700 hover:bg-emerald-50 border-emerald-300"
                                        onClick={() =>
                                          setSelectedResolveFlag({
                                            id: f.id,
                                            ruleCode: f.rule_code,
                                            message: f.message,
                                            studentName: st.name,
                                            apaarId: st.apaar_id,
                                          })
                                        }
                                      >
                                        Resolve
                                      </Button>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <span className="text-slate-400 text-xs">No active flags</span>
                            )}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Action Modals */}
      {selectedNoticeCollege && (
        <NoticeModal
          isOpen={true}
          onClose={() => setSelectedNoticeCollege(null)}
          institutionId={selectedNoticeCollege.id}
          institutionName={selectedNoticeCollege.name}
          aicteId={selectedNoticeCollege.aicteId}
          onSuccess={loadData}
        />
      )}

      {selectedResolveFlag && (
        <ResolveFlagModal
          isOpen={true}
          onClose={() => setSelectedResolveFlag(null)}
          flagId={selectedResolveFlag.id}
          ruleCode={selectedResolveFlag.ruleCode}
          flagMessage={selectedResolveFlag.message}
          studentName={selectedResolveFlag.studentName}
          apaarId={selectedResolveFlag.apaarId}
          onSuccess={loadData}
        />
      )}
    </div>
  );
}
