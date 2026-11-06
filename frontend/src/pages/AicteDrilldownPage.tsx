import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getDrilldown } from "../api/analytics";
import type { DrilldownResponse } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { ResolveFlagModal } from "../components/action/ResolveFlagModal";
import { Button } from "../components/ux4g/Button";
import { FlagBadge } from "../components/ux4g/Badge";
import { Breadcrumb, type BreadcrumbItem } from "../components/ux4g/Breadcrumb";
import { Spinner } from "../components/ux4g/Spinner";
import { Icon } from "../components/ux4g/Icon";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ux4g/Table";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

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

  // Build breadcrumb items strictly adhering to (state, college, course, students)
  const breadcrumbItems: BreadcrumbItem[] = [
    {
      label: "All States (National)",
      href: currentLevel !== "national" ? `/aicte/explore?academic_year=${academicYear}` : undefined,
    },
  ];

  if (stateParam) {
    breadcrumbItems.push({
      label: stateParam,
      href:
        currentLevel !== "state"
          ? `/aicte/explore?academic_year=${academicYear}&state=${encodeURIComponent(stateParam)}`
          : undefined,
    });
  }

  if (data?.institution) {
    breadcrumbItems.push({
      label: data.institution.name,
      href:
        currentLevel !== "college"
          ? `/aicte/explore?academic_year=${academicYear}&state=${encodeURIComponent(stateParam)}&institution_id=${data.institution.id}`
          : undefined,
    });
  }

  if (data?.course) {
    breadcrumbItems.push({
      label: data.course.name,
      href:
        data?.students && data.students.length > 0
          ? `/aicte/explore?academic_year=${academicYear}&state=${encodeURIComponent(stateParam)}&institution_id=${data.institution?.id}&course_id=${data.course.id}`
          : undefined,
    });

    if (data?.students && data.students.length > 0) {
      breadcrumbItems.push({
        label: "Flagged Students",
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wider ux4g-text-brand-primary px-2.5 py-0.5 rounded-full border ux4g-border-neutral-subtle">
              Hierarchical Drill-Down
            </span>
            <span className="text-xs ux4g-text-neutral-secondary font-medium">
              &bull; National &rarr; State &rarr; College &rarr; Course &rarr; Flagged Students
            </span>
          </div>
          <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight">
            Institutional Data Explorer & Student Auditing
          </h1>
          <p className="text-xs ux4g-text-neutral-secondary mt-1">
            Navigate through governance tiers down to granular student records and validation flags
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 ux4g-bg-neutral-soft border ux4g-border-neutral-subtle rounded-lg px-2.5 py-1.5 text-xs">
            <Icon name="calendar_month" size="xs" color="inherit" className="ux4g-text-neutral-secondary" />
            <select
              value={academicYear}
              onChange={(e) => {
                const next = new URLSearchParams(searchParams);
                next.set("academic_year", e.target.value);
                setSearchParams(next);
              }}
              className="bg-transparent font-semibold ux4g-text-neutral-primary focus:outline-none cursor-pointer"
              aria-label="Select Academic Year"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26</option>
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
        </div>
      </div>

      {/* UX4G Drill-Down Breadcrumb Bar */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl px-4 py-3 shadow-sm">
        <Breadcrumb items={breadcrumbItems} ariaLabel="Drill-down hierarchy breadcrumb" />
      </div>

      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3 ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm">
          <Spinner size="md" />
          <p className="text-xs ux4g-text-neutral-secondary">Querying hierarchy level: {currentLevel}...</p>
        </div>
      ) : (
        <>
          {/* LEVEL 1: NATIONAL / STATES TABLE */}
          {currentLevel === "national" && (
            <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 ux4g-bg-neutral-soft border-b ux4g-border-neutral-subtle flex items-center justify-between">
                <h3 className="font-bold text-xs ux4g-text-neutral-primary uppercase tracking-wider">
                  State-level enrolment and compliance breakdown
                </h3>
                <span className="text-xs ux4g-text-neutral-secondary">{data?.states?.length || 0} States Registered</span>
              </div>

              <div
                tabIndex={0}
                role="region"
                aria-label="States breakdown table"
                className="overflow-x-auto w-full focus:outline-none"
              >
                <Table className="min-w-[700px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>State Jurisdiction</TableHead>
                      <TableHead className="text-center">Approved Colleges</TableHead>
                      <TableHead className="text-center">Approved Intake</TableHead>
                      <TableHead className="text-center">Total Enrolled</TableHead>
                      <TableHead className="text-center">Over-Intake Colleges</TableHead>
                      <TableHead className="text-right">Drill Down</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data?.states?.map((st) => (
                      <TableRow
                        key={st.state}
                        onClick={() => navigateTo({ state: st.state })}
                        className="cursor-pointer"
                      >
                        <TableCell className="font-bold ux4g-text-neutral-primary flex items-center gap-2">
                          <Icon name="location_on" size="xs" color="inherit" className="ux4g-text-neutral-secondary" />
                          <span>{st.state}</span>
                        </TableCell>
                        <TableCell className="text-center font-medium ux4g-text-neutral-primary">
                          {st.colleges_count}
                        </TableCell>
                        <TableCell className="text-center font-bold ux4g-text-neutral-primary">
                          {st.approved_intake?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-center font-bold ux4g-text-brand-primary">
                          {st.total_enrolled?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-center">
                          {(st.over_intake_colleges ?? st.over_intake_colleges_count ?? 0) > 0 ? (
                            <span
                              className="px-2 py-0.5 rounded-full font-bold text-xs border"
                              style={{
                                backgroundColor: "var(--ux4g-color-red-50)",
                                color: "var(--ux4g-color-red-800)",
                                borderColor: "var(--ux4g-color-red-300)",
                              }}
                            >
                              {st.over_intake_colleges ?? st.over_intake_colleges_count} Over Limit
                            </span>
                          ) : (
                            <span
                              className="font-medium text-xs"
                              style={{ color: "var(--ux4g-color-green-700)" }}
                            >
                              100% Compliant
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" variant="outline" className="text-xs">
                            Inspect State &rarr;
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* LEVEL 2: COLLEGES IN SELECTED STATE */}
          {currentLevel === "state" && (
            <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 ux4g-bg-neutral-soft border-b ux4g-border-neutral-subtle flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-xs ux4g-text-neutral-primary uppercase tracking-wider">
                    Institutions in {stateParam}
                  </h3>
                  <p className="text-[11px] ux4g-text-neutral-secondary">
                    {(data?.colleges || data?.institutions || []).length} AICTE approved colleges
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigateTo({ state: "" })}
                  className="text-xs"
                >
                  &larr; Back to all states
                </Button>
              </div>

              <div
                tabIndex={0}
                role="region"
                aria-label={`Institutions in ${stateParam}`}
                className="overflow-x-auto w-full focus:outline-none"
              >
                <Table className="min-w-[800px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Institution Name & AICTE ID</TableHead>
                      <TableHead>District</TableHead>
                      <TableHead className="text-center">Approved Courses</TableHead>
                      <TableHead className="text-center">Approved Intake</TableHead>
                      <TableHead className="text-center">Total Enrolled</TableHead>
                      <TableHead className="text-center">Status</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(data?.colleges || data?.institutions || []).map((inst: any) => {
                      const isOver = inst.overshoot > 0;
                      return (
                        <TableRow
                          key={inst.institution_id || inst.id}
                          onClick={() => navigateTo({ institution_id: inst.institution_id || inst.id })}
                          className="cursor-pointer"
                        >
                          <TableCell>
                            <div className="font-bold ux4g-text-neutral-primary">{inst.name}</div>
                            <div className="font-mono text-[10px] ux4g-text-neutral-secondary">
                              {inst.aicte_id} &bull; {inst.approval_status}
                            </div>
                          </TableCell>
                          <TableCell className="ux4g-text-neutral-primary">{inst.district || "-"}</TableCell>
                          <TableCell className="text-center font-medium ux4g-text-neutral-primary">
                            {inst.courses_count}
                          </TableCell>
                          <TableCell className="text-center font-bold ux4g-text-neutral-primary">
                            {inst.approved_intake?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-center font-bold ux4g-text-brand-primary">
                            {inst.total_enrolled?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-center">
                            {isOver ? (
                              <FlagBadge level="exception" label={`+${inst.overshoot} Over Intake`} />
                            ) : (
                              <span
                                className="font-medium text-xs"
                                style={{ color: "var(--ux4g-color-green-700)" }}
                              >
                                Within Quota
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button size="sm" variant="outline" className="text-xs">
                              View Courses &rarr;
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* LEVEL 3: COURSES IN SELECTED COLLEGE */}
          {currentLevel === "college" && data?.institution && (
            <div className="space-y-4">
              {/* Institution Header Card */}
              <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-mono text-xs px-2 py-0.5 rounded ux4g-bg-neutral-soft border ux4g-border-neutral-subtle">
                      AICTE ID: {data.institution.aicte_id}
                    </span>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded border ux4g-border-neutral-subtle">
                      Status: {data.institution.approval_status}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold ux4g-text-neutral-primary">{data.institution.name}</h2>
                  <p className="text-xs ux4g-text-neutral-secondary mt-1">
                    {data.institution.address}, {data.institution.district}, {data.institution.state} &bull; Official Email: {data.institution.official_email}
                  </p>
                </div>

                <div className="flex items-center gap-2 self-start md:self-center flex-wrap">
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() =>
                      setSelectedNoticeCollege({
                        id: data.institution!.institution_id || data.institution!.id || 0,
                        name: data.institution!.name,
                        aicteId: data.institution!.aicte_id,
                      })
                    }
                    leftIcon={<Icon name="send" size="xs" color="inherit" />}
                  >
                    Issue formal notice
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigateTo({ institution_id: 0 })}
                  >
                    &larr; Back to colleges
                  </Button>
                </div>
              </div>

              {/* Courses Table */}
              <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm overflow-hidden">
                <div className="px-5 py-3.5 ux4g-bg-neutral-soft border-b ux4g-border-neutral-subtle flex items-center justify-between">
                  <h3 className="font-bold text-xs ux4g-text-neutral-primary uppercase tracking-wider">
                    Academic courses and seat quotas ({data.courses?.length || 0})
                  </h3>
                </div>

                <div
                  tabIndex={0}
                  role="region"
                  aria-label="Courses list"
                  className="overflow-x-auto w-full focus:outline-none"
                >
                  <Table className="min-w-[800px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Course Discipline & Level</TableHead>
                        <TableHead className="text-center">Approved Regular Intake</TableHead>
                        <TableHead className="text-center">Regular Admitted</TableHead>
                        <TableHead className="text-center">Compliance Status</TableHead>
                        <TableHead className="text-center">Supernumerary (Adm/Max)</TableHead>
                        <TableHead className="text-center">Active Flags</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.courses?.map((c) => {
                        const isOver = c.regular_admitted > c.approved_intake;
                        const overshoot = c.regular_admitted - c.approved_intake;
                        return (
                          <TableRow
                            key={c.course_id || c.id}
                            onClick={() => navigateTo({ course_id: c.course_id || c.id })}
                            className="cursor-pointer"
                          >
                            <TableCell>
                              <div className="font-bold ux4g-text-neutral-primary">{c.name}</div>
                              <div className="text-[10px] ux4g-text-neutral-secondary">
                                {c.level} &bull; {c.branch || "General"}
                              </div>
                            </TableCell>
                            <TableCell className="text-center font-bold ux4g-text-neutral-primary">
                              {c.approved_intake}
                            </TableCell>
                            <TableCell className="text-center font-bold ux4g-text-brand-primary">
                              {c.regular_admitted}
                            </TableCell>
                            <TableCell className="text-center">
                              {isOver ? (
                                <FlagBadge level="exception" label={`+${overshoot} Over Intake`} />
                              ) : (
                                <span
                                  className="font-medium text-xs"
                                  style={{ color: "var(--ux4g-color-green-700)" }}
                                >
                                  Within Quota
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="text-center ux4g-text-neutral-secondary">
                              <span className="font-medium ux4g-text-neutral-primary">{c.supernumerary_admitted}</span>
                              <span> / {c.supernumerary_allowed}</span>
                            </TableCell>
                            <TableCell className="text-center">
                              {(c.flagged_students_count ?? c.flags_count ?? 0) > 0 ? (
                                <FlagBadge level="warning" label={`${c.flagged_students_count ?? c.flags_count} Flags`} />
                              ) : (
                                <span className="text-xs ux4g-text-neutral-secondary">Clean</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              <Button size="sm" variant="outline" className="text-xs">
                                Inspect Students &rarr;
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          )}

          {/* LEVEL 4: STUDENTS IN SELECTED COURSE */}
          {currentLevel === "course" && data?.course && data?.institution && (
            <div className="space-y-4">
              {/* Course Detail Card */}
              <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded ux4g-bg-neutral-soft border ux4g-border-neutral-subtle">
                      {data.course.level} Program
                    </span>
                    <span className="text-xs ux4g-text-neutral-secondary">
                      {data.institution.name} ({data.institution.aicte_id})
                    </span>
                  </div>
                  <h2 className="text-xl font-bold ux4g-text-neutral-primary">{data.course.name}</h2>
                  <div className="flex items-center gap-4 text-xs ux4g-text-neutral-secondary mt-1 flex-wrap">
                    <span>
                      Approved Intake: <strong className="ux4g-text-neutral-primary">{data.course.approved_intake}</strong>
                    </span>
                    <span>
                      Regular Admitted: <strong className="ux4g-text-brand-primary">{data.course.regular_admitted}</strong>
                    </span>
                    <span>
                      Supernumerary Allowed: <strong className="ux4g-text-neutral-primary">{data.course.supernumerary_allowed}</strong>
                    </span>
                    <span>
                      Enrolled Students: <strong className="ux4g-text-neutral-primary">{data.students?.length || 0}</strong>
                    </span>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigateTo({ course_id: 0 })}
                >
                  &larr; Back to courses
                </Button>
              </div>

              {/* Students Search & Filter */}
              <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                <div className="relative w-full sm:w-80">
                  <Icon name="search" size="xs" color="inherit" className="ux4g-text-neutral-secondary absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={studentSearch}
                    onChange={(e) => setStudentSearch(e.target.value)}
                    placeholder="Search by student name, APAAR ID, or enrolment #..."
                    className="w-full pl-9 pr-3 py-2 text-xs border ux4g-border-neutral-subtle rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ux4g-bg-neutral-elevated ux4g-text-neutral-primary"
                  />
                </div>
                <span className="text-xs ux4g-text-neutral-secondary">
                  Showing {data.students?.length || 0} student records
                </span>
              </div>

              {/* Students Table */}
              <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm overflow-hidden">
                <div
                  tabIndex={0}
                  role="region"
                  aria-label="Student records list"
                  className="overflow-x-auto w-full focus:outline-none"
                >
                  <Table className="min-w-[900px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Student Name & APAAR ID</TableHead>
                        <TableHead>Enrolment No</TableHead>
                        <TableHead>Mode</TableHead>
                        <TableHead>Seat Type</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Active Validation Flags & Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.students
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
                          <TableRow key={st.id}>
                            <TableCell>
                              <div className="font-bold ux4g-text-neutral-primary">{st.name}</div>
                              <div className="font-mono text-[11px] ux4g-text-neutral-secondary">{st.apaar_id}</div>
                            </TableCell>
                            <TableCell className="font-mono text-xs ux4g-text-neutral-primary">{st.enrolment_no}</TableCell>
                            <TableCell className="text-xs ux4g-text-neutral-secondary">{st.admission_mode}</TableCell>
                            <TableCell className="text-xs font-medium ux4g-text-neutral-primary">{st.seat_type}</TableCell>
                            <TableCell className="text-xs ux4g-text-neutral-secondary">{st.reservation_category}</TableCell>
                            <TableCell>
                              <span
                                className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border"
                                style={{
                                  backgroundColor:
                                    st.status === "valid" || st.status === "verified"
                                      ? "var(--ux4g-color-green-50)"
                                      : "var(--ux4g-color-orange-50)",
                                  color:
                                    st.status === "valid" || st.status === "verified"
                                      ? "var(--ux4g-color-green-900)"
                                      : "var(--ux4g-color-orange-900)",
                                  borderColor:
                                    st.status === "valid" || st.status === "verified"
                                      ? "var(--ux4g-color-green-300)"
                                      : "var(--ux4g-color-orange-300)",
                                }}
                              >
                                {st.status}
                              </span>
                            </TableCell>
                            <TableCell>
                              {st.flags && st.flags.length > 0 ? (
                                <div className="space-y-1.5">
                                  {st.flags.map((f) => (
                                    <div
                                      key={f.id}
                                      className="p-1.5 rounded-md border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-[11px] flex items-start justify-between gap-2"
                                    >
                                      <div>
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                          <FlagBadge level={f.level as any} label={f.rule_code} />
                                        </div>
                                        <p className="ux4g-text-neutral-secondary mt-0.5">{f.message}</p>
                                      </div>

                                      {f.status === "open" && (
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="text-[10px] py-0.5 px-1.5 h-6 shrink-0"
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
                                <span className="ux4g-text-neutral-secondary text-xs">No active flags</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </div>
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
