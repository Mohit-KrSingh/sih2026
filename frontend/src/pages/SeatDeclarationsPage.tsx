import React, { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import {
  getInstitutionSeatDeclarations,
  saveCourseSeatDeclaration,
  batchSaveSeatDeclarations,
  type CourseSummaryResponse,
  type InstitutionSeatDeclarationResponse,
  type ValidationFlagSummary,
} from "../api/seats";
import { Button } from "../components/ux4g/Button";
import { Input } from "../components/ux4g/Input";
import { FlagBadge } from "../components/ux4g/Badge";
import { Spinner } from "../components/ux4g/Spinner";
import { EmptyState } from "../components/ux4g/EmptyState";
import { Alert } from "../components/ux4g/Alert";
import { Card, CardBody } from "../components/ux4g/Card";
import { Icon } from "../components/ux4g/Icon";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ux4g/Table";

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
      <Card variant="outline" className="p-6">
        <CardBody className="p-0 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider ux4g-text-brand">
                College Data Entry • Step 1
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ux4g-bg-neutral-soft ux4g-text-neutral-secondary border ux4g-border-neutral-subtle">
                <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
                <span>AICTE Quota Protected</span>
              </span>
            </div>
            <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight mt-1">
              Seat Declarations & Course Summary
            </h1>
            <p className="text-xs ux4g-text-neutral-secondary mt-1">
              Declare admitted student numbers for academic year {academicYear}. AICTE approved quotas are read-only.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Academic Year Selector */}
            <div className="flex items-center gap-1.5 ux4g-bg-neutral-soft border ux4g-border-neutral-subtle rounded-lg px-2.5 py-1 text-xs">
              <span className="ux4g-text-neutral-secondary font-medium">Year:</span>
              <select
                aria-label="Academic Year"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="bg-transparent font-semibold ux4g-text-neutral-primary focus:outline-none cursor-pointer border-none"
              >
                <option value="2026-27">2026-27 (Current)</option>
                <option value="2025-26">2025-26 (Past Year)</option>
              </select>
            </div>

            {/* Autosave Status Indicator */}
            <div className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg ux4g-bg-neutral-soft border ux4g-border-neutral-subtle font-medium">
              {saveStatus === "saving" && (
                <span className="flex items-center gap-1 ux4g-text-brand animate-pulse">
                  <Icon name="sync" size="xs" color="primary" className="animate-spin" aria-hidden="true" />
                  <span>Saving draft...</span>
                </span>
              )}
              {saveStatus === "saved" && (
                <span className="flex items-center gap-1 ux4g-text-success">
                  <Icon name="check_circle" size="xs" color="success" aria-hidden="true" />
                  <span>Draft autosaved {lastSavedTime ? `at ${lastSavedTime}` : ""}</span>
                </span>
              )}
              {saveStatus === "error" && (
                <span className="flex items-center gap-1 ux4g-text-error">
                  <Icon name="error" size="xs" color="error" aria-hidden="true" />
                  <span>Save failed</span>
                </span>
              )}
              {saveStatus === "idle" && (
                <span className="ux4g-text-neutral-secondary">Autosave ready</span>
              )}
            </div>

            {/* Request a correction link (R07 requirement) */}
            <Link
              to="/college/change-requests"
              className="ux4g-btn ux4g-btn-outline-primary ux4g-btn-s inline-flex items-center gap-1 text-xs"
            >
              <Icon name="edit_note" size="xs" color="inherit" aria-hidden="true" />
              <span>Request a correction</span>
            </Link>

            {/* Save draft button */}
            {!isReadOnly && (
              <Button
                size="sm"
                variant="primary"
                onClick={handleSaveAll}
                disabled={saveStatus === "saving" || isLoading}
                leftIcon={<Icon name="save" size="xs" color="inherit" aria-hidden="true" />}
              >
                Save draft
              </Button>
            )}

            <Button
              size="sm"
              variant="outline"
              onClick={fetchData}
              disabled={isLoading}
              leftIcon={<Icon name="refresh" size="xs" color="inherit" className={isLoading ? "animate-spin" : ""} aria-hidden="true" />}
            >
              Refresh
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Aggregate Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Metric 1: Approved Intake (Lock & Set by AICTE) */}
        <Card variant="outline" className="p-4 space-y-1">
          <CardBody className="p-0">
            <div className="flex items-center justify-between">
              <span className="text-xs ux4g-text-neutral-secondary font-medium">Approved Intake</span>
              <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold ux4g-text-neutral-secondary">
                <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
                <span>Set by AICTE</span>
              </span>
            </div>
            <p className="text-2xl font-bold ux4g-text-neutral-primary mt-1">{totalApproved}</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">Regular seats • AICTE owned</p>
          </CardBody>
        </Card>

        {/* Metric 2: Supernumerary Quota (Lock & Set by AICTE) */}
        <Card variant="outline" className="p-4 space-y-1">
          <CardBody className="p-0">
            <div className="flex items-center justify-between">
              <span className="text-xs ux4g-text-neutral-secondary font-medium">Supernumerary Quota</span>
              <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold ux4g-text-neutral-secondary">
                <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
                <span>Set by AICTE</span>
              </span>
            </div>
            <p className="text-2xl font-bold ux4g-text-neutral-primary mt-1">{totalSuperAllowed}</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">Allowed additional seats</p>
          </CardBody>
        </Card>

        {/* Metric 3: Total Declared */}
        <Card variant="outline" className="p-4 space-y-1">
          <CardBody className="p-0">
            <div className="flex items-center justify-between">
              <span className="text-xs ux4g-text-neutral-secondary font-medium">Total Declared</span>
              <Icon name="group" size="sm" color="primary" aria-hidden="true" />
            </div>
            <p className="text-2xl font-bold ux4g-text-brand mt-1">{totalDeclared}</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">
              {totalDeclaredRegular} regular + {totalDeclaredSuper} super
            </p>
          </CardBody>
        </Card>

        {/* Metric 4: Uploaded Enrolment */}
        <Card variant="outline" className="p-4 space-y-1">
          <CardBody className="p-0">
            <div className="flex items-center justify-between">
              <span className="text-xs ux4g-text-neutral-secondary font-medium">Uploaded Enrolment</span>
              <Icon name="domain" size="sm" color="inherit" aria-hidden="true" />
            </div>
            <p className="text-2xl font-bold ux4g-text-neutral-primary mt-1">{totalEnrolled}</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">Actual students in records</p>
          </CardBody>
        </Card>

        {/* Metric 5: Quota Compliance */}
        <Card variant="outline" className="p-4 space-y-1">
          <CardBody className="p-0">
            <span className="text-xs ux4g-text-neutral-secondary font-medium">Quota Compliance</span>
            <div className="pt-1">
              {coursesOverIntake > 0 ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ux4g-bg-error-soft ux4g-text-error border ux4g-border-error">
                  <Icon name="warning" size="xs" color="error" aria-hidden="true" />
                  <span>
                    {coursesOverIntake} {coursesOverIntake === 1 ? "course" : "courses"} over intake
                  </span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ux4g-bg-success-soft ux4g-text-success border ux4g-border-success">
                  <Icon name="check_circle" size="xs" color="success" aria-hidden="true" />
                  <span>All courses within limits</span>
                </span>
              )}
            </div>
            <p className="text-[11px] ux4g-text-neutral-secondary mt-1">
              {coursesData.length} approved courses total
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Info notice about AICTE ownership, draft autosave, and Request a correction */}
      <Alert variant="info" title="Automated draft persistence and AICTE data ownership">
        <p className="leading-relaxed">
          Approved intake and supernumerary quotas are owned strictly by AICTE (marked with a lock icon and "Set by AICTE"). Seat declarations are autosaved as drafts as you type. If an approved intake number is incorrect, you can{" "}
          <Link
            to="/college/change-requests"
            className="underline font-semibold ux4g-text-brand hover:opacity-80"
          >
            Request a correction
          </Link>
          .
        </p>
      </Alert>

      {/* Main Table Card */}
      <Card variant="outline" className="overflow-hidden">
        <div className="p-4 border-b ux4g-border-neutral-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="domain" size="sm" color="primary" aria-hidden="true" />
            <h2 className="font-bold ux4g-text-neutral-primary text-sm">
              Course intake and seat declaration table
            </h2>
          </div>
          <span className="text-xs ux4g-text-neutral-secondary">
            {coursesData.length} Approved Courses
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 flex flex-col justify-center items-center gap-3">
            <Spinner size="lg" />
            <p className="text-xs ux4g-text-neutral-secondary">Loading approved courses and seat declarations...</p>
          </div>
        ) : error ? (
          <div className="p-6">
            <Alert variant="error" title="Failed to load course data">
              <p>{error}</p>
              <div className="mt-3">
                <Button size="sm" variant="outline" onClick={fetchData}>
                  Retry
                </Button>
              </div>
            </Alert>
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
                  <TableHead className="text-center w-36">
                    <span className="inline-flex items-center gap-1">
                      <span>Approved</span>
                      <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
                    </span>
                  </TableHead>
                  <TableHead className="text-center w-36">
                    <span className="inline-flex items-center gap-1">
                      <span>Super. Allowed</span>
                      <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
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
                            ? "ux4g-bg-error-soft"
                            : undefined
                        }
                      >
                        {/* Course Name & Branch */}
                        <TableCell>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold ux4g-text-neutral-primary text-sm">
                                {row.course_name}
                              </span>
                              <span className="px-1.5 py-0.5 ux4g-bg-neutral-soft ux4g-text-neutral-secondary text-[10px] font-semibold rounded border ux4g-border-neutral-subtle">
                                {row.level}
                              </span>
                            </div>
                            <p className="text-xs ux4g-text-neutral-secondary mt-0.5">
                              Branch: <span className="font-medium ux4g-text-neutral-primary">{row.branch}</span> • {row.duration_years} Years
                            </p>
                          </div>
                        </TableCell>

                        {/* Approved Regular Intake (AICTE Read-only + Lock + Set by AICTE) */}
                        <TableCell className="text-center">
                          <div className="inline-flex flex-col items-center">
                            <span
                              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded ux4g-bg-neutral-soft border ux4g-border-neutral-subtle font-mono text-sm font-semibold ux4g-text-neutral-primary"
                              title="AICTE approved intake (Read-only)"
                            >
                              <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
                              <span>{row.approved_intake}</span>
                            </span>
                            <span className="text-[10px] font-medium ux4g-text-neutral-secondary mt-0.5">
                              Set by AICTE
                            </span>
                          </div>
                        </TableCell>

                        {/* Supernumerary Seats Allowed (AICTE Read-only + Lock + Set by AICTE) */}
                        <TableCell className="text-center">
                          <div className="inline-flex flex-col items-center">
                            <span
                              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded ux4g-bg-neutral-soft border ux4g-border-neutral-subtle font-mono text-xs font-semibold ux4g-text-neutral-primary"
                              title="Allowed supernumerary seats (Read-only)"
                            >
                              <Icon name="lock" size="xs" color="inherit" aria-hidden="true" />
                              <span>{row.supernumerary_seats_allowed}</span>
                            </span>
                            <span className="text-[10px] font-medium ux4g-text-neutral-secondary mt-0.5">
                              Set by AICTE
                            </span>
                          </div>
                        </TableCell>

                        {/* Uploaded / Calculated Enrolment */}
                        <TableCell className="text-center">
                          <span
                            className={`font-mono text-xs font-semibold ${
                              row.calculated_enrolment > 0
                                ? "ux4g-text-brand"
                                : "ux4g-text-neutral-secondary"
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
                              state={isOverIntake ? "error" : "default"}
                              aria-label={`Regular admitted count for ${row.course_name}`}
                              onChange={(e) =>
                                handleFieldChange(
                                  row.course_id,
                                  "regular_admitted",
                                  parseInt(e.target.value, 10) || 0
                                )
                              }
                              className="h-8 font-mono text-sm"
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
                            state={isSuperExceeded ? "warning" : "default"}
                            aria-label={`Supernumerary admitted count for ${row.course_name}`}
                            onChange={(e) =>
                              handleFieldChange(
                                row.course_id,
                                "supernumerary_admitted",
                                parseInt(e.target.value, 10) || 0
                              )
                            }
                            className="h-8 font-mono text-sm"
                          />
                        </TableCell>

                        {/* Total Declared */}
                        <TableCell className="text-center">
                          <span className="font-mono text-sm font-bold ux4g-text-neutral-primary">
                            {totalDecl}
                          </span>
                        </TableCell>

                        {/* Status Badge & Level Badges */}
                        <TableCell className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            {isOverIntake ? (
                              <span
                                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ux4g-bg-error-soft ux4g-text-error border ux4g-border-error"
                                data-testid={`status-badge-over-${row.course_id}`}
                              >
                                <Icon name="warning" size="xs" color="error" aria-hidden="true" />
                                <span>Over by {overshoot}</span>
                              </span>
                            ) : (
                              <span
                                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ux4g-bg-success-soft ux4g-text-success border ux4g-border-success"
                                data-testid={`status-badge-within-${row.course_id}`}
                              >
                                <Icon name="check_circle" size="xs" color="success" aria-hidden="true" />
                                <span>Within limit</span>
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
                            className="p-1 h-7 w-7 rounded-full inline-flex items-center justify-center"
                            aria-label={`Toggle category counts for ${row.course_name}`}
                            title="Toggle Category Counts (NRI, OCI, Foreign National)"
                          >
                            <Icon
                              name={row.isExpanded ? "expand_less" : "expand_more"}
                              size="xs"
                              color="inherit"
                              aria-hidden="true"
                            />
                          </Button>
                        </TableCell>
                      </TableRow>

                      {/* Expandable Category details or Flag Messages */}
                      {(row.isExpanded || row.flags.length > 0) && (
                        <TableRow className="ux4g-bg-neutral-soft border-t ux4g-border-neutral-subtle">
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
                                          ? "ux4g-bg-error-soft ux4g-border-error ux4g-text-error"
                                          : fl.level === "exception"
                                          ? "ux4g-bg-error-soft ux4g-border-error ux4g-text-error"
                                          : "ux4g-bg-warning-soft ux4g-border-warning ux4g-text-warning"
                                      }`}
                                    >
                                      <Icon name="warning" size="xs" color="inherit" className="mt-0.5 shrink-0" aria-hidden="true" />
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
                                <div className="flex items-center justify-between mb-2">
                                  <p className="text-xs font-semibold ux4g-text-neutral-primary">
                                    Special Category Admissions Breakdown:
                                  </p>
                                  <Link
                                    to="/college/change-requests"
                                    className="text-xs ux4g-text-brand font-medium underline hover:opacity-80"
                                  >
                                    Request a correction
                                  </Link>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                  <div>
                                    <label
                                      htmlFor={`nri-${row.course_id}`}
                                      className="text-[11px] ux4g-text-neutral-secondary font-medium block mb-1"
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
                                      className="text-[11px] ux4g-text-neutral-secondary font-medium block mb-1"
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
                                      className="text-[11px] ux4g-text-neutral-secondary font-medium block mb-1"
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
      </Card>
    </div>
  );
}

export default SeatDeclarationsPage;
