import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  listInstitutions,
  listCourses,
  updateCourseIntake,
  getIntakeHistory,
  updateInstitutionApprovalStatus,
  type InstitutionResponse,
  type CourseResponse,
  type CourseIntakeHistoryResponse,
} from "../api/institutions";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
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
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Edit,
  History,
  Lock,
  RefreshCw,
  ShieldAlert,
  Sliders,
} from "lucide-react";

export function AicteIntakePage() {
  useDocumentTitle("Intake & Capacity Control");
  const [institutions, setInstitutions] = useState<InstitutionResponse[]>([]);
  const [selectedInstitutionId, setSelectedInstitutionId] = useState<number | null>(null);
  const [selectedInstitution, setSelectedInstitution] = useState<InstitutionResponse | null>(null);

  // Institution search
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoadingInstitutions, setIsLoadingInstitutions] = useState(true);
  const [institutionError, setInstitutionError] = useState<string | null>(null);

  // Courses state
  const [courses, setCourses] = useState<CourseResponse[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [courseError, setCourseError] = useState<string | null>(null);

  // Edit Intake Modal state
  const [editingCourse, setEditingCourse] = useState<CourseResponse | null>(null);
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [approvedIntake, setApprovedIntake] = useState<number>(60);
  const [supernumeraryAllowed, setSupernumeraryAllowed] = useState<number>(0);
  const [changeReason, setChangeReason] = useState("");
  const [isUpdatingIntake, setIsUpdatingIntake] = useState(false);
  const [intakeUpdateError, setIntakeUpdateError] = useState<string | null>(null);
  const [intakeUpdateSuccess, setIntakeUpdateSuccess] = useState<string | null>(null);

  // History Modal state
  const [historyCourse, setHistoryCourse] = useState<CourseResponse | null>(null);
  const [intakeHistory, setIntakeHistory] = useState<CourseIntakeHistoryResponse[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Status Change Modal state
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [newApprovalStatus, setNewApprovalStatus] = useState<string>("active");
  const [statusChangeReason, setStatusChangeReason] = useState("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Load institutions list
  const fetchInstitutions = useCallback(async () => {
    setIsLoadingInstitutions(true);
    setInstitutionError(null);
    try {
      const resp = await listInstitutions({ limit: 100 });
      setInstitutions(resp.items);
      if (resp.items.length > 0 && !selectedInstitutionId) {
        setSelectedInstitutionId(resp.items[0].id);
        setSelectedInstitution(resp.items[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load institutions";
      setInstitutionError(msg);
    } finally {
      setIsLoadingInstitutions(false);
    }
  }, [selectedInstitutionId]);

  useEffect(() => {
    fetchInstitutions();
  }, [fetchInstitutions]);

  // Load courses when selected institution changes
  const fetchCourses = async (instId: number) => {
    setIsLoadingCourses(true);
    setCourseError(null);
    try {
      const data = await listCourses(instId);
      setCourses(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load institution courses";
      setCourseError(msg);
    } finally {
      setIsLoadingCourses(false);
    }
  };

  useEffect(() => {
    if (selectedInstitutionId) {
      const inst = institutions.find((i) => i.id === selectedInstitutionId);
      if (inst) setSelectedInstitution(inst);
      fetchCourses(selectedInstitutionId);
    }
  }, [selectedInstitutionId, institutions]);

  // Filtered institutions
  const filteredInstitutions = useMemo(() => {
    if (!searchQuery.trim()) return institutions;
    const q = searchQuery.toLowerCase();
    return institutions.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        i.aicte_id.toLowerCase().includes(q) ||
        i.state.toLowerCase().includes(q),
    );
  }, [institutions, searchQuery]);

  // Open Edit Intake modal
  const openEditModal = (course: CourseResponse) => {
    setEditingCourse(course);
    const existingIntake = course.intakes.find((i) => i.academic_year === "2026-27");
    setAcademicYear("2026-27");
    setApprovedIntake(existingIntake?.approved_intake ?? 60);
    setSupernumeraryAllowed(existingIntake?.supernumerary_seats_allowed ?? 0);
    setChangeReason("");
    setIntakeUpdateError(null);
    setIntakeUpdateSuccess(null);
  };

  const handleUpdateIntake = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInstitutionId || !editingCourse) return;
    if (!changeReason.trim()) {
      setIntakeUpdateError("A reason for modifying the approved quota is required for audit logs.");
      return;
    }

    setIsUpdatingIntake(true);
    setIntakeUpdateError(null);

    try {
      await updateCourseIntake(selectedInstitutionId, editingCourse.id, {
        academic_year: academicYear,
        approved_intake: Number(approvedIntake),
        supernumerary_seats_allowed: Number(supernumeraryAllowed),
        change_reason: changeReason.trim(),
      });
      setIntakeUpdateSuccess("Approved intake quota updated and recorded in audit log.");
      fetchCourses(selectedInstitutionId);
      setTimeout(() => {
        setEditingCourse(null);
      }, 900);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update intake quota";
      setIntakeUpdateError(msg);
    } finally {
      setIsUpdatingIntake(false);
    }
  };

  // Open History modal
  const openHistoryModal = async (course: CourseResponse) => {
    setHistoryCourse(course);
    if (!selectedInstitutionId) return;
    setIsLoadingHistory(true);
    try {
      const history = await getIntakeHistory(selectedInstitutionId, course.id);
      setIntakeHistory(history);
    } catch {
      setIntakeHistory([]);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Handle Approval Status Change
  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInstitutionId) return;
    setIsUpdatingStatus(true);
    setStatusError(null);

    try {
      const updated = await updateInstitutionApprovalStatus(selectedInstitutionId, {
        approval_status: newApprovalStatus,
        reason: statusChangeReason.trim() || undefined,
      });
      setSelectedInstitution(updated);
      setInstitutions((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setIsStatusModalOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update approval status";
      setStatusError(msg);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          AICTE Intake & Approval Control
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Statutory control of approved student intake and course quotas. Changes append to the audit history and trigger validation reconciliation.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Column: Institution Directory Selector */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Approved institutions
            </h2>
            <span className="text-xs font-mono text-slate-400">
              {filteredInstitutions.length}
            </span>
          </div>

          <Input
            placeholder="Search college or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />

          {isLoadingInstitutions ? (
            <div className="py-8 text-center">
              <LoadingSpinner size="sm" label="Loading..." />
            </div>
          ) : institutionError ? (
            <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">{institutionError}</div>
          ) : filteredInstitutions.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-400">No institutions match.</div>
          ) : (
            <div className="max-h-[540px] overflow-y-auto space-y-1.5 pr-1 divide-y divide-slate-100">
              {filteredInstitutions.map((inst) => (
                <button
                  key={inst.id}
                  type="button"
                  onClick={() => setSelectedInstitutionId(inst.id)}
                  className={`w-full text-left p-2.5 rounded-lg text-xs transition-all flex items-center justify-between ${
                    selectedInstitutionId === inst.id
                      ? "bg-blue-50 border border-blue-300 font-semibold text-blue-900"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="truncate pr-2">
                    <p className="font-mono text-[11px] text-slate-500">{inst.aicte_id}</p>
                    <p className="truncate font-medium">{inst.name}</p>
                    <span className="text-[10px] text-slate-400">{inst.state}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Institution Intake Quotas & Courses */}
        <div className="lg:col-span-3 space-y-6">
          {selectedInstitution ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
              {/* Institution Identity Card */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-200 pb-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {selectedInstitution.aicte_id}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                        selectedInstitution.approval_status === "active"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      Approval: {selectedInstitution.approval_status}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                        selectedInstitution.account_status === "active"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      Account: {selectedInstitution.account_status.replace("_", " ")}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-slate-900">{selectedInstitution.name}</h2>
                  <p className="text-xs text-slate-500">
                    {selectedInstitution.address}, {selectedInstitution.district},{" "}
                    {selectedInstitution.state} • Affiliated to:{" "}
                    <strong>{selectedInstitution.affiliating_university}</strong>
                  </p>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setNewApprovalStatus(selectedInstitution.approval_status);
                      setStatusChangeReason("");
                      setIsStatusModalOpen(true);
                    }}
                    leftIcon={<Sliders className="w-3.5 h-3.5" />}
                  >
                    Change approval status
                  </Button>
                </div>
              </div>

              {/* Statutory Notice: Read-only for colleges */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 flex items-center gap-2">
                <Lock className="w-4 h-4 text-slate-400 shrink-0" />
                <span>
                  <strong>Statutory Quota Authority:</strong> Approved intake numbers shown here are
                  governed exclusively by AICTE officers. Colleges cannot modify these numbers
                  directly and receive a 403 Forbidden upon any edit attempt.
                </span>
              </div>

              {/* Approved Courses Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">
                    Approved academic courses and intake quotas
                  </h3>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => selectedInstitutionId && fetchCourses(selectedInstitutionId)}
                    leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoadingCourses ? "animate-spin" : ""}`} />}
                  >
                    Refresh
                  </Button>
                </div>

                {isLoadingCourses ? (
                  <div className="py-12 text-center">
                    <LoadingSpinner size="md" label="Loading approved courses..." />
                  </div>
                ) : courseError ? (
                  <ErrorState
                    title="Failed to Load Courses"
                    message={courseError}
                    onRetry={() => selectedInstitutionId && fetchCourses(selectedInstitutionId)}
                  />
                ) : courses.length === 0 ? (
                  <EmptyState
                    title="No Courses Configured"
                    description="This institution currently has no approved courses on record."
                  />
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Course Name</TableHead>
                          <TableHead>Level</TableHead>
                          <TableHead>Branch</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Supernum. Allowed</TableHead>
                          <TableHead className="text-right">Approved Intake (2026-27)</TableHead>
                          <TableHead className="text-right">Supernum. Seats</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {courses.map((c) => {
                          const intake2627 = c.intakes.find((i) => i.academic_year === "2026-27");
                          return (
                            <TableRow key={c.id}>
                              <TableCell className="font-semibold text-slate-900">
                                {c.name}
                              </TableCell>
                              <TableCell>
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700">
                                  {c.level}
                                </span>
                              </TableCell>
                              <TableCell className="text-xs text-slate-600">{c.branch}</TableCell>
                              <TableCell className="text-xs text-slate-600">
                                {c.duration_years} Years
                              </TableCell>
                              <TableCell>
                                <span
                                  className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                    c.supernumerary_allowed
                                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                      : "bg-slate-100 text-slate-500"
                                  }`}
                                >
                                  {c.supernumerary_allowed ? "Yes" : "No"}
                                </span>
                              </TableCell>
                              <TableCell className="text-right font-mono font-bold text-slate-900 text-sm">
                                {intake2627?.approved_intake ?? "—"}
                              </TableCell>
                              <TableCell className="text-right font-mono font-medium text-slate-600 text-xs">
                                {intake2627?.supernumerary_seats_allowed ?? "0"}
                              </TableCell>
                              <TableCell className="text-right whitespace-nowrap">
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => openHistoryModal(c)}
                                    title="View Intake Modification History"
                                    leftIcon={<History className="w-3.5 h-3.5" />}
                                  >
                                    History
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="primary"
                                    onClick={() => openEditModal(c)}
                                    title="Update Approved Intake Quota"
                                    leftIcon={<Edit className="w-3.5 h-3.5" />}
                                  >
                                    Edit intake
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 shadow-sm">
              Select an institution from the directory to review and manage approved intake.
            </div>
          )}
        </div>
      </div>

      {/* Edit Intake Quota Modal */}
      {editingCourse && selectedInstitution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-xs font-mono font-semibold text-blue-600">
                  {selectedInstitution.aicte_id}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                  Update approved intake: {editingCourse.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingCourse(null)}
                aria-label="Close dialog"
                className="text-slate-400 hover:text-slate-600 text-sm p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpdateIntake} className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700">Academic Year</label>
                <select
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="2026-27">2026-27 (Current)</option>
                  <option value="2025-26">2025-26 (History)</option>
                  <option value="2027-28">2027-28 (Upcoming)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Approved Regular Intake"
                  type="number"
                  min="0"
                  max="1000"
                  value={approvedIntake}
                  onChange={(e) => setApprovedIntake(parseInt(e.target.value, 10) || 0)}
                  required
                />
                <Input
                  label="Supernumerary Allowed"
                  type="number"
                  min="0"
                  max="200"
                  value={supernumeraryAllowed}
                  onChange={(e) => setSupernumeraryAllowed(parseInt(e.target.value, 10) || 0)}
                  hint={editingCourse.supernumerary_allowed ? "Eligible" : "Not enabled for course"}
                  disabled={!editingCourse.supernumerary_allowed}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700">
                  Official Justification / Change Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={2}
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                  placeholder="e.g. AICTE Approval Process Handbook revised sanctioned strength"
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <p className="text-[11px] text-slate-400">
                  Reason will be permanently recorded in course_intake_history and the audit log.
                </p>
              </div>

              {intakeUpdateError && (
                <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  <span>{intakeUpdateError}</span>
                </div>
              )}

              {intakeUpdateSuccess && (
                <div className="p-3 bg-emerald-50 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{intakeUpdateSuccess}</span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setEditingCourse(null)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={isUpdatingIntake}
                  loadingText="Saving quota..."
                >
                  Save intake changes
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Course Intake History Modal */}
      {historyCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-xs font-mono font-semibold text-blue-600">INTAKE HISTORY</span>
                <h3 className="text-base font-bold text-slate-900 mt-0.5">
                  Audit revisions: {historyCourse.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setHistoryCourse(null)}
                aria-label="Close dialog"
                className="text-slate-400 hover:text-slate-600 text-sm p-1"
              >
                ✕
              </button>
            </div>

            {isLoadingHistory ? (
              <div className="py-12 text-center">
                <LoadingSpinner size="sm" label="Loading revision history..." />
              </div>
            ) : intakeHistory.length === 0 ? (
              <EmptyState
                title="No Prior Modifications"
                description="This course retains its initial baseline approved intake quota with no historical revisions."
              />
            ) : (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Year</TableHead>
                      <TableHead className="text-right">Approved Intake</TableHead>
                      <TableHead className="text-right">Supernum.</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead>Modified By</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Timestamp</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {intakeHistory.map((h) => (
                      <TableRow key={h.id}>
                        <TableCell className="font-mono text-xs font-semibold">{h.academic_year}</TableCell>
                        <TableCell className="text-right font-mono font-bold text-slate-900">
                          {h.approved_intake}
                        </TableCell>
                        <TableCell className="text-right font-mono text-slate-600">
                          {h.supernumerary_seats_allowed}
                        </TableCell>
                        <TableCell className="text-xs text-slate-600 capitalize">{h.source}</TableCell>
                        <TableCell className="text-xs text-slate-700 truncate max-w-[120px]">
                          {h.set_by || "system"}
                        </TableCell>
                        <TableCell className="text-xs text-slate-600 max-w-xs truncate">
                          {h.change_reason || "Initial seed"}
                        </TableCell>
                        <TableCell className="text-[11px] text-slate-400 whitespace-nowrap">
                          {new Date(h.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setHistoryCourse(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Change Institution Approval Status Modal */}
      {isStatusModalOpen && selectedInstitution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Update institutional approval status
                </h3>
                <p className="text-xs text-slate-500">{selectedInstitution.name}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsStatusModalOpen(false)}
                aria-label="Close dialog"
                className="text-slate-400 hover:text-slate-600 text-sm p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpdateStatus} className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700">Approval Status</label>
                <select
                  value={newApprovalStatus}
                  onChange={(e) => setNewApprovalStatus(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="active">Active (Full submission & upload rights)</option>
                  <option value="suspended">Suspended (Uploads blocked, read-only)</option>
                  <option value="withdrawn">Withdrawn (Approval formally revoked)</option>
                  <option value="expired">Expired (Approval tenure ended)</option>
                </select>
              </div>

              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <span>
                  <strong>SPEC.md Rule:</strong> Setting status to suspended, withdrawn, or expired
                  immediately blocks new student uploads (HTTP 403) and sets the account to read-only.
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700">
                  Reason for Status Modification
                </label>
                <textarea
                  rows={2}
                  value={statusChangeReason}
                  onChange={(e) => setStatusChangeReason(e.target.value)}
                  placeholder="e.g. Annual accreditation compliance review"
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {statusError && (
                <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">
                  {statusError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setIsStatusModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={isUpdatingStatus}
                  loadingText="Updating..."
                >
                  Apply status change
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
