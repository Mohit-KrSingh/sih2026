import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { listCourses, type CourseResponse } from "../api/institutions";
import {
  createStudent,
  getStudent,
  updateStudent,
  type StudentCreateRequest,
  type StudentResponse,
  type StudentSaveResultResponse,
  type StudentValidationFlag,
} from "../api/students";
import { useAuth } from "../auth/AuthContext";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/ErrorState";
import { Input } from "../components/ui/Input";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

const GENDER_OPTIONS = [
  { value: "Male", label: "Male" },
  { value: "Female", label: "Female" },
  { value: "Other", label: "Other" },
];

const ADMISSION_MODE_OPTIONS = [
  { value: "State counselling", label: "State counselling" },
  { value: "JEE Main counselling", label: "JEE Main counselling" },
  { value: "Management quota", label: "Management quota" },
  { value: "Direct second year", label: "Direct second year" },
  { value: "NRI/OCI/foreign quota", label: "NRI/OCI/foreign quota" },
  { value: "Other", label: "Other" },
];

const SEAT_TYPE_OPTIONS = [
  { value: "Regular", label: "Regular" },
  { value: "Supernumerary", label: "Supernumerary" },
];

const RESERVATION_OPTIONS = [
  { value: "General", label: "General" },
  { value: "OBC", label: "OBC" },
  { value: "SC", label: "SC" },
  { value: "ST", label: "ST" },
  { value: "EWS", label: "EWS" },
];

const YES_NO_OPTIONS = [
  { value: "No", label: "No" },
  { value: "Yes", label: "Yes" },
];

export const StudentFormPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const isEditMode = Boolean(id);
  const studentId = id ? parseInt(id, 10) : undefined;

  useDocumentTitle(isEditMode ? "Edit Student Record" : "New Student Admission");

  const institutionId = user?.institution_id ?? 1;
  const isViewer = user?.role === "college_viewer";

  // Form State
  const [apaarId, setApaarId] = useState("");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [gender, setGender] = useState("Male");

  const [courseId, setCourseId] = useState<number | "">("");
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [enrolmentNo, setEnrolmentNo] = useState("");
  const [admissionDate, setAdmissionDate] = useState("");
  const [admissionMode, setAdmissionMode] = useState("State counselling");
  const [seatType, setSeatType] = useState("Regular");

  const [reservationCategory, setReservationCategory] = useState("General");
  const [nri, setNri] = useState("No");
  const [oci, setOci] = useState("No");
  const [foreignNational, setForeignNational] = useState("No");
  const [country, setCountry] = useState("");

  // Metadata & Options
  const [courses, setCourses] = useState<CourseResponse[]>([]);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Result from "Check and save"
  const [saveResult, setSaveResult] = useState<StudentSaveResultResponse | null>(null);
  const [savedStudent, setSavedStudent] = useState<StudentResponse | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        setLoadingInitial(true);
        setErrorMessage(null);

        const courseList = await listCourses(institutionId);
        if (isMounted) {
          setCourses(courseList);
          if (courseList.length > 0) {
            setCourseId((prev) => (prev !== "" ? prev : courseList[0].id));
          }
        }

        if (isEditMode && studentId) {
          const student = await getStudent(institutionId, studentId);
          if (isMounted) {
            setSavedStudent(student);
            setApaarId(student.apaar_id);
            setName(student.name);
            setDob(student.dob);
            setGender(student.gender);
            setCourseId(student.course_id ?? "");
            setAcademicYear(student.academic_year);
            setEnrolmentNo(student.enrolment_no);
            setAdmissionDate(student.admission_date);
            setAdmissionMode(student.admission_mode);
            setSeatType(student.seat_type);
            setReservationCategory(student.reservation_category);
            setNri(student.nri);
            setOci(student.oci);
            setForeignNational(student.foreign_national);
            setCountry(student.country || "");
            if (student.flags && student.flags.length > 0) {
              setSaveResult({
                student,
                flags: student.flags,
                is_valid: student.status === "valid",
                errors_count: student.flags.filter((f) => f.level === "error").length,
                exceptions_count: student.flags.filter((f) => f.level === "exception").length,
                warnings_count: student.flags.filter((f) => f.level === "warning").length,
                infos_count: student.flags.filter((f) => f.level === "info").length,
              });
            }
          }
        }
      } catch (err) {
        if (isMounted) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to load data");
        }
      } finally {
        if (isMounted) {
          setLoadingInitial(false);
        }
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [institutionId, isEditMode, studentId]);

  // When foreign national switches to No, reset country
  const handleForeignNationalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setForeignNational(val);
    if (val !== "Yes") {
      setCountry("");
    }
  };

  const handleCheckAndSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer) return;

    if (!courseId) {
      setErrorMessage("Select an approved course before saving.");
      return;
    }

    try {
      setSubmitting(true);
      setErrorMessage(null);

      const payload: StudentCreateRequest = {
        apaar_id: apaarId,
        name,
        dob,
        gender,
        course_id: Number(courseId),
        academic_year: academicYear,
        enrolment_no: enrolmentNo,
        admission_date: admissionDate,
        admission_mode: admissionMode,
        seat_type: seatType,
        reservation_category: reservationCategory,
        nri,
        oci,
        foreign_national: foreignNational,
        country: foreignNational === "Yes" ? country : null,
      };

      let res: StudentSaveResultResponse;
      if (isEditMode && studentId) {
        res = await updateStudent(institutionId, studentId, payload);
      } else {
        res = await createStudent(institutionId, payload);
      }

      setSaveResult(res);
      setSavedStudent(res.student);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save student record");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingInitial) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-slate-600">Loading student details...</p>
      </div>
    );
  }

  if (errorMessage && !courses.length) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ErrorState
          title="Failed to Load Student Information"
          message={errorMessage}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  const courseOptions = courses.map((c) => ({
    value: c.id,
    label: `${c.name} (${c.branch}) - ${c.level}`,
  }));

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link
              to="/college/students"
              className="text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
            >
              ← Back to Student Directory
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            {isEditMode ? `Edit Student Record #${studentId}` : "Single Student Entry"}
          </h1>
          <p className="text-sm text-slate-600">
            {isEditMode
              ? "Modify student data. Saved as draft and re-evaluated by the automated validation engine."
              : "Enter individual student details. 'Check and save' evaluates all rules and saves as draft."}
          </p>
        </div>

        {savedStudent && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Record Status:</span>
            <Badge
              variant={
                savedStudent.status === "valid"
                  ? "success"
                  : savedStudent.status === "flagged"
                  ? "warning"
                  : "neutral"
              }
            >
              {savedStudent.status.toUpperCase()}
            </Badge>
          </div>
        )}
      </div>

      {/* Read-Only Notice for Viewers */}
      {isViewer && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800">
          <strong>Read-only mode:</strong> You are signed in with the <Badge size="sm">viewer</Badge> role. Student data cannot be added or modified.
        </div>
      )}

      {/* Top Error Alert if submission failed */}
      {errorMessage && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md text-sm text-red-800 flex items-start gap-3">
          <span className="font-bold text-red-600">Error:</span>
          <div>{errorMessage}</div>
        </div>
      )}

      {/* Validation Feedback Banner after 'Check and save' */}
      {saveResult && (
        <div
          className={`p-5 rounded-lg border text-left space-y-3 transition-all ${
            saveResult.errors_count > 0
              ? "bg-red-50 border-red-300"
              : saveResult.exceptions_count > 0 || saveResult.warnings_count > 0
              ? "bg-amber-50 border-amber-300"
              : "bg-emerald-50 border-emerald-300"
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-base text-slate-900">
                {saveResult.errors_count > 0
                  ? "Draft Saved with Validation Errors"
                  : saveResult.exceptions_count > 0
                  ? "Draft Saved with Exceptions"
                  : saveResult.warnings_count > 0
                  ? "Draft Saved with Warnings"
                  : "Draft Validated Cleanly"}
              </span>
              <Badge variant={saveResult.is_valid ? "success" : "danger"}>
                {saveResult.is_valid ? "Compliant" : "Attention Required"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {saveResult.errors_count > 0 && (
                <FlagBadge level="error" count={saveResult.errors_count} />
              )}
              {saveResult.exceptions_count > 0 && (
                <FlagBadge level="exception" count={saveResult.exceptions_count} />
              )}
              {saveResult.warnings_count > 0 && (
                <FlagBadge level="warning" count={saveResult.warnings_count} />
              )}
            </div>
          </div>

          <p className="text-sm text-slate-700">
            {saveResult.errors_count > 0
              ? "The student record has been saved as a draft. However, errors must be resolved before final submission to AICTE."
              : saveResult.exceptions_count > 0
              ? "Record saved as draft. Exceptions may require written justification during final submission."
              : saveResult.warnings_count > 0
              ? "Record saved as draft with warnings. Please review the highlighted fields."
              : "All automated rules passed successfully. The student record is saved and compliant."}
          </p>

          {/* List of flags */}
          {saveResult.flags.length > 0 && (
            <div className="mt-3 space-y-2 border-t border-slate-200 pt-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 block">
                Rule Violations & Advisory Notices ({saveResult.flags.length})
              </span>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {saveResult.flags.map((flag: StudentValidationFlag, index: number) => (
                  <div
                    key={`${flag.rule_code}-${index}`}
                    className="p-3 bg-white rounded border border-slate-200 shadow-sm text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FlagBadge level={flag.level} />
                        <span className="font-mono font-semibold text-slate-800">
                          {flag.rule_code}
                        </span>
                        {flag.field && (
                          <span className="text-slate-500">
                            • Field: <code className="text-blue-700">{flag.field}</code>
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-slate-800 text-sm font-medium">{flag.message}</p>
                    {flag.fix_hint && (
                      <p className="text-slate-500 italic">
                        <strong>Fix hint:</strong> {flag.fix_hint}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="pt-2 flex items-center justify-between">
            <span className="text-xs text-slate-500 font-mono">
              Database ID: #{saveResult.student.id} • APAAR: {saveResult.student.apaar_id}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => navigate("/college/students")}
            >
              View in Directory
            </Button>
          </div>
        </div>
      )}

      {/* Main Student Form */}
      <form onSubmit={handleCheckAndSave} className="space-y-6">
        {/* GROUP 1: Identity */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
                1
              </span>
              Identity Information
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              National academic identifier and personal identity attributes (Spec 8.2).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="APAAR ID (12 Digits)"
              placeholder="e.g. 111122223333"
              value={apaarId}
              onChange={(e) => setApaarId(e.target.value)}
              required
              disabled={isViewer}
              hint="Exactly 12 numeric digits assigned by the Ministry of Education"
            />

            <Input
              label="Student Full Name"
              placeholder="e.g. Rahul Sharma"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={isViewer}
              hint="Official name containing letters, spaces, dots, or hyphens"
            />

            <Input
              label="Date of Birth"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              required
              disabled={isViewer}
              hint="Encrypted with Fernet at rest. Zero plain Aadhaar/DOB leakage."
            />

            <Select
              label="Gender"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              options={GENDER_OPTIONS}
              disabled={isViewer}
            />
          </div>
        </section>

        {/* GROUP 2: Admission */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
                2
              </span>
              Admission Details
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Institutional curriculum enrolment, enrolment number, and admission mode (Spec 8.2).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Select
                label="Approved Course & Branch"
                value={courseId}
                onChange={(e) => setCourseId(Number(e.target.value))}
                options={courseOptions}
                disabled={isViewer || courses.length === 0}
                required
                hint="Only AICTE-approved courses for this institution are permitted"
              />
            </div>

            <Input
              label="Academic Year"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              required
              disabled={isViewer}
              hint="Target academic year cycle (default 2026-27)"
            />

            <Input
              label="College Enrolment / Roll No."
              placeholder="e.g. EN26-CSE-0042"
              value={enrolmentNo}
              onChange={(e) => setEnrolmentNo(e.target.value)}
              required
              disabled={isViewer}
              hint="Unique within this course and academic year"
            />

            <Input
              label="Admission Date"
              type="date"
              value={admissionDate}
              onChange={(e) => setAdmissionDate(e.target.value)}
              required
              disabled={isViewer}
              hint="Must fall within the academic year admission window"
            />

            <Select
              label="Admission Mode"
              value={admissionMode}
              onChange={(e) => setAdmissionMode(e.target.value)}
              options={ADMISSION_MODE_OPTIONS}
              disabled={isViewer}
            />

            <Select
              label="Seat Type"
              value={seatType}
              onChange={(e) => setSeatType(e.target.value)}
              options={SEAT_TYPE_OPTIONS}
              disabled={isViewer}
              hint="Supernumerary seats require AICTE supernumerary quota approval"
            />
          </div>
        </section>

        {/* GROUP 3: Category & Nationality */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
                3
              </span>
              Category & Nationality
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Statutory reservation categories and international status (Spec 8.2).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Reservation Category"
              value={reservationCategory}
              onChange={(e) => setReservationCategory(e.target.value)}
              options={RESERVATION_OPTIONS}
              disabled={isViewer}
            />

            <Select
              label="Non-Resident Indian (NRI)"
              value={nri}
              onChange={(e) => setNri(e.target.value)}
              options={YES_NO_OPTIONS}
              disabled={isViewer}
            />

            <Select
              label="Overseas Citizen of India (OCI)"
              value={oci}
              onChange={(e) => setOci(e.target.value)}
              options={YES_NO_OPTIONS}
              disabled={isViewer}
            />

            <Select
              label="Foreign National"
              value={foreignNational}
              onChange={handleForeignNationalChange}
              options={YES_NO_OPTIONS}
              disabled={isViewer}
              hint="Country field appears only when 'Yes' is selected"
            />

            {/* Country field appears strictly for foreign nationals per TASKS.md T20 */}
            {foreignNational === "Yes" && (
              <div className="sm:col-span-2 p-4 bg-blue-50 border border-blue-200 rounded-md space-y-2">
                <Input
                  label="Country of Origin / Citizenship"
                  placeholder="e.g. Nepal, Bhutan, United Kingdom"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  required
                  disabled={isViewer}
                  hint="Mandatory when Foreign National is marked Yes (Spec 8.2 COUNTRY_REQUIRED)"
                />
              </div>
            )}
          </div>
        </section>

        {/* Action Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/college/students")}
            disabled={submitting}
          >
            Cancel
          </Button>

          {!isViewer && (
            <Button
              type="submit"
              variant="primary"
              disabled={submitting}
              className="min-w-[160px]"
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Validating & Saving...
                </>
              ) : (
                "Check and save"
              )}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
};
export default StudentFormPage;
