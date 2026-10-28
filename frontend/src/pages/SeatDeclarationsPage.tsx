import React, { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  getInstitutionSeatDeclarations,
  saveCourseSeatDeclaration,
  batchSaveSeatDeclarations,
  type CourseSummaryResponse,
  type InstitutionSeatDeclarationResponse,
  type ValidationFlagSummary,
} from "../api/seats";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { FlagBadge } from "../components/ui/Badge";
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
  AlertCircle,
  AlertTriangle,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  Lock,
  RefreshCw,
  Save,
  Users,
} from "lucide-react";

interface FormCourseRow {
  course_id: number;
  course_name: string;
  branch: string;
  level: string;
  duration_years: number;
  approved_intake: number;
  supernumerary_seats_allowed: number;
  regular_admitted: number;
  supernumerary_admitted: number;
  nri_count: number;
  oci_count: number;
  fn_count: number;
  calculated_enrolment: number;
  calculated_regular: number;
  calculated_supernumerary: number;
  status: string;
  flags: ValidationFlagSummary[];
  isExpanded?: boolean;
}

export function SeatDeclarationsPage() {
  useDocumentTitle("Seat Declarations & Intake Quotas");
  const { user } = useAuth();
  const institutionId = user?.institution_id;
  const isReadOnly = user?.role === "college_viewer";

  const [academicYear, setAcademicYear] = useState("2026-27");
  const [coursesData, setCoursesData] = useState<FormCourseRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Autosave status state
  const [saveStatus, setSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [lastSavedTime, setLastSavedTime] = useState<string | null>(null);

  // Debounce timers per course
  const debounceTimers = useRef<Record<number, NodeJS.Timeout>>({});

  // 1. Fetch data
  const fetchData = useCallback(async () => {
    if (!institutionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const resp: InstitutionSeatDeclarationResponse =
        await getInstitutionSeatDeclarations(institutionId, academicYear);
      setCoursesData(
        resp.courses.map((c: CourseSummaryResponse) => ({
          course_id: c.course_id,
          course_name: c.course_name,
          branch: c.branch,
          level: c.level,
          duration_years: c.duration_years,
          approved_intake: c.approved_intake,
          supernumerary_seats_allowed: c.supernumerary_seats_allowed,
          regular_admitted: c.regular_admitted,
          supernumerary_admitted: c.supernumerary_admitted,
          nri_count: c.nri_count,
          oci_count: c.oci_count,
          fn_count: c.fn_count,
          calculated_enrolment: c.calculated_enrolment,
          calculated_regular: c.calculated_regular,
          calculated_supernumerary: c.calculated_supernumerary,
          status: c.status,
          flags: c.flags,
          isExpanded: false,
        }))
      );
      setSaveStatus("idle");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load seat declarations";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [institutionId, academicYear]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Clean up timers on unmount
  useEffect(() => {
    const timers = debounceTimers.current;
    return () => {
      Object.values(timers).forEach((t) => clearTimeout(t));
    };
  }, []);

  // 2. Client-side live validation helper
  const computeLiveFlags = (row: FormCourseRow): ValidationFlagSummary[] => {
    const flags: ValidationFlagSummary[] = [];

    // Negative check
    if (
      row.regular_admitted < 0 ||
      row.supernumerary_admitted < 0 ||
      row.nri_count < 0 ||
      row.oci_count < 0 ||
      row.fn_count < 0
    ) {
      flags.push({
        rule_code: "SEAT_DECLARATION_INVALID",
        level: "error",
        message: "Seat declaration counts cannot be negative numbers.",
        fix_hint: "Enter zero or positive integers for all seat counts.",
        field: "regular_admitted",
      });
    }

    // Category sum check
    const totalDecl = row.regular_admitted + row.supernumerary_admitted;
    const catTotal = row.nri_count + row.oci_count + row.fn_count;
    if (catTotal > totalDecl && totalDecl >= 0) {
      flags.push({
        rule_code: "SEAT_DECLARATION_INVALID",
        level: "error",
        message: `Total category admissions (${catTotal}) exceed total declared seats (${totalDecl}).`,
        fix_hint: "Ensure sum of NRI, OCI, and Foreign National counts does not exceed total seats.",
        field: "nri_count",
      });
    }

    // Regular quota overshoot check (INTAKE_EXCEEDED)
    if (row.regular_admitted > row.approved_intake) {
      const overshoot = row.regular_admitted - row.approved_intake;
      flags.push({
        rule_code: "INTAKE_EXCEEDED",
        level: "exception",
        message: `Regular admitted students (${row.regular_admitted}) exceed approved intake (${row.approved_intake}) by ${overshoot}.`,
        fix_hint: "Submit a justification for over-intake admissions before final submission.",
        field: "regular_admitted",
      });
    }

    // Supernumerary quota overshoot check (SUPERNUMERARY_EXCEEDED)
    if (row.supernumerary_admitted > row.supernumerary_seats_allowed) {
      const supOvershoot = row.supernumerary_admitted - row.supernumerary_seats_allowed;
      flags.push({
        rule_code: "SUPERNUMERARY_EXCEEDED",
        level: "exception",
        message: `Supernumerary admitted (${row.supernumerary_admitted}) exceeds allowed quota (${row.supernumerary_seats_allowed}) by ${supOvershoot}.`,
        fix_hint: "Reduce supernumerary admitted count or submit a justification.",
        field: "supernumerary_admitted",
      });
    }

    // Uploaded records mismatch check (SEAT_DECLARATION_MISMATCH)
    if (row.calculated_enrolment > 0) {
      if (
        row.regular_admitted !== row.calculated_regular ||
        row.supernumerary_admitted !== row.calculated_supernumerary
      ) {
        flags.push({
          rule_code: "SEAT_DECLARATION_MISMATCH",
          level: "error",
          message: `Declared seats (${row.regular_admitted} regular, ${row.supernumerary_admitted} supernumerary) differ from uploaded student records (${row.calculated_regular} regular, ${row.calculated_supernumerary} supernumerary).`,
          fix_hint: "Align declared counts with your uploaded student records.",
          field: "regular_admitted",
        });
      }
    }

    return flags;
  };

  // 3. Trigger debounced autosave
  const triggerAutosave = (updatedRow: FormCourseRow) => {
    if (!institutionId || isReadOnly) return;

    if (debounceTimers.current[updatedRow.course_id]) {
      clearTimeout(debounceTimers.current[updatedRow.course_id]);
    }

    setSaveStatus("saving");

    debounceTimers.current[updatedRow.course_id] = setTimeout(async () => {
      try {
        const resp = await saveCourseSeatDeclaration(
          institutionId,
          updatedRow.course_id,
          {
            academic_year: academicYear,
            regular_admitted: updatedRow.regular_admitted,
            supernumerary_admitted: updatedRow.supernumerary_admitted,
            nri_count: updatedRow.nri_count,
            oci_count: updatedRow.oci_count,
            fn_count: updatedRow.fn_count,
            status: "draft",
          }
        );

        // Update row with backend resolved flags
        setCoursesData((prev) =>
          prev.map((c) =>
            c.course_id === updatedRow.course_id
              ? {
                  ...c,
                  flags: resp.flags,
                  status: resp.status,
                }
              : c
          )
        );

        setSaveStatus("saved");
        setLastSavedTime(new Date().toLocaleTimeString());
      } catch (err) {
        console.error("Autosave error:", err);
        setSaveStatus("error");
      }
    }, 600);
  };

  // 4. Handle field updates with immediate live validation
  const handleFieldChange = (
    courseId: number,
    field:
      | "regular_admitted"
      | "supernumerary_admitted"
      | "nri_count"
      | "oci_count"
      | "fn_count",
    value: number
  ) => {
    setCoursesData((prev) =>
      prev.map((row) => {
        if (row.course_id !== courseId) return row;
        const updatedRow: FormCourseRow = {
          ...row,
          [field]: value,
        };
        // Compute live client-side flags immediately
        updatedRow.flags = computeLiveFlags(updatedRow);
        // Trigger background draft autosave
        triggerAutosave(updatedRow);
        return updatedRow;
      })
    );
  };

  // 5. Manual save all
  const handleSaveAll = async () => {
    if (!institutionId || isReadOnly) return;
    setSaveStatus("saving");
    try {
      const payload = {
        academic_year: academicYear,
        declarations: coursesData.map((c) => ({
          course_id: c.course_id,
          regular_admitted: c.regular_admitted,
          supernumerary_admitted: c.supernumerary_admitted,
          nri_count: c.nri_count,
          oci_count: c.oci_count,
          fn_count: c.fn_count,
          status: "draft" as const,
        })),
      };
      const resp = await batchSaveSeatDeclarations(institutionId, payload);
      setCoursesData(
        resp.courses.map((c) => ({
          course_id: c.course_id,
          course_name: c.course_name,
          branch: c.branch,
          level: c.level,
          duration_years: c.duration_years,
          approved_intake: c.approved_intake,
          supernumerary_seats_allowed: c.supernumerary_seats_allowed,
          regular_admitted: c.regular_admitted,
          supernumerary_admitted: c.supernumerary_admitted,
          nri_count: c.nri_count,
          oci_count: c.oci_count,
          fn_count: c.fn_count,
          calculated_enrolment: c.calculated_enrolment,
          calculated_regular: c.calculated_regular,
          calculated_supernumerary: c.calculated_supernumerary,
          status: c.status,
          flags: c.flags,
          isExpanded: false,
        }))
      );
      setSaveStatus("saved");
      setLastSavedTime(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      console.error("Batch save error:", err);
      setSaveStatus("error");
    }
  };

  const toggleExpand = (courseId: number) => {
    setCoursesData((prev) =>
      prev.map((c) =>
        c.course_id === courseId ? { ...c, isExpanded: !c.isExpanded } : c
      )
    );
  };

  // Aggregate stats
  const totalApproved = coursesData.reduce((sum, c) => sum + c.approved_intake, 0);
  const totalSuperAllowed = coursesData.reduce(
    (sum, c) => sum + c.supernumerary_seats_allowed,
    0
  );
  const totalDeclaredRegular = coursesData.reduce(
    (sum, c) => sum + (c.regular_admitted || 0),
    0
  );
  const totalDeclaredSuper = coursesData.reduce(
    (sum, c) => sum + (c.supernumerary_admitted || 0),
    0
  );
  const totalDeclared = totalDeclaredRegular + totalDeclaredSuper;
  const totalEnrolled = coursesData.reduce(
    (sum, c) => sum + c.calculated_enrolment,
    0
  );

  const coursesOverIntake = coursesData.filter(
    (c) => c.regular_admitted > c.approved_intake
  ).length;

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
              College Data Entry &bull; Step 1
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700">
              <Lock className="w-3 h-3 text-slate-400" /> AICTE Quota Protected
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            Seat Declarations & Course Summary
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Declare admitted student numbers for academic year {academicYear}. AICTE approved quotas are read-only.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Academic Year Selector */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs">
            <span className="text-slate-500 font-medium">Year:</span>
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold text-slate-900 focus:outline-none cursor-pointer"
            >
              <option value="2026-27">2026-27 (Current)</option>
              <option value="2025-26">2025-26 (Past Year)</option>
            </select>
          </div>

          {/* Autosave Status Indicator */}
          <div className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 font-medium">
            {saveStatus === "saving" && (
              <span className="flex items-center gap-1 text-blue-600 animate-pulse">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Saving draft...
              </span>
            )}
            {saveStatus === "saved" && (
              <span className="flex items-center gap-1 text-emerald-600">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Draft autosaved {lastSavedTime ? `at ${lastSavedTime}` : ""}
              </span>
            )}
            {saveStatus === "error" && (
              <span className="flex items-center gap-1 text-red-600">
                <AlertCircle className="w-3.5 h-3.5" /> Save failed
              </span>
            )}
            {saveStatus === "idle" && (
              <span className="text-slate-500">Autosave ready</span>
            )}
          </div>

          {/* Save All button */}
          {!isReadOnly && (
            <Button
              size="sm"
              variant="primary"
              onClick={handleSaveAll}
              disabled={saveStatus === "saving" || isLoading}
              leftIcon={<Save className="w-4 h-4" />}
            >
              Save draft
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={fetchData}
            disabled={isLoading}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Aggregate Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Approved Intake</span>
            <Lock className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900">{totalApproved}</p>
          <p className="text-[11px] text-slate-400">Regular seats &bull; AICTE owned</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Supernumerary Quota</span>
            <Lock className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900">{totalSuperAllowed}</p>
          <p className="text-[11px] text-slate-400">Allowed additional seats</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Total Declared</span>
            <Users className="w-3.5 h-3.5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-blue-700">{totalDeclared}</p>
          <p className="text-[11px] text-slate-400">
            {totalDeclaredRegular} regular + {totalDeclaredSuper} super
          </p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Uploaded Enrolment</span>
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900">{totalEnrolled}</p>
          <p className="text-[11px] text-slate-400">Actual students in records</p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm">
          <span className="text-xs text-slate-500">Quota Compliance</span>
          <div className="pt-1">
            {coursesOverIntake > 0 ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
                <AlertTriangle className="w-3 h-3 text-red-600" />
                {coursesOverIntake} {coursesOverIntake === 1 ? "course" : "courses"} over intake
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                All courses within limits
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {coursesData.length} approved courses total
          </p>
        </div>
      </div>

      {/* Info notice about AICTE ownership & draft autosave */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3 text-xs text-blue-900 shadow-sm">
        <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="space-y-1">
          <p className="font-semibold text-blue-950">
            Automated Draft Persistence & AICTE Data Ownership
          </p>
          <p className="text-blue-800 leading-relaxed">
            Approved intake and supernumerary quotas are owned strictly by AICTE (marked with a lock icon). Seat declarations are autosaved as drafts as you type. If you enter values that exceed approved intake, the system flags the overshoot immediately but preserves your draft so you can provide justifications during final submission.
          </p>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            <h2 className="font-bold text-slate-900 text-sm">
              Course Intake & Seat Declaration Table
            </h2>
          </div>
          <span className="text-xs text-slate-500">
            {coursesData.length} Approved Courses
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 flex justify-center items-center">
            <LoadingSpinner size="lg" label="Loading approved courses and seat declarations..." />
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState title="Failed to load course data" message={error} onRetry={fetchData} />
          </div>
        ) : coursesData.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No courses found"
              description="No AICTE-approved courses are registered for this institution."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/4">Course & Branch</TableHead>
                  <TableHead className="text-center w-28">
                    <span className="inline-flex items-center gap-1">
                      Approved <Lock className="w-3 h-3 text-slate-400" />
                    </span>
                  </TableHead>
                  <TableHead className="text-center w-28">
                    <span className="inline-flex items-center gap-1">
                      Super. Allowed <Lock className="w-3 h-3 text-slate-400" />
                    </span>
                  </TableHead>
                  <TableHead className="text-center w-24">Enrolled</TableHead>
                  <TableHead className="w-32">Regular Admitted</TableHead>
                  <TableHead className="w-32">Supernumerary</TableHead>
                  <TableHead className="text-center w-24">Total Declared</TableHead>
                  <TableHead className="w-44 text-center">Status & Badges</TableHead>
                  <TableHead className="w-16 text-center">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {coursesData.map((row) => {
                  const isOverIntake = row.regular_admitted > row.approved_intake;
                  const overshoot = Math.max(0, row.regular_admitted - row.approved_intake);
                  const isSuperExceeded =
                    row.supernumerary_admitted > row.supernumerary_seats_allowed;
                  const totalDecl = row.regular_admitted + row.supernumerary_admitted;

                  return (
                    <React.Fragment key={row.course_id}>
                      <TableRow
                        className={
                          isOverIntake
                            ? "bg-red-50/40 hover:bg-red-50/70"
                            : "hover:bg-slate-50/70"
                        }
                      >
                        {/* Course Name & Branch */}
                        <TableCell>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-slate-900 text-sm">
                                {row.course_name}
                              </span>
                              <span className="px-1.5 py-0.2 bg-slate-100 text-slate-700 text-[10px] font-semibold rounded">
                                {row.level}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5">
                              Branch: <span className="font-medium text-slate-700">{row.branch}</span> &bull; {row.duration_years} Years
                            </p>
                          </div>
                        </TableCell>

                        {/* Approved Regular Intake (AICTE Read-only) */}
                        <TableCell className="text-center">
                          <span
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 font-mono text-sm font-semibold text-slate-800"
                            title="AICTE approved intake (Read-only)"
                          >
                            <Lock className="w-3 h-3 text-slate-400" />
                            {row.approved_intake}
                          </span>
                        </TableCell>

                        {/* Supernumerary Seats Allowed (AICTE Read-only) */}
                        <TableCell className="text-center">
                          <span
                            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-100 border border-slate-200 font-mono text-xs font-medium text-slate-700"
                            title="Allowed supernumerary seats (Read-only)"
                          >
                            <Lock className="w-3 h-3 text-slate-400" />
                            {row.supernumerary_seats_allowed}
                          </span>
                        </TableCell>

                        {/* Uploaded / Calculated Enrolment */}
                        <TableCell className="text-center">
                          <span
                            className={`font-mono text-xs font-semibold ${
                              row.calculated_enrolment > 0
                                ? "text-blue-700"
                                : "text-slate-400"
                            }`}
                            title={`Records: ${row.calculated_regular} Regular, ${row.calculated_supernumerary} Supernumerary`}
                          >
                            {row.calculated_enrolment}
                          </span>
                        </TableCell>

                        {/* Regular Admitted Input (Editable by College) */}
                        <TableCell>
                          <div className="space-y-1">
                            <Input
                              type="number"
                              min={0}
                              disabled={isReadOnly}
                              value={row.regular_admitted}
                              onChange={(e) =>
                                handleFieldChange(
                                  row.course_id,
                                  "regular_admitted",
                                  parseInt(e.target.value, 10) || 0
                                )
                              }
                              className={`h-8 font-mono text-sm ${
                                isOverIntake
                                  ? "border-red-400 focus:ring-red-300 text-red-900 bg-red-50/50"
                                  : ""
                              }`}
                            />
                          </div>
                        </TableCell>

                        {/* Supernumerary Admitted Input */}
                        <TableCell>
                          <Input
                            type="number"
                            min={0}
                            disabled={isReadOnly}
                            value={row.supernumerary_admitted}
                            onChange={(e) =>
                              handleFieldChange(
                                row.course_id,
                                "supernumerary_admitted",
                                parseInt(e.target.value, 10) || 0
                              )
                            }
                            className={`h-8 font-mono text-sm ${
                              isSuperExceeded
                                ? "border-amber-400 focus:ring-amber-300 text-amber-900 bg-amber-50/50"
                                : ""
                            }`}
                          />
                        </TableCell>

                        {/* Total Declared */}
                        <TableCell className="text-center">
                          <span className="font-mono text-sm font-bold text-slate-900">
                            {totalDecl}
                          </span>
                        </TableCell>

                        {/* Status Badge & Level Badges */}
                        <TableCell className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            {isOverIntake ? (
                              <span
                                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-300"
                                data-testid={`status-badge-over-${row.course_id}`}
                              >
                                <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                                Over by {overshoot}
                              </span>
                            ) : (
                              <span
                                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300"
                                data-testid={`status-badge-within-${row.course_id}`}
                              >
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                Within limit
                              </span>
                            )}

                            {/* Additional Flag indicator if any */}
                            {row.flags.length > 0 && (
                              <div className="flex flex-wrap gap-1 justify-center mt-0.5">
                                {row.flags.map((f, i) => (
                                  <FlagBadge
                                    key={i}
                                    level={f.level}
                                    label={f.rule_code}
                                    title={f.message}
                                    className="scale-90"
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        </TableCell>

                        {/* Expand Details (Categories) */}
                        <TableCell className="text-center">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => toggleExpand(row.course_id)}
                            className="p-1 h-7 w-7 rounded-full"
                            title="Toggle Category Counts (NRI, OCI, Foreign National)"
                          >
                            {row.isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>

                      {/* Expandable Category details or Flag Messages */}
                      {(row.isExpanded || row.flags.length > 0) && (
                        <TableRow className="bg-slate-50/80 border-t border-slate-100">
                          <TableCell colSpan={9} className="p-4">
                            <div className="space-y-3">
                              {/* Validation Flag Hints */}
                              {row.flags.length > 0 && (
                                <div className="space-y-2">
                                  {row.flags.map((fl, idx) => (
                                    <div
                                      key={idx}
                                      className={`p-2.5 rounded-lg border text-xs flex items-start gap-2 ${
                                        fl.level === "error"
                                          ? "bg-red-50 border-red-200 text-red-900"
                                          : fl.level === "exception"
                                          ? "bg-red-50/70 border-red-300 text-red-900"
                                          : "bg-amber-50 border-amber-200 text-amber-900"
                                      }`}
                                    >
                                      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                                      <div className="space-y-0.5">
                                        <p className="font-semibold">
                                          [{fl.rule_code}] {fl.message}
                                        </p>
                                        {fl.fix_hint && (
                                          <p className="text-[11px] opacity-90">
                                            Fix: {fl.fix_hint}
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Category Quota Breakdown Inputs */}
                              <div className="pt-1">
                                <p className="text-xs font-semibold text-slate-700 mb-2">
                                  Special Category Admissions Breakdown:
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                  <div>
                                    <label
                                      htmlFor={`nri-${row.course_id}`}
                                      className="text-[11px] text-slate-500 font-medium block mb-1"
                                    >
                                      NRI Count:
                                    </label>
                                    <Input
                                      id={`nri-${row.course_id}`}
                                      type="number"
                                      min={0}
                                      disabled={isReadOnly}
                                      value={row.nri_count}
                                      onChange={(e) =>
                                        handleFieldChange(
                                          row.course_id,
                                          "nri_count",
                                          parseInt(e.target.value, 10) || 0
                                        )
                                      }
                                      className="h-8 font-mono text-xs"
                                    />
                                  </div>

                                  <div>
                                    <label
                                      htmlFor={`oci-${row.course_id}`}
                                      className="text-[11px] text-slate-500 font-medium block mb-1"
                                    >
                                      OCI Count:
                                    </label>
                                    <Input
                                      id={`oci-${row.course_id}`}
                                      type="number"
                                      min={0}
                                      disabled={isReadOnly}
                                      value={row.oci_count}
                                      onChange={(e) =>
                                        handleFieldChange(
                                          row.course_id,
                                          "oci_count",
                                          parseInt(e.target.value, 10) || 0
                                        )
                                      }
                                      className="h-8 font-mono text-xs"
                                    />
                                  </div>

                                  <div>
                                    <label
                                      htmlFor={`fn-${row.course_id}`}
                                      className="text-[11px] text-slate-500 font-medium block mb-1"
                                    >
                                      Foreign National Count:
                                    </label>
                                    <Input
                                      id={`fn-${row.course_id}`}
                                      type="number"
                                      min={0}
                                      disabled={isReadOnly}
                                      value={row.fn_count}
                                      onChange={(e) =>
                                        handleFieldChange(
                                          row.course_id,
                                          "fn_count",
                                          parseInt(e.target.value, 10) || 0
                                        )
                                      }
                                      className="h-8 font-mono text-xs"
                                    />
                                  </div>
                                </div>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
