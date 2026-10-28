import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listCourses, type CourseResponse } from "../api/institutions";
import {
  deleteStudent,
  getStudents,
  type StudentListResponse,
  type StudentResponse,
  type StudentValidationFlag,
} from "../api/students";
import { downloadStudentCertificate } from "../api/verification";
import { useAuth } from "../auth/AuthContext";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/Table";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

const ACADEMIC_YEAR_OPTIONS = [
  { value: "2026-27", label: "2026-27 (Current Admissions)" },
  { value: "2025-26", label: "2025-26 (Past History)" },
];

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "valid", label: "Valid (Compliant)" },
  { value: "flagged", label: "Flagged (Has Flags)" },
  { value: "submitted", label: "Submitted" },
  { value: "withdrawn", label: "Withdrawn" },
  { value: "transferred", label: "Transferred" },
];

const LEVEL_FILTER_OPTIONS = [
  { value: "all", label: "All Validation Levels" },
  { value: "error", label: "Error (Blocks Submit)" },
  { value: "exception", label: "Exception (Over-intake, etc.)" },
  { value: "warning", label: "Warning (Advisory)" },
  { value: "info", label: "Info (Informational)" },
  { value: "clean", label: "Clean (No Flags)" },
];

export const StudentsListPage: React.FC = () => {
  useDocumentTitle("Student Directory");
  const { user } = useAuth();
  const navigate = useNavigate();
  const institutionId = user?.institution_id ?? 1;
  const isViewer = user?.role === "college_viewer";

  // Filter & Pagination States
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [courseId, setCourseId] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [levelFilter, setLevelFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const limit = 15;

  // Data States
  const [courses, setCourses] = useState<CourseResponse[]>([]);
  const [data, setData] = useState<StudentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Delete Modal State
  const [studentToDelete, setStudentToDelete] = useState<StudentResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [downloadingCertId, setDownloadingCertId] = useState<number | null>(null);

  const handleDownloadCertificate = async (student: StudentResponse) => {
    try {
      setDownloadingCertId(student.id);
      await downloadStudentCertificate(institutionId, student.id, `certificate_${student.enrolment_no}.pdf`);
    } catch (err) {
      setErrorMessage((err as Error).message || "Failed to download degree certificate.");
    } finally {
      setDownloadingCertId(null);
    }
  };

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search.trim());
      setPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [search]);

  // Load Courses for Filter Dropdown
  useEffect(() => {
    async function loadCourses() {
      try {
        const courseList = await listCourses(institutionId);
        setCourses(courseList);
      } catch (err) {
        console.error("Failed to load institution courses:", err);
      }
    }
    loadCourses();
  }, [institutionId]);

  // Load Students Directory
  const loadStudents = useCallback(async () => {
    try {
      setLoading(true);
      setErrorMessage(null);
      const res = await getStudents(institutionId, {
        academic_year: academicYear,
        course_id: courseId !== "all" ? Number(courseId) : undefined,
        status: statusFilter,
        level: levelFilter,
        search: debouncedSearch || undefined,
        page,
        limit,
      });
      setData(res);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load student records"
      );
    } finally {
      setLoading(false);
    }
  }, [institutionId, academicYear, courseId, statusFilter, levelFilter, debouncedSearch, page, limit]);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  const handleDeleteConfirm = async () => {
    if (!studentToDelete) return;
    try {
      setIsDeleting(true);
      await deleteStudent(institutionId, studentToDelete.id);
      setActionSuccessMessage(
        `Draft record for ${studentToDelete.name} (APAAR: ${studentToDelete.apaar_id}) was deleted.`
      );
      setStudentToDelete(null);
      await loadStudents();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to delete student draft"
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClearFilters = () => {
    setCourseId("all");
    setStatusFilter("all");
    setLevelFilter("all");
    setSearch("");
    setPage(1);
  };

  const courseOptions = [
    { value: "all", label: "All Approved Courses" },
    ...courses.map((c) => ({
      value: c.id.toString(),
      label: `${c.name} (${c.branch})`,
    })),
  ];

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 space-y-6">
      {/* Top Header & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Student Records Directory</h1>
          <p className="text-sm text-slate-600 mt-1">
            Manage enrolled students keyed by APAAR ID. Filter by validation flags, edit drafts, or add single records.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/college/upload">
            <Button variant="outline" size="sm">
              Bulk CSV Upload
            </Button>
          </Link>
          {!isViewer && (
            <Link to="/college/students/new">
              <Button variant="primary" size="sm">
                + Add Student
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Action Notification */}
      {actionSuccessMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-sm text-emerald-800 flex items-center justify-between">
          <span>{actionSuccessMessage}</span>
          <button
            onClick={() => setActionSuccessMessage(null)}
            className="text-emerald-700 font-bold hover:text-emerald-900"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800 flex items-center justify-between">
          <span>{errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-red-700 font-bold hover:text-red-900"
          >
            ✕
          </button>
        </div>
      )}

      {/* Statistical Summary Overview Cards */}
      {data?.stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Total Enrolled
            </span>
            <div className="mt-2 text-2xl font-bold text-slate-900">
              {data.stats.total.toLocaleString()}
            </div>
            <span className="text-xs text-slate-400">Academic Year {academicYear}</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Compliant (Clean)
            </span>
            <div className="mt-2 text-2xl font-bold text-emerald-600">
              {data.stats.valid.toLocaleString()}
            </div>
            <span className="text-xs text-emerald-700 font-medium">0 active errors</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Flagged Records
            </span>
            <div className="mt-2 text-2xl font-bold text-amber-600">
              {data.stats.flagged.toLocaleString()}
            </div>
            <div className="flex gap-1.5 mt-1">
              {data.stats.error_flags_count > 0 && (
                <span className="text-[10px] bg-red-100 text-red-800 px-1.5 py-0.5 rounded font-medium">
                  {data.stats.error_flags_count} Err
                </span>
              )}
              {data.stats.exception_flags_count > 0 && (
                <span className="text-[10px] bg-red-50 text-red-700 border border-red-300 px-1.5 py-0.5 rounded font-medium">
                  {data.stats.exception_flags_count} Exc
                </span>
              )}
              {data.stats.warning_flags_count > 0 && (
                <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-medium">
                  {data.stats.warning_flags_count} Warn
                </span>
              )}
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Unsubmitted Drafts
            </span>
            <div className="mt-2 text-2xl font-bold text-slate-700">
              {data.stats.draft.toLocaleString()}
            </div>
            <span className="text-xs text-slate-400">Pending review</span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          <Select
            label="Academic Year"
            value={academicYear}
            onChange={(e) => {
              setAcademicYear(e.target.value);
              setPage(1);
            }}
            options={ACADEMIC_YEAR_OPTIONS}
          />

          <Select
            label="Approved Course"
            value={courseId}
            onChange={(e) => {
              setCourseId(e.target.value);
              setPage(1);
            }}
            options={courseOptions}
          />

          <Select
            label="Record Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            options={STATUS_FILTER_OPTIONS}
          />

          <Select
            label="Validation Level"
            value={levelFilter}
            onChange={(e) => {
              setLevelFilter(e.target.value);
              setPage(1);
            }}
            options={LEVEL_FILTER_OPTIONS}
          />

          <div className="flex flex-col justify-end">
            <Input
              label="Search Students"
              placeholder="Search APAAR, name, enrolment..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
          <span>
            Showing {data?.items.length || 0} of {data?.total || 0} matching records
          </span>
          <button
            type="button"
            onClick={handleClearFilters}
            className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Students Data Table */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] bg-white rounded-lg border border-slate-200">
          <LoadingSpinner size="lg" />
          <p className="mt-3 text-sm text-slate-600">Loading student directory...</p>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="bg-white rounded-lg border border-slate-200 p-8">
          <EmptyState
            title="No Student Records Found"
            description={
              debouncedSearch || statusFilter !== "all" || levelFilter !== "all" || courseId !== "all"
                ? "No student records match the active search and filter criteria. Try adjusting your filters."
                : "No students have been added for this academic year yet. Use 'Add Student' or 'Bulk CSV Upload' to get started."
            }
            actionLabel={!isViewer ? "+ Add Student" : undefined}
            onAction={!isViewer ? () => navigate("/college/students/new") : undefined}
          />
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden space-y-4 p-1">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>APAAR ID</TableHead>
                <TableHead>Student Name</TableHead>
                <TableHead>Course & Branch</TableHead>
                <TableHead>Enrolment No</TableHead>
                <TableHead>Admission Date</TableHead>
                <TableHead>Seat Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Validation Flags</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((student) => {
                const canModify = !student.is_locked && !isViewer && !["submitted", "accepted", "verified"].includes(student.status);
                return (
                  <TableRow key={student.id} className="hover:bg-slate-50 transition-colors">
                    <TableCell className="font-mono text-xs font-semibold text-slate-900">
                      {student.apaar_id}
                    </TableCell>
                    <TableCell>
                      <Link
                        to={`/college/students/${student.id}`}
                        className="font-medium text-slate-900 hover:text-blue-600 underline decoration-slate-300 block"
                        title="View student profile"
                      >
                        {student.name}
                      </Link>
                      <div className="text-xs text-slate-400 capitalize">
                        {student.gender} • {student.reservation_category}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs font-medium text-slate-800">
                        {student.course_name}
                      </div>
                      <div className="text-[11px] text-slate-500">{student.branch}</div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-700">
                      {student.enrolment_no}
                    </TableCell>
                    <TableCell className="text-xs text-slate-600">
                      <div>{student.admission_date}</div>
                      <div className="text-[10px] text-slate-400">{student.admission_mode}</div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        size="sm"
                        variant={student.seat_type === "Supernumerary" ? "warning" : "neutral"}
                      >
                        {student.seat_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        size="sm"
                        variant={
                          student.status === "valid"
                            ? "success"
                            : student.status === "flagged"
                            ? "warning"
                            : student.status === "submitted"
                            ? "primary"
                            : "neutral"
                        }
                      >
                        {student.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {student.flags && student.flags.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {student.flags.slice(0, 2).map((fl: StudentValidationFlag, i: number) => (
                            <FlagBadge key={i} level={fl.level} label={fl.rule_code} />
                          ))}
                          {student.flags.length > 2 && (
                            <Badge size="sm" variant="neutral">
                              +{student.flags.length - 2} more
                            </Badge>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-emerald-700 font-medium">✓ Clean</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          className="px-2 py-1 text-xs text-indigo-700 border-indigo-200 hover:bg-indigo-50"
                          title="Download sample degree certificate PDF with APAAR ID and QR code"
                          isLoading={downloadingCertId === student.id}
                          disabled={downloadingCertId === student.id}
                          onClick={() => handleDownloadCertificate(student)}
                        >
                          Certificate
                        </Button>
                        {canModify ? (
                          <>
                            <Link to={`/college/students/${student.id}/edit`}>
                              <Button variant="outline" size="sm" className="px-2 py-1 text-xs">
                                Edit
                              </Button>
                            </Link>
                            <Button
                              variant="danger"
                              size="sm"
                              className="px-2 py-1 text-xs"
                              onClick={() => setStudentToDelete(student)}
                            >
                              Delete
                            </Button>
                          </>
                        ) : (
                          <Link to={`/college/students/${student.id}/edit`}>
                            <Button variant="ghost" size="sm" className="px-2 py-1 text-xs">
                              View
                            </Button>
                          </Link>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {/* Pagination Controls */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
              <span className="text-xs text-slate-500">
                Page {data.page} of {data.total_pages} ({data.total} total students)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= data.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {studentToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200 text-left">
            <h3 className="text-lg font-bold text-slate-900">Confirm Draft Deletion</h3>
            <p className="text-sm text-slate-600">
              Are you sure you want to delete the draft student record for{" "}
              <strong>{studentToDelete.name}</strong> (APAAR: <code>{studentToDelete.apaar_id}</code>)?
            </p>
            <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-800">
              This will remove the student draft and all associated validation flags from the system.
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStudentToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete Draft"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default StudentsListPage;
