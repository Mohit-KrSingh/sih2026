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
import { Badge, FlagBadge } from "../components/ux4g/Badge";
import { Button } from "../components/ux4g/Button";
import { Card, CardBody } from "../components/ux4g/Card";
import { DatePicker } from "../components/ux4g/DatePicker";
import { EmptyState } from "../components/ux4g/EmptyState";
import { ErrorSummary, type ErrorItem } from "../components/ux4g/ErrorSummary";
import { FormField } from "../components/ux4g/FormField";
import { Icon } from "../components/ux4g/Icon";
import { Input } from "../components/ux4g/Input";
import { Select, type SelectOption } from "../components/ux4g/Select";
import { Spinner } from "../components/ux4g/Spinner";
import { Alert } from "../components/ux4g/Alert";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

const GENDER_OPTIONS: SelectOption[] = [
  { value: "Male", label: "Male" },
  { value: "Female", label: "Female" },
  { value: "Other", label: "Other" },
];

const ADMISSION_MODE_OPTIONS: SelectOption[] = [
  { value: "State counselling", label: "State counselling" },
  { value: "JEE Main counselling", label: "JEE Main counselling" },
  { value: "Management quota", label: "Management quota" },
  { value: "Direct second year", label: "Direct second year" },
  { value: "NRI/OCI/foreign quota", label: "NRI/OCI/foreign quota" },
  { value: "Other", label: "Other" },
];

const SEAT_TYPE_OPTIONS: SelectOption[] = [
  { value: "Regular", label: "Regular" },
  { value: "Supernumerary", label: "Supernumerary" },
];

const RESERVATION_OPTIONS: SelectOption[] = [
  { value: "General", label: "General" },
  { value: "OBC", label: "OBC" },
  { value: "SC", label: "SC" },
  { value: "ST", label: "ST" },
  { value: "EWS", label: "EWS" },
];

const YES_NO_OPTIONS: SelectOption[] = [
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

  // Form State: Group 1 - Identity
  const [apaarId, setApaarId] = useState("");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [gender, setGender] = useState("Male");

  // Form State: Group 2 - Admission
  const [courseId, setCourseId] = useState<number | "">("");
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [enrolmentNo, setEnrolmentNo] = useState("");
  const [admissionDate, setAdmissionDate] = useState("");
  const [admissionMode, setAdmissionMode] = useState("State counselling");
  const [seatType, setSeatType] = useState("Regular");

  // Form State: Group 3 - Category & Nationality
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

  // Form errors for ErrorSummary & field binding
  const [formErrors, setFormErrors] = useState<ErrorItem[]>([]);

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

  // Helper to retrieve live check flag from backend results
  const getFieldFlag = (fieldId: string): StudentValidationFlag | undefined => {
    if (!saveResult?.flags) return undefined;
    return saveResult.flags.find(
      (f) =>
        f.field === fieldId ||
        (fieldId === "course_id" && (f.field === "course" || f.field === "course_id"))
    );
  };

  // Helper to retrieve field error message for FormField binding
  const getFieldError = (fieldId: string): string | undefined => {
    const directErr = formErrors.find((e) => e.fieldId === fieldId);
    return directErr?.message;
  };

  // Client-side validation per SPEC §8.2
  const validateForm = (): ErrorItem[] => {
    const errors: ErrorItem[] = [];

    if (!apaarId.trim()) {
      errors.push({ fieldId: "apaar_id", message: "APAAR ID is required (12 digits)." });
    } else if (!/^\d{12}$/.test(apaarId.trim())) {
      errors.push({ fieldId: "apaar_id", message: "APAAR ID must be exactly 12 numeric digits." });
    }

    if (!name.trim()) {
      errors.push({ fieldId: "name", message: "Student full name is required." });
    }

    if (!dob) {
      errors.push({ fieldId: "dob", message: "Date of birth is required." });
    }

    if (!courseId) {
      errors.push({ fieldId: "course_id", message: "An approved course must be selected." });
    }

    if (!academicYear.trim()) {
      errors.push({ fieldId: "academic_year", message: "Academic year is required." });
    }

    if (!enrolmentNo.trim()) {
      errors.push({ fieldId: "enrolment_no", message: "College enrolment or roll number is required." });
    }

    if (!admissionDate) {
      errors.push({ fieldId: "admission_date", message: "Admission date is required." });
    }

    if (foreignNational === "Yes" && !country.trim()) {
      errors.push({ fieldId: "country", message: "Country of origin is required when Foreign National is Yes." });
    }

    return errors;
  };

  const handleCheckAndSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer) return;

    // Run client validation
    const validationErrors = validateForm();
    if (validationErrors.length > 0) {
      setFormErrors(validationErrors);
      setErrorMessage("Please correct the validation errors highlighted below before saving.");
      return;
    }

    try {
      setSubmitting(true);
      setErrorMessage(null);
      setFormErrors([]);

      const payload: StudentCreateRequest = {
        apaar_id: apaarId.trim(),
        name: name.trim(),
        dob,
        gender,
        course_id: Number(courseId),
        academic_year: academicYear.trim(),
        enrolment_no: enrolmentNo.trim(),
        admission_date: admissionDate,
        admission_mode: admissionMode,
        seat_type: seatType,
        reservation_category: reservationCategory,
        nri,
        oci,
        foreign_national: foreignNational,
        country: foreignNational === "Yes" ? country.trim() : null,
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
        <Spinner size="lg" />
        <p className="mt-4 text-sm ux4g-text-neutral-secondary">Loading student admission data...</p>
      </div>
    );
  }

  if (errorMessage && !courses.length) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <EmptyState
          title="Failed to load student information"
          description={errorMessage}
          action={
            <Button variant="primary" onClick={() => window.location.reload()}>
              Retry loading
            </Button>
          }
        />
      </div>
    );
  }

  const courseOptions: SelectOption[] = courses.map((c) => ({
    value: c.id,
    label: `${c.name} (${c.branch}) - ${c.level}`,
  }));

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b ux4g-border-neutral-subtle pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link
              to="/college/students"
              className="text-sm font-semibold ux4g-text-brand hover:opacity-80 transition-opacity flex items-center gap-1"
            >
              <Icon name="arrow_back" size="xs" color="inherit" aria-hidden="true" />
              <span>Back to Student Directory</span>
            </Link>
          </div>
          <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight mt-1">
            {isEditMode ? `Edit student record #${studentId}` : "Single Student Entry"}
          </h1>
          <p className="text-xs ux4g-text-neutral-secondary">
            {isEditMode
              ? "Modify student data. Saved as draft and re-evaluated by the automated validation engine."
              : "Enter individual student details. 'Check and save' evaluates all rules and saves as draft."}
          </p>
        </div>

        {savedStudent && (
          <div className="flex items-center gap-2">
            <span className="text-xs ux4g-text-neutral-secondary">Record Status:</span>
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
        <Alert variant="warning" title="Read-only mode:">
          You are signed in with the viewer role. Student data cannot be added or modified.
        </Alert>
      )}

      {/* Top Error Alert if submission failed */}
      {errorMessage && (
        <Alert variant="error" title="Submission Error">
          {errorMessage}
        </Alert>
      )}

      {/* Error Summary at top when validation errors exist (autoFocuses and links to invalid fields) */}
      {formErrors.length > 0 && (
        <ErrorSummary
          errors={formErrors}
          title="There is a problem with your submission"
          autoFocus={true}
        />
      )}

      {/* Validation Feedback Banner after 'Check and save' */}
      {saveResult && (
        <Card
          variant="outline"
          className={`p-5 text-left space-y-3 transition-all ${
            saveResult.errors_count > 0
              ? "ux4g-bg-error-soft ux4g-border-error"
              : saveResult.exceptions_count > 0 || saveResult.warnings_count > 0
              ? "ux4g-bg-warning-soft ux4g-border-warning"
              : "ux4g-bg-success-soft ux4g-border-success"
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-base ux4g-text-neutral-primary">
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

          <p className="text-sm ux4g-text-neutral-primary">
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
            <div className="mt-3 space-y-2 border-t ux4g-border-neutral-subtle pt-3">
              <span className="text-xs font-semibold uppercase tracking-wider ux4g-text-neutral-secondary block">
                Rule violations and advisory notices ({saveResult.flags.length})
              </span>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {saveResult.flags.map((flag: StudentValidationFlag, index: number) => (
                  <div
                    key={`${flag.rule_code}-${index}`}
                    className="p-3 ux4g-bg-neutral-elevated rounded border ux4g-border-neutral-subtle shadow-sm text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FlagBadge level={flag.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {flag.rule_code}
                        </span>
                        {flag.field && (
                          <span className="ux4g-text-neutral-secondary">
                            • Field: <code className="ux4g-text-brand font-semibold">{flag.field}</code>
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="ux4g-text-neutral-primary text-sm font-medium">{flag.message}</p>
                    {flag.fix_hint && (
                      <p className="ux4g-text-neutral-secondary italic">
                        <strong>Fix hint:</strong> {flag.fix_hint}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="pt-2 flex items-center justify-between">
            <span className="text-xs ux4g-text-neutral-secondary font-mono">
              Database ID: #{saveResult.student.id} • APAAR: {saveResult.student.apaar_id}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => navigate("/college/students")}
            >
              View in directory
            </Button>
          </div>
        </Card>
      )}

      {/* Main Student Form */}
      <form noValidate onSubmit={handleCheckAndSave} className="space-y-6">
        {/* GROUP 1: Identity */}
        <Card variant="outline" className="p-6 space-y-4">
          <CardBody className="p-0 space-y-4">
            <div className="border-b ux4g-border-neutral-subtle pb-3">
              <h2 className="text-lg font-semibold ux4g-text-neutral-primary flex items-center gap-2">
                <span className="w-6 h-6 rounded-full ux4g-bg-primary-soft ux4g-text-brand text-xs font-bold flex items-center justify-center">
                  1
                </span>
                Identity Information
              </h2>
              <p className="text-xs ux4g-text-neutral-secondary mt-1">
                National academic identifier and personal identity attributes (Spec 8.2).
              </p>
            </div>

            <div className="space-y-4">
              {/* Field 1: APAAR ID */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
                <div className={getFieldFlag("apaar_id") ? "md:col-span-7" : "md:col-span-12"}>
                  <FormField
                    id="apaar_id"
                    label="APAAR ID (12 Digits)"
                    required
                    hint="Exactly 12 numeric digits assigned by the Ministry of Education"
                    error={getFieldError("apaar_id")}
                  >
                    <Input
                      id="apaar_id"
                      placeholder="e.g. 111122223333"
                      maxLength={12}
                      value={apaarId}
                      onChange={(e) => setApaarId(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                </div>
                {getFieldFlag("apaar_id") && (
                  <div className="md:col-span-5 pt-1 md:pt-6" data-testid="live-check-apaar_id">
                    <div className="p-3 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("apaar_id")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("apaar_id")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("apaar_id")!.message}`}
                      </p>
                      {getFieldFlag("apaar_id")!.fix_hint && (
                        <p className="italic ux4g-text-neutral-secondary">
                          <strong>Fix hint:</strong> {getFieldFlag("apaar_id")!.fix_hint}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Field 2: Student Full Name */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
                <div className={getFieldFlag("name") ? "md:col-span-7" : "md:col-span-12"}>
                  <FormField
                    id="name"
                    label="Student Full Name"
                    required
                    hint="Official name containing letters, spaces, dots, or hyphens"
                    error={getFieldError("name")}
                  >
                    <Input
                      id="name"
                      placeholder="e.g. Rahul Sharma"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                </div>
                {getFieldFlag("name") && (
                  <div className="md:col-span-5 pt-1 md:pt-6" data-testid="live-check-name">
                    <div className="p-3 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("name")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("name")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("name")!.message}`}
                      </p>
                      {getFieldFlag("name")!.fix_hint && (
                        <p className="italic ux4g-text-neutral-secondary">
                          <strong>Fix hint:</strong> {getFieldFlag("name")!.fix_hint}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Field 3: Date of Birth & Field 4: Gender */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
                <div>
                  <FormField
                    id="dob"
                    label="Date of Birth"
                    required
                    hint="Encrypted with Fernet at rest. Zero plain Aadhaar/DOB leakage."
                    error={getFieldError("dob")}
                  >
                    <DatePicker
                      id="dob"
                      value={dob}
                      onChange={(e) => setDob(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("dob") && (
                    <div className="pt-2" data-testid="live-check-dob">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("dob")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("dob")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("dob")!.message}`}
                        </p>
                        {getFieldFlag("dob")!.fix_hint && (
                          <p className="italic ux4g-text-neutral-secondary">
                            <strong>Fix hint:</strong> {getFieldFlag("dob")!.fix_hint}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <FormField id="gender" label="Gender" error={getFieldError("gender")}>
                    <Select
                      id="gender"
                      value={gender}
                      onChange={(e) => setGender(e.target.value)}
                      options={GENDER_OPTIONS}
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("gender") && (
                    <div className="pt-2" data-testid="live-check-gender">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("gender")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("gender")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("gender")!.message}`}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* GROUP 2: Admission */}
        <Card variant="outline" className="p-6 space-y-4">
          <CardBody className="p-0 space-y-4">
            <div className="border-b ux4g-border-neutral-subtle pb-3">
              <h2 className="text-lg font-semibold ux4g-text-neutral-primary flex items-center gap-2">
                <span className="w-6 h-6 rounded-full ux4g-bg-primary-soft ux4g-text-brand text-xs font-bold flex items-center justify-center">
                  2
                </span>
                Admission Details
              </h2>
              <p className="text-xs ux4g-text-neutral-secondary mt-1">
                Institutional curriculum enrolment, enrolment number, and admission mode (Spec 8.2).
              </p>
            </div>

            <div className="space-y-4">
              {/* Field 5: Approved Course */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
                <div className={getFieldFlag("course_id") ? "md:col-span-7" : "md:col-span-12"}>
                  <FormField
                    id="course_id"
                    label="Approved Course & Branch"
                    required
                    hint="Only AICTE-approved courses for this institution are permitted"
                    error={getFieldError("course_id")}
                  >
                    <Select
                      id="course_id"
                      value={courseId}
                      onChange={(e) => setCourseId(Number(e.target.value))}
                      options={courseOptions}
                      disabled={isViewer || courses.length === 0}
                      required
                    />
                  </FormField>
                </div>
                {getFieldFlag("course_id") && (
                  <div className="md:col-span-5 pt-1 md:pt-6" data-testid="live-check-course_id">
                    <div className="p-3 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("course_id")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("course_id")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("course_id")!.message}`}
                      </p>
                      {getFieldFlag("course_id")!.fix_hint && (
                        <p className="italic ux4g-text-neutral-secondary">
                          <strong>Fix hint:</strong> {getFieldFlag("course_id")!.fix_hint}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Field 6: Academic Year & Field 7: Enrolment No */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
                <div>
                  <FormField
                    id="academic_year"
                    label="Academic Year"
                    required
                    hint="Target academic year cycle (default 2026-27)"
                    error={getFieldError("academic_year")}
                  >
                    <Input
                      id="academic_year"
                      value={academicYear}
                      onChange={(e) => setAcademicYear(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("academic_year") && (
                    <div className="pt-2" data-testid="live-check-academic_year">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("academic_year")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("academic_year")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("academic_year")!.message}`}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <FormField
                    id="enrolment_no"
                    label="College Enrolment / Roll No."
                    required
                    hint="Unique within this course and academic year"
                    error={getFieldError("enrolment_no")}
                  >
                    <Input
                      id="enrolment_no"
                      placeholder="e.g. EN26-CSE-0042"
                      value={enrolmentNo}
                      onChange={(e) => setEnrolmentNo(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("enrolment_no") && (
                    <div className="pt-2" data-testid="live-check-enrolment_no">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("enrolment_no")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("enrolment_no")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("enrolment_no")!.message}`}
                        </p>
                        {getFieldFlag("enrolment_no")!.fix_hint && (
                          <p className="italic ux4g-text-neutral-secondary">
                            <strong>Fix hint:</strong> {getFieldFlag("enrolment_no")!.fix_hint}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Field 8: Admission Date, Field 9: Mode, Field 10: Seat Type */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-start">
                <div>
                  <FormField
                    id="admission_date"
                    label="Admission Date"
                    required
                    hint="Must fall within the academic year admission window"
                    error={getFieldError("admission_date")}
                  >
                    <DatePicker
                      id="admission_date"
                      value={admissionDate}
                      onChange={(e) => setAdmissionDate(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("admission_date") && (
                    <div className="pt-2" data-testid="live-check-admission_date">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("admission_date")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("admission_date")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("admission_date")!.message}`}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <FormField id="admission_mode" label="Admission Mode" error={getFieldError("admission_mode")}>
                    <Select
                      id="admission_mode"
                      value={admissionMode}
                      onChange={(e) => setAdmissionMode(e.target.value)}
                      options={ADMISSION_MODE_OPTIONS}
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("admission_mode") && (
                    <div className="pt-2" data-testid="live-check-admission_mode">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("admission_mode")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("admission_mode")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("admission_mode")!.message}`}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <FormField
                    id="seat_type"
                    label="Seat Type"
                    hint="Supernumerary seats require AICTE supernumerary quota approval"
                    error={getFieldError("seat_type")}
                  >
                    <Select
                      id="seat_type"
                      value={seatType}
                      onChange={(e) => setSeatType(e.target.value)}
                      options={SEAT_TYPE_OPTIONS}
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("seat_type") && (
                    <div className="pt-2" data-testid="live-check-seat_type">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("seat_type")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("seat_type")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                          {`Live status: ${getFieldFlag("seat_type")!.message}`}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* GROUP 3: Category & Nationality */}
        <Card variant="outline" className="p-6 space-y-4">
          <CardBody className="p-0 space-y-4">
            <div className="border-b ux4g-border-neutral-subtle pb-3">
              <h2 className="text-lg font-semibold ux4g-text-neutral-primary flex items-center gap-2">
                <span className="w-6 h-6 rounded-full ux4g-bg-primary-soft ux4g-text-brand text-xs font-bold flex items-center justify-center">
                  3
                </span>
                Category & Nationality
              </h2>
              <p className="text-xs ux4g-text-neutral-secondary mt-1">
                Statutory reservation categories and international status (Spec 8.2).
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
              <div>
                <FormField
                  id="reservation_category"
                  label="Reservation Category"
                  error={getFieldError("reservation_category")}
                >
                  <Select
                    id="reservation_category"
                    value={reservationCategory}
                    onChange={(e) => setReservationCategory(e.target.value)}
                    options={RESERVATION_OPTIONS}
                    disabled={isViewer}
                  />
                </FormField>
                {getFieldFlag("reservation_category") && (
                  <div className="pt-2" data-testid="live-check-reservation_category">
                    <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("reservation_category")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("reservation_category")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("reservation_category")!.message}`}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <FormField id="nri" label="Non-Resident Indian (NRI)" error={getFieldError("nri")}>
                  <Select
                    id="nri"
                    value={nri}
                    onChange={(e) => setNri(e.target.value)}
                    options={YES_NO_OPTIONS}
                    disabled={isViewer}
                  />
                </FormField>
                {getFieldFlag("nri") && (
                  <div className="pt-2" data-testid="live-check-nri">
                    <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("nri")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("nri")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("nri")!.message}`}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <FormField id="oci" label="Overseas Citizen of India (OCI)" error={getFieldError("oci")}>
                  <Select
                    id="oci"
                    value={oci}
                    onChange={(e) => setOci(e.target.value)}
                    options={YES_NO_OPTIONS}
                    disabled={isViewer}
                  />
                </FormField>
                {getFieldFlag("oci") && (
                  <div className="pt-2" data-testid="live-check-oci">
                    <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("oci")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("oci")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("oci")!.message}`}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <FormField
                  id="foreign_national"
                  label="Foreign National"
                  hint="Country field appears only when 'Yes' is selected"
                  error={getFieldError("foreign_national")}
                >
                  <Select
                    id="foreign_national"
                    value={foreignNational}
                    onChange={handleForeignNationalChange}
                    options={YES_NO_OPTIONS}
                    disabled={isViewer}
                  />
                </FormField>
                {getFieldFlag("foreign_national") && (
                  <div className="pt-2" data-testid="live-check-foreign_national">
                    <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FlagBadge level={getFieldFlag("foreign_national")!.level} />
                        <span className="font-mono font-semibold ux4g-text-neutral-primary">
                          {`[${getFieldFlag("foreign_national")!.rule_code}]`}
                        </span>
                      </div>
                      <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("foreign_national")!.message}`}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Country field appears strictly for foreign nationals per TASKS.md T20 */}
              {foreignNational === "Yes" && (
                <div className="sm:col-span-2 p-4 ux4g-bg-neutral-soft border ux4g-border-neutral-subtle rounded-md space-y-2">
                  <FormField
                    id="country"
                    label="Country of Origin / Citizenship"
                    required
                    hint="Mandatory when Foreign National is marked Yes (Spec 8.2 COUNTRY_REQUIRED)"
                    error={getFieldError("country")}
                  >
                    <Input
                      id="country"
                      placeholder="e.g. Nepal, Bhutan, United Kingdom"
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      required
                      disabled={isViewer}
                    />
                  </FormField>
                  {getFieldFlag("country") && (
                    <div className="pt-2" data-testid="live-check-country">
                      <div className="p-2.5 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs space-y-1">
                        <div className="flex items-center gap-1.5">
                          <FlagBadge level={getFieldFlag("country")!.level} />
                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                            {`[${getFieldFlag("country")!.rule_code}]`}
                          </span>
                        </div>
                        <p className="font-medium ux4g-text-neutral-primary">
                        {`Live status: ${getFieldFlag("country")!.message}`}
                      </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Action Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t ux4g-border-neutral-subtle">
          <Button
            type="button"
            variant="outline"
            aria-label="Cancel and return to student directory"
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
              isLoading={submitting}
              className="min-w-[160px]"
            >
              Check and save
            </Button>
          )}
        </div>
      </form>
    </div>
  );
};

export default StudentFormPage;
