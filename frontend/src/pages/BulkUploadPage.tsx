import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listCourses, type CourseResponse } from "../api/institutions";
import {
  downloadErrorCsv,
  downloadTemplateCsv,
  getUploadDetails,
  getUploadHistory,
  updateStudent,
  uploadStudentsFile,
  type StudentUpdateRequest,
  type UploadHistoryItem,
  type UploadResultResponse,
  type UploadRowResult,
} from "../api/students";
import { useAuth } from "../auth/AuthContext";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  FileUpload,
  FlagBadge,
  Icon,
  Input,
  Progress,
  Select,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableEmptyState,
  TableHead,
  TableHeader,
  TablePagination,
  TableRow,
  TableSkeletonRows,
} from "../components/ux4g";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

const SEAT_TYPE_OPTIONS = [
  { value: "Regular", label: "Regular" },
  { value: "Supernumerary", label: "Supernumerary" },
];

type SortableField =
  | "row_number"
  | "apaar_id"
  | "name"
  | "course"
  | "enrolment_no"
  | "admission_date"
  | "seat_type"
  | "status";

export function BulkUploadPage() {
  useDocumentTitle("Bulk Student Upload");
  const { user } = useAuth();
  const institutionId = user?.institution_id ?? 1;

  // View state: "upload" | "results" | "history"
  const [activeTab, setActiveTab] = useState<"upload" | "results" | "history">("upload");

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [academicYear, setAcademicYear] = useState<string>("2026-27");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Result State
  const [result, setResult] = useState<UploadResultResponse | null>(null);
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [courseFilter, setCourseFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Sorting State
  const [sortField, setSortField] = useState<SortableField | null>(null);
  const [sortDirection, setSortDirection] = useState<"ascending" | "descending" | "none">("none");

  // Pagination State (enables smooth scrolling and instant interaction with 5,000+ rows)
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);

  // Inline Edit State
  const [editingRowNumber, setEditingRowNumber] = useState<number | null>(null);
  const [editFormData, setEditFormData] = useState<Partial<UploadRowResult>>({});
  const [isSavingRow, setIsSavingRow] = useState<boolean>(false);
  const [inlineSaveSuccess, setInlineSaveSuccess] = useState<string | null>(null);

  // Upload History State
  const [historyItems, setHistoryItems] = useState<UploadHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  // Approved Courses
  const [courses, setCourses] = useState<CourseResponse[]>([]);

  // Load courses
  useEffect(() => {
    if (institutionId) {
      listCourses(institutionId)
        .then(setCourses)
        .catch(() => {});
    }
  }, [institutionId]);

  // Load history when tab is clicked
  useEffect(() => {
    if (activeTab === "history" && institutionId) {
      setIsLoadingHistory(true);
      getUploadHistory(institutionId)
        .then((res) => setHistoryItems(res.items))
        .catch(() => {})
        .finally(() => setIsLoadingHistory(false));
    }
  }, [activeTab, institutionId]);

  // Template download trigger
  const handleDownloadTemplate = async () => {
    try {
      const csvText = await downloadTemplateCsv(institutionId);
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "apaar_student_upload_template.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: unknown) {
      alert((err as Error).message || "Failed to download template");
    }
  };

  // Download error CSV
  const handleDownloadErrors = async (uploadId: number) => {
    try {
      const csvText = await downloadErrorCsv(institutionId, uploadId);
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `upload_${uploadId}_errors.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: unknown) {
      alert((err as Error).message || "Failed to download error file");
    }
  };

  // Handle file upload
  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a file to upload (.csv, .tsv, .xlsx, .xls)");
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const data = await uploadStudentsFile(institutionId, selectedFile, academicYear);
      setResult(data);
      setActiveTab("results");
      setSelectedFile(null);
      setCurrentPage(1);
    } catch (err: unknown) {
      setUploadError((err as Error).message || "Upload failed. Please check file formatting.");
    } finally {
      setIsUploading(false);
    }
  };

  // Handle viewing a past upload
  const handleViewPastUpload = async (uploadId: number) => {
    try {
      setIsUploading(true);
      const data = await getUploadDetails(institutionId, uploadId);
      setResult(data);
      setActiveTab("results");
      setCurrentPage(1);
    } catch (err: unknown) {
      alert((err as Error).message || "Failed to load upload details");
    } finally {
      setIsUploading(false);
    }
  };

  // Toggle row expansion for flags
  const toggleRowExpanded = (rowNum: number) => {
    setExpandedRows((prev) => ({
      ...prev,
      [rowNum]: !prev[rowNum],
    }));
  };

  // Sorting handler
  const handleSort = (field: SortableField) => {
    if (sortField !== field) {
      setSortField(field);
      setSortDirection("ascending");
    } else if (sortDirection === "ascending") {
      setSortDirection("descending");
    } else if (sortDirection === "descending") {
      setSortField(null);
      setSortDirection("none");
    } else {
      setSortDirection("ascending");
    }
  };

  // Inline edit start
  const handleStartInlineEdit = (row: UploadRowResult) => {
    setEditingRowNumber(row.row_number);
    setEditFormData({ ...row });
    setInlineSaveSuccess(null);
  };

  const handleCancelInlineEdit = () => {
    setEditingRowNumber(null);
    setEditFormData({});
  };

  // Inline edit save
  const handleSaveInlineEdit = async (rowNum: number) => {
    if (!result || !editFormData.student_id) {
      alert("This row cannot be edited directly because it does not have a student record.");
      return;
    }

    setIsSavingRow(true);
    setInlineSaveSuccess(null);

    try {
      let courseId: number | undefined = undefined;
      const matchedCourse = courses.find(
        (c) => c.name.toLowerCase() === (editFormData.course || "").toLowerCase()
      );
      if (matchedCourse) {
        courseId = matchedCourse.id;
      }

      const payload: StudentUpdateRequest = {
        name: editFormData.name,
        dob: editFormData.dob,
        gender: editFormData.gender,
        course_id: courseId,
        academic_year: editFormData.admission_year,
        enrolment_no: editFormData.enrolment_no,
        admission_date: editFormData.admission_date,
        admission_mode: editFormData.admission_mode,
        seat_type: editFormData.seat_type,
        reservation_category: editFormData.reservation_category,
        nri: editFormData.nri,
        oci: editFormData.oci,
        foreign_national: editFormData.foreign_national,
        country: editFormData.country,
      };

      const updated = await updateStudent(institutionId, editFormData.student_id, payload);

      // Update row in result state
      const updatedRows = result.rows.map((r) => {
        if (r.row_number === rowNum) {
          return {
            ...r,
            name: updated.student.name,
            dob: updated.student.dob,
            gender: updated.student.gender,
            course: updated.student.course_name,
            branch: updated.student.branch,
            enrolment_no: updated.student.enrolment_no,
            admission_date: updated.student.admission_date,
            admission_mode: updated.student.admission_mode,
            seat_type: updated.student.seat_type,
            reservation_category: updated.student.reservation_category,
            status: updated.student.status,
            flags: updated.flags,
          };
        }
        return r;
      });

      // Recalculate summary counts
      const validCount = updatedRows.filter((r) => r.status === "valid").length;
      const flaggedCount = updatedRows.filter((r) => r.status === "flagged").length;

      setResult({
        ...result,
        summary: {
          ...result.summary,
          valid_rows: validCount,
          flagged_rows: flaggedCount,
        },
        rows: updatedRows,
      });

      setEditingRowNumber(null);
      setEditFormData({});
      setInlineSaveSuccess(`Row #${rowNum} updated and re-validated successfully.`);
    } catch (err: unknown) {
      alert((err as Error).message || "Failed to update row");
    } finally {
      setIsSavingRow(false);
    }
  };

  // Filtered and Sorted rows (memoized for instantaneous responsiveness over 5,000+ records)
  const filteredAndSortedRows = useMemo(() => {
    const rawRows = result?.rows || [];

    const filtered = rawRows.filter((r) => {
      // Flag level filter
      if (levelFilter !== "all") {
        if (levelFilter === "clean") {
          if (r.flags.length > 0) return false;
        } else {
          const hasLevel = r.flags.some((f) => f.level === levelFilter);
          if (!hasLevel) return false;
        }
      }

      // Course filter
      if (courseFilter !== "all") {
        if (r.course.toLowerCase() !== courseFilter.toLowerCase()) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const match =
          r.apaar_id.toLowerCase().includes(q) ||
          r.name.toLowerCase().includes(q) ||
          r.enrolment_no.toLowerCase().includes(q);
        if (!match) return false;
      }

      return true;
    });

    if (!sortField || sortDirection === "none") {
      return filtered;
    }

    return [...filtered].sort((a, b) => {
      let valA: string | number = "";
      let valB: string | number = "";

      switch (sortField) {
        case "row_number":
          valA = a.row_number;
          valB = b.row_number;
          break;
        case "apaar_id":
          valA = a.apaar_id || "";
          valB = b.apaar_id || "";
          break;
        case "name":
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
          break;
        case "course":
          valA = a.course.toLowerCase();
          valB = b.course.toLowerCase();
          break;
        case "enrolment_no":
          valA = a.enrolment_no.toLowerCase();
          valB = b.enrolment_no.toLowerCase();
          break;
        case "admission_date":
          valA = a.admission_date;
          valB = b.admission_date;
          break;
        case "seat_type":
          valA = a.seat_type;
          valB = b.seat_type;
          break;
        case "status":
          valA = a.status;
          valB = b.status;
          break;
      }

      if (valA < valB) return sortDirection === "ascending" ? -1 : 1;
      if (valA > valB) return sortDirection === "ascending" ? 1 : -1;
      return 0;
    });
  }, [result?.rows, levelFilter, courseFilter, searchQuery, sortField, sortDirection]);

  // Paginated window for silky smooth 60fps rendering
  const totalFilteredRows = filteredAndSortedRows.length;
  const totalPages = Math.max(1, Math.ceil(totalFilteredRows / pageSize));
  const currentSafePage = Math.min(currentPage, totalPages);

  const paginatedRows = useMemo(() => {
    const startIndex = (currentSafePage - 1) * pageSize;
    return filteredAndSortedRows.slice(startIndex, startIndex + pageSize);
  }, [filteredAndSortedRows, currentSafePage, pageSize]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b ux4g-border-neutral-subtle">
        <div>
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 mb-1.5 text-xs font-semibold uppercase tracking-wider">
            <Link
              to="/college/students"
              className="ux4g-text-brand-primary hover:underline focus:outline-none focus:ring-1 focus:ring-primary rounded"
            >
              Students Directory
            </Link>
            <span className="ux4g-text-neutral-tertiary">/</span>
            <span className="ux4g-text-neutral-secondary">Bulk Upload</span>
          </nav>
          <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight">
            Bulk Student Enrolment Upload
          </h1>
          <p className="text-sm ux4g-text-neutral-secondary mt-1">
            Upload CSV or Excel files with APAAR IDs to enrol students, execute pure rule validation,
            and resolve compliance flags.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            onClick={handleDownloadTemplate}
            aria-label="Download CSV Template with required lowercase headers"
          >
            Download CSV Template
          </Button>
          {result && (
            <Button
              variant="secondary"
              onClick={() => handleDownloadErrors(result.upload_id)}
              disabled={
                result.summary.error_count === 0 &&
                result.summary.warning_count === 0 &&
                result.summary.exception_count === 0
              }
              aria-label="Download Error File containing invalid or flagged rows"
            >
              Download Error File
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b ux4g-border-neutral-subtle gap-2" role="tablist" aria-label="Upload navigation tabs">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "upload"}
          onClick={() => setActiveTab("upload")}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer ${
            activeTab === "upload"
              ? "border-b-2 ux4g-border-primary ux4g-text-brand-primary font-semibold"
              : "border-transparent ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary"
          }`}
        >
          Upload New File
        </button>
        {result && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "results"}
            onClick={() => setActiveTab("results")}
            className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer ${
              activeTab === "results"
                ? "border-b-2 ux4g-border-primary ux4g-text-brand-primary font-semibold"
                : "border-transparent ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary"
            }`}
          >
            Upload Results ({result.row_count} rows)
          </button>
        )}
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer ${
            activeTab === "history"
              ? "border-b-2 ux4g-border-primary ux4g-text-brand-primary font-semibold"
              : "border-transparent ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary"
          }`}
        >
          Upload History
        </button>
      </div>

      {/* Inline Save Success Banner */}
      {inlineSaveSuccess && (
        <Alert
          variant="success"
          title="Row Updated"
          onDismiss={() => setInlineSaveSuccess(null)}
        >
          {inlineSaveSuccess}
        </Alert>
      )}

      {/* Tab: Upload Form */}
      {activeTab === "upload" && (
        <Card variant="solid" className="max-w-3xl">
          <CardBody className="space-y-6">
            <form onSubmit={handleFileUpload} className="space-y-6">
              {uploadError && (
                <Alert
                  variant="error"
                  title="File Upload Rejected"
                  onDismiss={() => setUploadError(null)}
                >
                  {uploadError}
                </Alert>
              )}

              <div>
                <label
                  htmlFor="academic_year"
                  className="block text-sm font-semibold ux4g-text-neutral-primary mb-1.5"
                >
                  Target Academic Year
                </label>
                <Select
                  id="academic_year"
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  options={[
                    { value: "2026-27", label: "2026-27 (Current Cycle)" },
                    { value: "2025-26", label: "2025-26 (Previous Cycle)" },
                  ]}
                />
              </div>

              <div>
                <FileUpload
                  id="file-upload"
                  label="Student Enrolment File (.csv, .tsv, .xlsx, .xls)"
                  hint="Supports CSV, TSV, and Excel files up to 10,000 rows. Plain UTF-8 format."
                  accept=".csv,.tsv,.xlsx,.xls"
                  selectedFile={selectedFile}
                  onFileSelect={(file) => {
                    setSelectedFile(file);
                    setUploadError(null);
                  }}
                  onFileClear={() => setSelectedFile(null)}
                  disabled={isUploading}
                />
              </div>

              {/* Progress indicator during parse and rule validation */}
              {isUploading && (
                <div className="space-y-2 p-4 rounded-lg ux4g-bg-neutral-soft ux4g-border ux4g-border-neutral-subtle">
                  <div className="flex items-center justify-between text-xs font-semibold ux4g-text-neutral-primary">
                    <span className="flex items-center gap-2">
                      <Spinner size="sm" variant="primary" />
                      Parsing & Running Validation Rules...
                    </span>
                    <span>Processing</span>
                  </div>
                  <Progress value={65} max={100} label="Upload Progress" />
                  <p className="text-xs ux4g-text-neutral-tertiary">
                    Evaluating row-level formatting, duplicate APAAR IDs, course intake caps, and cross-institution enrolment.
                  </p>
                </div>
              )}

              <div className="ux4g-bg-neutral-soft rounded-lg p-4 text-xs ux4g-text-neutral-secondary space-y-2 border ux4g-border-neutral-subtle">
                <p className="font-semibold ux4g-text-neutral-primary">Upload Guidelines & Policies:</p>
                <ul className="list-disc pl-4 space-y-1">
                  <li>
                    <strong>Never silently discarded:</strong> All rows in readable files are saved as
                    drafts with their validation flags.
                  </li>
                  <li>
                    <strong>Re-uploading updates records:</strong> Matching records (same college,
                    course, year, APAAR ID) are updated without duplicating.
                  </li>
                  <li>
                    <strong>Required Columns:</strong> apaar_id, name, dob, gender, course, branch,
                    admission_year, enrolment_no, admission_date, admission_mode, seat_type,
                    reservation_category, nri, oci, foreign_national, country.
                  </li>
                  <li>
                    Date format must follow ISO standard <code>YYYY-MM-DD</code>.
                  </li>
                </ul>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  disabled={!selectedFile || isUploading}
                  isLoading={isUploading}
                >
                  Upload & Run Validation Engine
                </Button>
                {selectedFile && !isUploading && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setSelectedFile(null)}
                  >
                    Clear File
                  </Button>
                )}
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      {/* Tab: Results */}
      {activeTab === "results" && result && (
        <div className="space-y-6">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-neutral-secondary">Total Uploaded</div>
              <div className="text-2xl font-bold ux4g-text-neutral-primary mt-1">{result.summary.total_rows}</div>
              <div className="text-[11px] ux4g-text-neutral-tertiary mt-0.5">
                +{result.summary.inserted_count} new, {result.summary.updated_count} updated
              </div>
            </div>

            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-status-success">Valid (Clean)</div>
              <div className="text-2xl font-bold ux4g-text-status-success mt-1">{result.summary.valid_rows}</div>
              <div className="text-[11px] ux4g-text-status-success mt-0.5">Ready for submit</div>
            </div>

            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-status-warning">Flagged Rows</div>
              <div className="text-2xl font-bold ux4g-text-status-warning mt-1">{result.summary.flagged_rows}</div>
              <div className="text-[11px] ux4g-text-status-warning mt-0.5">Need attention</div>
            </div>

            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-status-error">Errors</div>
              <div className="text-2xl font-bold ux4g-text-status-error mt-1">{result.summary.error_count}</div>
              <div className="text-[11px] ux4g-text-status-error mt-0.5">Blocks submit</div>
            </div>

            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-status-error">Exceptions</div>
              <div className="text-2xl font-bold ux4g-text-status-error mt-1">{result.summary.exception_count}</div>
              <div className="text-[11px] ux4g-text-status-error mt-0.5">Needs justification</div>
            </div>

            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-status-warning">Warnings</div>
              <div className="text-2xl font-bold ux4g-text-status-warning mt-1">{result.summary.warning_count}</div>
              <div className="text-[11px] ux4g-text-status-warning mt-0.5">Review items</div>
            </div>

            <div className="ux4g-bg-neutral-elevated p-3.5 rounded-lg border ux4g-border-neutral-subtle shadow-xs">
              <div className="text-xs font-medium ux4g-text-neutral-secondary">Infos</div>
              <div className="text-2xl font-bold ux4g-text-neutral-primary mt-1">{result.summary.info_count}</div>
              <div className="text-[11px] ux4g-text-neutral-tertiary mt-0.5">Notices</div>
            </div>
          </div>

          {/* Action and Filter Toolbar */}
          <div className="ux4g-bg-neutral-elevated p-4 rounded-lg border ux4g-border-neutral-subtle shadow-xs space-y-3">
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2">
                <Select
                  aria-label="Filter records by flag severity level"
                  value={levelFilter}
                  onChange={(e) => {
                    setLevelFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  options={[
                    { value: "all", label: "All Flag Levels" },
                    { value: "error", label: "Errors Only" },
                    { value: "exception", label: "Exceptions Only" },
                    { value: "warning", label: "Warnings Only" },
                    { value: "clean", label: "Clean / Valid Only" },
                  ]}
                  className="w-full sm:w-40 text-xs"
                />

                <Select
                  aria-label="Filter records by course"
                  value={courseFilter}
                  onChange={(e) => {
                    setCourseFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  options={[
                    { value: "all", label: "All Courses" },
                    ...courses.map((c) => ({ value: c.name, label: c.name })),
                  ]}
                  className="w-full sm:w-48 text-xs"
                />

                <Input
                  aria-label="Search records by APAAR ID, student name, or enrolment number"
                  type="text"
                  placeholder="Search APAAR, Name, Enrolment..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full sm:w-56 text-xs"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownloadErrors(result.upload_id)}
                  disabled={
                    result.summary.error_count === 0 &&
                    result.summary.warning_count === 0 &&
                    result.summary.exception_count === 0
                  }
                >
                  Download Error File (CSV)
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setActiveTab("upload")}>
                  Upload Another File
                </Button>
              </div>
            </div>
          </div>

          {/* Rows Table with Sticky Header, Column Sorting, Row Focus & Accessible Region */}
          <div className="ux4g-bg-neutral-elevated rounded-lg border ux4g-border-neutral-subtle shadow-xs overflow-hidden">
            <Table
              size="m"
              columnDividers
              stickyHeader
              ariaLabel="Uploaded student enrolment records"
              className="text-xs"
            >
              <TableHeader sticky>
                <TableRow>
                  <TableHead
                    sortable
                    sortDirection={sortField === "row_number" ? sortDirection : "none"}
                    onSort={() => handleSort("row_number")}
                    className="w-16 text-center"
                  >
                    Row
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "apaar_id" ? sortDirection : "none"}
                    onSort={() => handleSort("apaar_id")}
                  >
                    APAAR ID
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "name" ? sortDirection : "none"}
                    onSort={() => handleSort("name")}
                  >
                    Student Name
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "course" ? sortDirection : "none"}
                    onSort={() => handleSort("course")}
                  >
                    Course / Branch
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "enrolment_no" ? sortDirection : "none"}
                    onSort={() => handleSort("enrolment_no")}
                  >
                    Enrolment #
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "admission_date" ? sortDirection : "none"}
                    onSort={() => handleSort("admission_date")}
                  >
                    Adm Date
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "seat_type" ? sortDirection : "none"}
                    onSort={() => handleSort("seat_type")}
                  >
                    Seat Type
                  </TableHead>
                  <TableHead
                    sortable
                    sortDirection={sortField === "status" ? sortDirection : "none"}
                    onSort={() => handleSort("status")}
                    className="text-center"
                  >
                    Status
                  </TableHead>
                  <TableHead>Validation Flags</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedRows.length === 0 ? (
                  <TableEmptyState
                    colSpan={10}
                    title="No records match current filters"
                    description="Try clearing your search query or selecting 'All Flag Levels'."
                  />
                ) : (
                  paginatedRows.map((r) => {
                    const isExpanded = !!expandedRows[r.row_number];
                    const isEditing = editingRowNumber === r.row_number;

                    const errCount = r.flags.filter((f) => f.level === "error").length;
                    const excCount = r.flags.filter((f) => f.level === "exception").length;
                    const warnCount = r.flags.filter((f) => f.level === "warning").length;
                    const infoCount = r.flags.filter((f) => f.level === "info").length;

                    return (
                      <React.Fragment key={r.row_number}>
                        <TableRow
                          focusable
                          className={r.flags.length > 0 ? "ux4g-bg-neutral-soft" : ""}
                        >
                          <TableCell className="text-center font-mono ux4g-text-neutral-tertiary">
                            #{r.row_number}
                          </TableCell>

                          <TableCell className="font-mono font-medium ux4g-text-neutral-primary">
                            {r.apaar_id || (
                              <span className="ux4g-text-status-error italic font-sans">
                                Missing
                              </span>
                            )}
                          </TableCell>

                          <TableCell className="font-medium ux4g-text-neutral-primary">
                            {isEditing ? (
                              <Input
                                aria-label="Student full name"
                                type="text"
                                value={editFormData.name ?? ""}
                                onChange={(e) =>
                                  setEditFormData({ ...editFormData, name: e.target.value })
                                }
                                className="text-xs py-1"
                              />
                            ) : (
                              r.name || (
                                <span className="ux4g-text-status-error italic">Empty</span>
                              )
                            )}
                          </TableCell>

                          <TableCell className="ux4g-text-neutral-secondary">
                            {isEditing ? (
                              <Select
                                aria-label="Course and branch"
                                value={editFormData.course ?? ""}
                                onChange={(e) =>
                                  setEditFormData({ ...editFormData, course: e.target.value })
                                }
                                options={[
                                  ...(courses.some(
                                    (c) =>
                                      c.name.toLowerCase() ===
                                      (editFormData.course || "").toLowerCase()
                                  )
                                    ? []
                                    : editFormData.course
                                    ? [
                                        {
                                          value: editFormData.course,
                                          label: `${editFormData.course} (Unapproved)`,
                                        },
                                      ]
                                    : []),
                                  ...courses.map((c) => ({ value: c.name, label: c.name })),
                                ]}
                                className="text-xs py-1"
                              />
                            ) : (
                              <div>
                                <div className="font-medium ux4g-text-neutral-primary">{r.course}</div>
                                {r.branch && (
                                  <div className="text-[10px] ux4g-text-neutral-tertiary">
                                    {r.branch}
                                  </div>
                                )}
                              </div>
                            )}
                          </TableCell>

                          <TableCell className="font-mono ux4g-text-neutral-secondary">
                            {isEditing ? (
                              <Input
                                aria-label="Enrolment number"
                                type="text"
                                value={editFormData.enrolment_no ?? ""}
                                onChange={(e) =>
                                  setEditFormData({
                                    ...editFormData,
                                    enrolment_no: e.target.value,
                                  })
                                }
                                className="text-xs py-1 w-28"
                              />
                            ) : (
                              r.enrolment_no
                            )}
                          </TableCell>

                          <TableCell className="ux4g-text-neutral-secondary whitespace-nowrap">
                            {isEditing ? (
                              <Input
                                aria-label="Admission date"
                                type="date"
                                value={editFormData.admission_date ?? ""}
                                onChange={(e) =>
                                  setEditFormData({
                                    ...editFormData,
                                    admission_date: e.target.value,
                                  })
                                }
                                className="text-xs py-1"
                              />
                            ) : (
                              r.admission_date
                            )}
                          </TableCell>

                          <TableCell className="ux4g-text-neutral-secondary">
                            {isEditing ? (
                              <Select
                                aria-label="Seat type"
                                value={editFormData.seat_type ?? "Regular"}
                                onChange={(e) =>
                                  setEditFormData({
                                    ...editFormData,
                                    seat_type: e.target.value,
                                  })
                                }
                                options={SEAT_TYPE_OPTIONS}
                                className="text-xs py-1"
                              />
                            ) : (
                              r.seat_type
                            )}
                          </TableCell>

                          <TableCell className="text-center">
                            {r.status === "valid" ? (
                              <Badge variant="success" size="sm">
                                Valid
                              </Badge>
                            ) : (
                              <Badge variant="danger" size="sm">
                                Flagged
                              </Badge>
                            )}
                          </TableCell>

                          <TableCell>
                            {r.flags.length === 0 ? (
                              <span className="ux4g-text-status-success font-medium text-[11px] flex items-center gap-1">
                                <Icon name="check_circle" size="sm" color="success" aria-hidden="true" />
                                Passed 0 flags
                              </span>
                            ) : (
                              <div className="flex flex-wrap items-center gap-1.5">
                                {errCount > 0 && (
                                  <button
                                    type="button"
                                    onClick={() => toggleRowExpanded(r.row_number)}
                                    className="cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary rounded"
                                    aria-label={`Error ${errCount}`}
                                  >
                                    <FlagBadge level="error" count={errCount} />
                                  </button>
                                )}
                                {excCount > 0 && (
                                  <button
                                    type="button"
                                    onClick={() => toggleRowExpanded(r.row_number)}
                                    className="cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary rounded"
                                    aria-label={`Exception ${excCount}`}
                                  >
                                    <FlagBadge level="exception" count={excCount} />
                                  </button>
                                )}
                                {warnCount > 0 && (
                                  <button
                                    type="button"
                                    onClick={() => toggleRowExpanded(r.row_number)}
                                    className="cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary rounded"
                                    aria-label={`Warning ${warnCount}`}
                                  >
                                    <FlagBadge level="warning" count={warnCount} />
                                  </button>
                                )}
                                {infoCount > 0 && (
                                  <button
                                    type="button"
                                    onClick={() => toggleRowExpanded(r.row_number)}
                                    className="cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary rounded"
                                    aria-label={`Info ${infoCount}`}
                                  >
                                    <FlagBadge level="info" count={infoCount} />
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => toggleRowExpanded(r.row_number)}
                                  aria-expanded={isExpanded}
                                  className="text-[11px] ux4g-text-brand-primary hover:underline ml-1 cursor-pointer font-medium"
                                >
                                  {isExpanded ? "Hide" : "Details"}
                                </button>
                              </div>
                            )}
                          </TableCell>

                          <TableCell className="text-right whitespace-nowrap">
                            {isEditing ? (
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  size="sm"
                                  variant="primary"
                                  onClick={() => handleSaveInlineEdit(r.row_number)}
                                  disabled={isSavingRow}
                                  isLoading={isSavingRow}
                                >
                                  {isSavingRow ? "Saving..." : "Save & Re-validate"}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={handleCancelInlineEdit}
                                  disabled={isSavingRow}
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleStartInlineEdit(r)}
                                  title="Edit fields and re-validate immediately"
                                >
                                  Inline Edit
                                </Button>
                                {r.student_id && (
                                  <Link to={`/college/students/${r.student_id}/edit`}>
                                    <Button
                                      size="sm"
                                      variant="tertiary"
                                      title="Open full edit form"
                                    >
                                      Form
                                    </Button>
                                  </Link>
                                )}
                              </div>
                            )}
                          </TableCell>
                        </TableRow>

                        {/* Expanded Flag Detail Drawer */}
                        {isExpanded && r.flags.length > 0 && (
                          <TableRow className="ux4g-bg-neutral-soft border-b ux4g-border-neutral-subtle">
                            <TableCell colSpan={10} className="py-3 px-6">
                              <div className="space-y-2">
                                <div className="text-xs font-semibold ux4g-text-neutral-primary">
                                  Validation Issues for Row #{r.row_number} ({r.flags.length} total):
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                                  {r.flags.map((fl, fIdx) => (
                                    <div
                                      key={fIdx}
                                      className="p-3 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated text-xs space-y-1.5 shadow-2xs"
                                    >
                                      <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                          <FlagBadge level={fl.level} />
                                          <span className="font-mono font-semibold ux4g-text-neutral-primary">
                                            {fl.rule_code}
                                          </span>
                                        </div>
                                        {fl.field && (
                                          <span className="font-mono text-[10px] ux4g-bg-neutral-soft ux4g-text-neutral-secondary px-1.5 py-0.5 rounded border ux4g-border-neutral-subtle">
                                            field: {fl.field}
                                          </span>
                                        )}
                                      </div>
                                      <p className="ux4g-text-neutral-primary font-medium">{fl.message}</p>
                                      {fl.fix_hint && (
                                        <p className="ux4g-text-neutral-secondary text-[11px]">
                                          <strong className="ux4g-text-neutral-primary">How to fix:</strong>{" "}
                                          {fl.fix_hint}
                                        </p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </TableBody>
            </Table>

            {/* Pagination Controls */}
            {totalFilteredRows > 0 && (
              <TablePagination
                currentPage={currentSafePage}
                totalPages={totalPages}
                totalItems={totalFilteredRows}
                pageSize={pageSize}
                pageSizeOptions={[10, 25, 50, 100, 250, 500]}
                onPageChange={setCurrentPage}
                onPageSizeChange={(newSize) => {
                  setPageSize(newSize);
                  setCurrentPage(1);
                }}
                ariaLabel="Upload results pagination"
              />
            )}
          </div>
        </div>
      )}

      {/* Tab: History */}
      {activeTab === "history" && (
        <div className="ux4g-bg-neutral-elevated rounded-lg border ux4g-border-neutral-subtle shadow-xs overflow-hidden">
          <div className="p-4 border-b ux4g-border-neutral-subtle flex items-center justify-between">
            <h2 className="text-sm font-semibold ux4g-text-neutral-primary">Historical Bulk Uploads</h2>
            <Button size="sm" variant="outline" onClick={() => setActiveTab("upload")}>
              New Upload
            </Button>
          </div>

          {isLoadingHistory ? (
            <Table size="m" className="text-xs">
              <TableHeader>
                <TableRow>
                  <TableHead>Upload ID</TableHead>
                  <TableHead>Filename</TableHead>
                  <TableHead>Date / Time</TableHead>
                  <TableHead className="text-center">Total Rows</TableHead>
                  <TableHead className="text-center">Valid</TableHead>
                  <TableHead className="text-center">Flagged</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableSkeletonRows columns={8} rows={4} />
              </TableBody>
            </Table>
          ) : historyItems.length === 0 ? (
            <div className="p-8 text-center">
              <EmptyState
                title="No upload history found"
                description="Upload student enrolment files to track batch history here."
              />
            </div>
          ) : (
            <Table
              size="m"
              columnDividers
              ariaLabel="Historical student enrolment uploads"
              className="text-xs"
            >
              <TableHeader>
                <TableRow>
                  <TableHead>Upload ID</TableHead>
                  <TableHead>Filename</TableHead>
                  <TableHead>Date / Time</TableHead>
                  <TableHead className="text-center">Total Rows</TableHead>
                  <TableHead className="text-center">Valid</TableHead>
                  <TableHead className="text-center">Flagged</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyItems.map((h) => {
                  const sm = h.summary_json?.summary;
                  return (
                    <TableRow key={h.id} focusable>
                      <TableCell className="font-mono font-medium ux4g-text-neutral-primary">
                        #{h.id}
                      </TableCell>
                      <TableCell className="font-medium ux4g-text-neutral-primary">
                        {h.filename}
                      </TableCell>
                      <TableCell className="ux4g-text-neutral-secondary whitespace-nowrap">
                        {new Date(h.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-center font-bold ux4g-text-neutral-primary">
                        {h.row_count}
                      </TableCell>
                      <TableCell className="text-center font-bold ux4g-text-status-success">
                        {sm?.valid_rows ?? "-"}
                      </TableCell>
                      <TableCell className="text-center font-bold ux4g-text-status-warning">
                        {sm?.flagged_rows ?? "-"}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="success" size="sm">
                          {h.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleViewPastUpload(h.id)}
                        >
                          View Results
                        </Button>
                        <Button
                          size="sm"
                          variant="tertiary"
                          onClick={() => handleDownloadErrors(h.id)}
                          title="Download error file for this upload"
                        >
                          Errors
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      )}
    </div>
  );
}
