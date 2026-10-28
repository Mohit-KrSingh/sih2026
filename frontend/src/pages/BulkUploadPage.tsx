import React, { useEffect, useState } from "react";
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
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Input } from "../components/ui/Input";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

const SEAT_TYPE_OPTIONS = [
  { value: "Regular", label: "Regular" },
  { value: "Supernumerary", label: "Supernumerary" },
];

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
      // Find course id
      let courseId = editFormData.student_id ? 1 : 1;
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

  // Filter rows
  const filteredRows = (result?.rows || []).filter((r) => {
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              to="/college/students"
              className="text-xs font-semibold uppercase tracking-wider text-primary-600 hover:text-primary-800"
            >
              Students Directory
            </Link>
            <span className="text-slate-400">/</span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Bulk Upload
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Bulk Student Enrolment Upload
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Upload CSV or Excel files with APAAR IDs to enrol students, execute pure rule validation,
            and resolve flags.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleDownloadTemplate}
            title="Download blank CSV template with required lowercase headers"
          >
            Download CSV Template
          </Button>
          {result && (
            <Button
              variant="secondary"
              onClick={() => handleDownloadErrors(result.upload_id)}
              disabled={result.summary.error_count === 0 && result.summary.warning_count === 0}
            >
              Download Error File
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          type="button"
          onClick={() => setActiveTab("upload")}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "upload"
              ? "border-primary-600 text-primary-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Upload New File
        </button>
        {result && (
          <button
            type="button"
            onClick={() => setActiveTab("results")}
            className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "results"
                ? "border-primary-600 text-primary-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Upload Results ({result.row_count} rows)
          </button>
        )}
        <button
          type="button"
          onClick={() => setActiveTab("history")}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "history"
              ? "border-primary-600 text-primary-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Upload History
        </button>
      </div>

      {/* Inline Save Success Banner */}
      {inlineSaveSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-sm text-emerald-800 flex justify-between items-center">
          <span>{inlineSaveSuccess}</span>
          <button
            type="button"
            onClick={() => setInlineSaveSuccess(null)}
            className="text-emerald-700 font-bold hover:text-emerald-900"
          >
            ×
          </button>
        </div>
      )}

      {/* Tab: Upload Form */}
      {activeTab === "upload" && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 max-w-3xl shadow-sm">
          <form onSubmit={handleFileUpload} className="space-y-6">
            {uploadError && (
              <ErrorState
                title="File Upload Rejected"
                message={uploadError}
                onRetry={() => setUploadError(null)}
              />
            )}

            <div>
              <label htmlFor="academic_year" className="block text-sm font-medium text-slate-700 mb-1">
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
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Student Enrolment File (.csv, .tsv, .xlsx, .xls)
              </label>
              <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:bg-slate-50 transition-colors">
                <input
                  type="file"
                  id="file-upload"
                  accept=".csv,.tsv,.xlsx,.xls"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                      setUploadError(null);
                    }
                  }}
                  className="hidden"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer flex flex-col items-center justify-center space-y-2"
                >
                  <div className="w-12 h-12 rounded-full bg-primary-50 text-primary-600 flex items-center justify-center">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-slate-700">
                    {selectedFile ? selectedFile.name : "Click to select a file or drag and drop"}
                  </span>
                  <span className="text-xs text-slate-500">
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB`
                      : "Supports CSV, TSV, and Excel files up to 10,000 rows"}
                  </span>
                </label>
              </div>
            </div>

            <div className="bg-slate-50 rounded-lg p-4 text-xs text-slate-600 space-y-1.5 border border-slate-100">
              <p className="font-semibold text-slate-700">Upload Guidelines & Policies:</p>
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

            <div className="flex items-center gap-3 pt-2">
              <Button type="submit" variant="primary" disabled={!selectedFile || isUploading}>
                {isUploading ? (
                  <span className="flex items-center gap-2">
                    <LoadingSpinner size="sm" />
                    Parsing & Validating...
                  </span>
                ) : (
                  "Upload & Run Validation Engine"
                )}
              </Button>
              {selectedFile && !isUploading && (
                <Button type="button" variant="outline" onClick={() => setSelectedFile(null)}>
                  Clear File
                </Button>
              )}
            </div>
          </form>
        </div>
      )}

      {/* Tab: Results */}
      {activeTab === "results" && result && (
        <div className="space-y-6">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-slate-500">Total Uploaded</div>
              <div className="text-2xl font-bold text-slate-900 mt-1">{result.summary.total_rows}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                +{result.summary.inserted_count} new, {result.summary.updated_count} updated
              </div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-emerald-700">Valid (Clean)</div>
              <div className="text-2xl font-bold text-emerald-600 mt-1">{result.summary.valid_rows}</div>
              <div className="text-[11px] text-emerald-600 mt-0.5">Ready for submit</div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-amber-700">Flagged Rows</div>
              <div className="text-2xl font-bold text-amber-600 mt-1">{result.summary.flagged_rows}</div>
              <div className="text-[11px] text-amber-600 mt-0.5">Need attention</div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-red-700">Errors</div>
              <div className="text-2xl font-bold text-red-600 mt-1">{result.summary.error_count}</div>
              <div className="text-[11px] text-red-500 mt-0.5">Blocks submit</div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-red-700">Exceptions</div>
              <div className="text-2xl font-bold text-red-600 mt-1">{result.summary.exception_count}</div>
              <div className="text-[11px] text-red-500 mt-0.5">Needs justification</div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-amber-700">Warnings</div>
              <div className="text-2xl font-bold text-amber-600 mt-1">{result.summary.warning_count}</div>
              <div className="text-[11px] text-amber-600 mt-0.5">Review items</div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs font-medium text-slate-500">Infos</div>
              <div className="text-2xl font-bold text-slate-600 mt-1">{result.summary.info_count}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Notices</div>
            </div>
          </div>

          {/* Action and Filter Toolbar */}
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <Select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                  options={[
                    { value: "all", label: "All Flag Levels" },
                    { value: "error", label: "Errors Only" },
                    { value: "exception", label: "Exceptions Only" },
                    { value: "warning", label: "Warnings Only" },
                    { value: "clean", label: "Clean / Valid Only" },
                  ]}
                  className="w-40 text-xs"
                />

                <Select
                  value={courseFilter}
                  onChange={(e) => setCourseFilter(e.target.value)}
                  options={[
                    { value: "all", label: "All Courses" },
                    ...courses.map((c) => ({ value: c.name, label: c.name })),
                  ]}
                  className="w-48 text-xs"
                />

                <Input
                  type="text"
                  placeholder="Search APAAR, Name, Enrolment..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-56 text-xs"
                />
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownloadErrors(result.upload_id)}
                  disabled={result.summary.error_count === 0 && result.summary.warning_count === 0}
                >
                  Download Error File (CSV)
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setActiveTab("upload")}>
                  Upload Another File
                </Button>
              </div>
            </div>
          </div>

          {/* Rows Table */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-3 w-12 text-center">Row</th>
                    <th className="py-3 px-3">APAAR ID</th>
                    <th className="py-3 px-3">Student Name</th>
                    <th className="py-3 px-3">Course / Branch</th>
                    <th className="py-3 px-3">Enrolment #</th>
                    <th className="py-3 px-3">Adm Date</th>
                    <th className="py-3 px-3">Seat Type</th>
                    <th className="py-3 px-3 text-center">Status</th>
                    <th className="py-3 px-3">Validation Flags</th>
                    <th className="py-3 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-normal">
                  {filteredRows.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-slate-500">
                        <EmptyState
                          title="No records match current filters"
                          description="Try clearing your search query or selecting 'All Flag Levels'."
                        />
                      </td>
                    </tr>
                  ) : (
                    filteredRows.map((r) => {
                      const isExpanded = !!expandedRows[r.row_number];
                      const isEditing = editingRowNumber === r.row_number;

                      const errCount = r.flags.filter((f) => f.level === "error").length;
                      const excCount = r.flags.filter((f) => f.level === "exception").length;
                      const warnCount = r.flags.filter((f) => f.level === "warning").length;
                      const infoCount = r.flags.filter((f) => f.level === "info").length;

                      return (
                        <React.Fragment key={r.row_number}>
                          <tr
                            className={`hover:bg-slate-50 transition-colors ${
                              r.flags.length > 0 ? "bg-red-50/20" : ""
                            }`}
                          >
                            <td className="py-3 px-3 text-center font-mono text-slate-500">
                              #{r.row_number}
                            </td>

                            <td className="py-3 px-3 font-mono font-medium text-slate-900">
                              {r.apaar_id || <span className="text-red-500 italic">Missing</span>}
                            </td>

                            <td className="py-3 px-3 font-medium text-slate-900">
                              {isEditing ? (
                                <input
                                  type="text"
                                  className="border border-slate-300 rounded px-2 py-1 text-xs w-full"
                                  value={editFormData.name ?? ""}
                                  onChange={(e) =>
                                    setEditFormData({ ...editFormData, name: e.target.value })
                                  }
                                />
                              ) : (
                                r.name || <span className="text-red-500 italic">Empty</span>
                              )}
                            </td>

                            <td className="py-3 px-3 text-slate-700">
                              {isEditing ? (
                                <select
                                  className="border border-slate-300 rounded px-2 py-1 text-xs w-full"
                                  value={editFormData.course ?? ""}
                                  onChange={(e) =>
                                    setEditFormData({ ...editFormData, course: e.target.value })
                                  }
                                >
                                  {courses.map((c) => (
                                    <option key={c.id} value={c.name}>
                                      {c.name}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                <div>
                                  <div>{r.course}</div>
                                  {r.branch && <div className="text-[10px] text-slate-400">{r.branch}</div>}
                                </div>
                              )}
                            </td>

                            <td className="py-3 px-3 font-mono text-slate-600">
                              {isEditing ? (
                                <input
                                  type="text"
                                  className="border border-slate-300 rounded px-2 py-1 text-xs w-28"
                                  value={editFormData.enrolment_no ?? ""}
                                  onChange={(e) =>
                                    setEditFormData({
                                      ...editFormData,
                                      enrolment_no: e.target.value,
                                    })
                                  }
                                />
                              ) : (
                                r.enrolment_no
                              )}
                            </td>

                            <td className="py-3 px-3 text-slate-600 whitespace-nowrap">
                              {isEditing ? (
                                <input
                                  type="date"
                                  className="border border-slate-300 rounded px-2 py-1 text-xs"
                                  value={editFormData.admission_date ?? ""}
                                  onChange={(e) =>
                                    setEditFormData({
                                      ...editFormData,
                                      admission_date: e.target.value,
                                    })
                                  }
                                />
                              ) : (
                                r.admission_date
                              )}
                            </td>

                            <td className="py-3 px-3 text-slate-600">
                              {isEditing ? (
                                <select
                                  className="border border-slate-300 rounded px-2 py-1 text-xs"
                                  value={editFormData.seat_type ?? "Regular"}
                                  onChange={(e) =>
                                    setEditFormData({
                                      ...editFormData,
                                      seat_type: e.target.value,
                                    })
                                  }
                                >
                                  {SEAT_TYPE_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={opt.value}>
                                      {opt.label}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                r.seat_type
                              )}
                            </td>

                            <td className="py-3 px-3 text-center">
                              {r.status === "valid" ? (
                                <Badge variant="success" size="sm">
                                  Valid
                                </Badge>
                              ) : (
                                <Badge variant="danger" size="sm">
                                  Flagged
                                </Badge>
                              )}
                            </td>

                            <td className="py-3 px-3">
                              {r.flags.length === 0 ? (
                                <span className="text-emerald-600 font-medium text-[11px]">
                                  Passed 0 flags
                                </span>
                              ) : (
                                <div className="flex flex-wrap items-center gap-1">
                                  {errCount > 0 && (
                                    <button
                                      type="button"
                                      onClick={() => toggleRowExpanded(r.row_number)}
                                    >
                                      <FlagBadge level="error" count={errCount} />
                                    </button>
                                  )}
                                  {excCount > 0 && (
                                    <button
                                      type="button"
                                      onClick={() => toggleRowExpanded(r.row_number)}
                                    >
                                      <FlagBadge level="exception" count={excCount} />
                                    </button>
                                  )}
                                  {warnCount > 0 && (
                                    <button
                                      type="button"
                                      onClick={() => toggleRowExpanded(r.row_number)}
                                    >
                                      <FlagBadge level="warning" count={warnCount} />
                                    </button>
                                  )}
                                  {infoCount > 0 && (
                                    <button
                                      type="button"
                                      onClick={() => toggleRowExpanded(r.row_number)}
                                    >
                                      <FlagBadge level="info" count={infoCount} />
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => toggleRowExpanded(r.row_number)}
                                    className="text-[11px] text-primary-600 hover:underline ml-1"
                                  >
                                    {isExpanded ? "Hide" : "Details"}
                                  </button>
                                </div>
                              )}
                            </td>

                            <td className="py-3 px-3 text-right whitespace-nowrap">
                              {isEditing ? (
                                <div className="flex items-center justify-end gap-1">
                                  <Button
                                    size="sm"
                                    variant="primary"
                                    onClick={() => handleSaveInlineEdit(r.row_number)}
                                    disabled={isSavingRow}
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
                                      <Button size="sm" variant="ghost" title="Open full edit form">
                                        Form
                                      </Button>
                                    </Link>
                                  )}
                                </div>
                              )}
                            </td>
                          </tr>

                          {/* Expanded Flag Detail Drawer */}
                          {isExpanded && r.flags.length > 0 && (
                            <tr className="bg-slate-50/70 border-b border-slate-200">
                              <td colSpan={10} className="py-3 px-6">
                                <div className="space-y-2">
                                  <div className="text-xs font-semibold text-slate-700">
                                    Validation Issues for Row #{r.row_number} ({r.flags.length} total):
                                  </div>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                    {r.flags.map((fl, fIdx) => (
                                      <div
                                        key={fIdx}
                                        className="p-2.5 rounded border border-slate-200 bg-white text-xs space-y-1 shadow-2xs"
                                      >
                                        <div className="flex items-center justify-between">
                                          <div className="flex items-center gap-1.5">
                                            <FlagBadge level={fl.level} />
                                            <span className="font-mono font-semibold text-slate-800">
                                              {fl.rule_code}
                                            </span>
                                          </div>
                                          {fl.field && (
                                            <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                                              field: {fl.field}
                                            </span>
                                          )}
                                        </div>
                                        <p className="text-slate-800 font-medium">{fl.message}</p>
                                        {fl.fix_hint && (
                                          <p className="text-slate-500 text-[11px]">
                                            <strong className="text-slate-700">How to fix:</strong>{" "}
                                            {fl.fix_hint}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab: History */}
      {activeTab === "history" && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Historical Bulk Uploads</h2>
            <Button size="sm" variant="outline" onClick={() => setActiveTab("upload")}>
              New Upload
            </Button>
          </div>

          {isLoadingHistory ? (
            <div className="p-8 text-center">
              <LoadingSpinner size="md" />
              <p className="text-xs text-slate-500 mt-2">Loading upload history...</p>
            </div>
          ) : historyItems.length === 0 ? (
            <div className="p-8 text-center text-slate-500">
              <EmptyState
                title="No upload history found"
                description="Upload student enrolment files to track batch history here."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Upload ID</th>
                    <th className="py-3 px-4">Filename</th>
                    <th className="py-3 px-4">Date / Time</th>
                    <th className="py-3 px-4 text-center">Total Rows</th>
                    <th className="py-3 px-4 text-center">Valid</th>
                    <th className="py-3 px-4 text-center">Flagged</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {historyItems.map((h) => {
                    const sm = h.summary_json?.summary;
                    return (
                      <tr key={h.id} className="hover:bg-slate-50">
                        <td className="py-3 px-4 font-mono font-medium text-slate-900">#{h.id}</td>
                        <td className="py-3 px-4 font-medium text-slate-900">{h.filename}</td>
                        <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                          {new Date(h.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-center font-bold text-slate-900">{h.row_count}</td>
                        <td className="py-3 px-4 text-center font-bold text-emerald-600">
                          {sm?.valid_rows ?? "-"}
                        </td>
                        <td className="py-3 px-4 text-center font-bold text-amber-600">
                          {sm?.flagged_rows ?? "-"}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge variant="success" size="sm">
                            {h.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap space-x-2">
                          <Button size="sm" variant="outline" onClick={() => handleViewPastUpload(h.id)}>
                            View Results
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDownloadErrors(h.id)}
                            title="Download error file for this upload"
                          >
                            Errors
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
