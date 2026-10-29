import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  getInstitutionChangeRequests,
  submitChangeRequest,
  getInstitutionChangeRequestEvidenceUrl,
} from "../api/changeRequests";
import { getStudents, type StudentResponse } from "../api/students";
import type { ChangeRequest, ChangeRequestStatus } from "../types/changeRequests";
import { Button } from "../components/ui/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  FileCheck,
  FileText,
  Plus,
  RefreshCw,
  Search,
  X,
  XCircle,
} from "lucide-react";

const FIELD_OPTIONS = [
  { value: "status", label: "Student Status (Withdrawal / Transfer / Graduated)" },
  { value: "name", label: "Legal Name Correction" },
  { value: "dob", label: "Date of Birth (DOB)" },
  { value: "gender", label: "Gender" },
  { value: "enrolment_no", label: "College Enrolment / Roll No" },
  { value: "admission_date", label: "Admission Date" },
  { value: "admission_mode", label: "Admission Mode" },
  { value: "seat_type", label: "Seat Type (Regular / Supernumerary)" },
  { value: "reservation_category", label: "Reservation Category" },
  { value: "nri", label: "NRI Status" },
  { value: "oci", label: "OCI Status" },
  { value: "foreign_national", label: "Foreign National Status" },
];

const STATUS_VALUES = [
  { value: "withdrawn", label: "Withdrawn (Leaves college / cancels admission)" },
  { value: "transferred", label: "Transferred (Moves to another institution)" },
  { value: "graduated", label: "Graduated" },
  { value: "submitted", label: "Submitted (Active enrolled)" },
];

export function CollegeChangeRequestsPage() {
  useDocumentTitle("Student Record Change Requests");
  const { user } = useAuth();
  const institutionId = user?.institution_id;

  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [lockedStudents, setLockedStudents] = useState<StudentResponse[]>([]);
  const [isLoadingStudents, setIsLoadingStudents] = useState(false);

  // Form State
  const [selectedStudentId, setSelectedStudentId] = useState<number | "">("");
  const [selectedField, setSelectedField] = useState<string>("status");
  const [newValue, setNewValue] = useState<string>("withdrawn");
  const [reason, setReason] = useState<string>("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadRequests = async () => {
    if (!institutionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await getInstitutionChangeRequests(institutionId, {
        status: statusFilter === "all" ? undefined : statusFilter,
      });
      setRequests(res.items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load change requests.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, [institutionId, statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const openNewRequestModal = async () => {
    setIsModalOpen(true);
    setFormError(null);
    if (!institutionId) return;
    setIsLoadingStudents(true);
    try {
      const res = await getStudents(institutionId, { status: "submitted", limit: 100 });
      setLockedStudents(res.items);
      if (res.items.length > 0) {
        setSelectedStudentId(res.items[0].id);
      }
    } catch {
      // Fallback: students list optional
    } finally {
      setIsLoadingStudents(false);
    }
  };

  const handleFieldChange = (field: string) => {
    setSelectedField(field);
    if (field === "status") {
      setNewValue("withdrawn");
    } else if (field === "gender") {
      setNewValue("Male");
    } else if (field === "seat_type") {
      setNewValue("Regular");
    } else if (field === "reservation_category") {
      setNewValue("General");
    } else if (["nri", "oci", "foreign_national"].includes(field)) {
      setNewValue("Yes");
    } else {
      setNewValue("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institutionId || !selectedStudentId) {
      setFormError("Please select a student record.");
      return;
    }
    if (!newValue.trim()) {
      setFormError("Please provide the requested new value.");
      return;
    }
    if (!reason.trim() || reason.trim().length < 5) {
      setFormError("Please provide an explanatory reason of at least 5 characters.");
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      await submitChangeRequest(institutionId, {
        student_id: Number(selectedStudentId),
        field: selectedField,
        new_value: newValue.trim(),
        reason: reason.trim(),
        document: evidenceFile,
      });

      setSuccessMsg("Change request submitted successfully to AICTE for review.");
      setIsModalOpen(false);
      // Reset form
      setReason("");
      setEvidenceFile(null);
      await loadRequests();
      setTimeout(() => setSuccessMsg(null), 6000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit change request.";
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Metrics
  const totalCount = requests.length;
  const pendingCount = requests.filter((r) => r.status === "pending").length;
  const approvedCount = requests.filter((r) => r.status === "approved").length;
  const rejectedCount = requests.filter((r) => r.status === "rejected").length;

  const filteredRequests = requests.filter((r) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const studentName = r.student?.name?.toLowerCase() || "";
    const apaarId = r.student?.apaar_id?.toLowerCase() || "";
    const field = r.field.toLowerCase();
    return studentName.includes(term) || apaarId.includes(term) || field.includes(term);
  });

  const renderStatusBadge = (status: ChangeRequestStatus) => {
    switch (status) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-300">
            <Clock className="w-3.5 h-3.5" />
            Pending Review
          </span>
        );
      case "approved":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Approved
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-300">
            <XCircle className="w-3.5 h-3.5" />
            Rejected
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl border border-blue-200">
              <FileCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                Post-Lock Change Requests
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Request student corrections, withdrawals, or transfers on locked records. AICTE approval required.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={loadRequests}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={openNewRequestModal}
            className="flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Change Request
          </Button>
        </div>
      </div>

      {/* Success Notification */}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-3 text-emerald-800 text-sm font-medium">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            aria-label="Dismiss notification"
            className="text-emerald-600 hover:text-emerald-800 p-1 rounded-md"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Requests
            </p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</p>
          </div>
          <div className="p-3 bg-slate-100 text-slate-700 rounded-xl">
            <FileText className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Pending Review
            </p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{pendingCount}</p>
          </div>
          <div className="p-3 bg-amber-50 text-amber-700 rounded-xl border border-amber-200">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Approved
            </p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{approvedCount}</p>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Rejected
            </p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{rejectedCount}</p>
          </div>
          <div className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Status Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg w-full md:w-auto overflow-x-auto">
          {[
            { id: "all", label: "All Requests" },
            { id: "pending", label: "Pending Review" },
            { id: "approved", label: "Approved" },
            { id: "rejected", label: "Rejected" },
          ].map((tab) => (
            <button
              key={tab.id}
              aria-label={`Filter by ${tab.label}`}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                statusFilter === tab.id
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search student, APAAR ID, field..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Main Content Table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 flex justify-center items-center shadow-sm">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to Load Change Requests"
          message={error}
          onRetry={loadRequests}
        />
      ) : filteredRequests.length === 0 ? (
        <EmptyState
          icon={<FileCheck className="w-6 h-6 text-slate-400" />}
          title="No Change Requests Found"
          description={
            searchTerm || statusFilter !== "all"
              ? "No change requests matched your current filters."
              : "No post-lock change requests have been filed yet. When records are locked after final submission, use this screen to request updates with supporting evidence."
          }
          actionLabel={statusFilter !== "all" ? "Clear Filters" : "New Change Request"}
          onAction={statusFilter !== "all" ? () => setStatusFilter("all") : openNewRequestModal}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Req #</th>
                  <th className="py-3 px-4">Student & APAAR</th>
                  <th className="py-3 px-4">Field Changed</th>
                  <th className="py-3 px-4">Old Value</th>
                  <th className="py-3 px-4">Requested New Value</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Reason & Evidence</th>
                  <th className="py-3 px-4">AICTE Decision Note</th>
                  <th className="py-3 px-4">Submitted At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredRequests.map((cr) => (
                  <tr key={cr.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-900">
                      #{cr.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">
                        {cr.student?.name || `Student #${cr.student_id}`}
                      </div>
                      <div className="font-mono text-slate-500 text-[11px] mt-0.5">
                        APAAR: {cr.student?.apaar_id || "—"}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium text-blue-700">
                      {cr.field}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      <span className="line-through bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                        {cr.old_value || "—"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-900">
                      <span className="bg-blue-50 text-blue-800 px-2 py-0.5 rounded border border-blue-200 font-semibold text-[11px]">
                        {cr.new_value}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">{renderStatusBadge(cr.status)}</td>
                    <td className="py-3.5 px-4 max-w-xs">
                      <p className="line-clamp-2 text-slate-700">{cr.reason}</p>
                      {cr.document_ref && institutionId && (
                        <a
                          href={getInstitutionChangeRequestEvidenceUrl(institutionId, cr.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 font-medium mt-1"
                        >
                          <Download className="w-3 h-3" />
                          View Evidence Document
                        </a>
                      )}
                    </td>
                    <td className="py-3.5 px-4 max-w-xs">
                      {cr.decision_note ? (
                        <div className="text-slate-700 text-[11px] bg-slate-50 p-2 rounded border border-slate-200">
                          <span className="font-semibold block text-slate-900">
                            {cr.decided_by_email || "AICTE Reviewer"}:
                          </span>
                          {cr.decision_note}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Awaiting review</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-500 text-[11px]">
                      {new Date(cr.created_at).toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: New Change Request */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl w-full max-w-2xl overflow-hidden animate-scaleUp">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <FileCheck className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Submit Post-Lock Change Request
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                aria-label="Close dialog"
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              {formError && (
                <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Step 1: Select Student */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  1. Select Locked Student Record <span className="text-rose-500">*</span>
                </label>
                {isLoadingStudents ? (
                  <div className="py-2 text-xs text-slate-500 flex items-center gap-2">
                    <LoadingSpinner size="sm" /> Loading locked students...
                  </div>
                ) : lockedStudents.length > 0 ? (
                  <select
                    value={selectedStudentId}
                    onChange={(e) => setSelectedStudentId(Number(e.target.value))}
                    required
                    className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {lockedStudents.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} (APAAR: {s.apaar_id}) — {s.course_name || "Course"} [{s.status}]
                      </option>
                    ))}
                  </select>
                ) : (
                  <div>
                    <input
                      type="number"
                      placeholder="Enter Student Database ID"
                      value={selectedStudentId}
                      onChange={(e) =>
                        setSelectedStudentId(e.target.value ? Number(e.target.value) : "")
                      }
                      required
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      No locked students auto-detected in current list. Enter the student ID directly.
                    </p>
                  </div>
                )}
              </div>

              {/* Step 2: Choose Field */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    2. Field to Modify <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={selectedField}
                    onChange={(e) => handleFieldChange(e.target.value)}
                    className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {FIELD_OPTIONS.map((f) => (
                      <option key={f.value} value={f.value}>
                        {f.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Step 3: Requested Value */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    3. Requested New Value <span className="text-rose-500">*</span>
                  </label>
                  {selectedField === "status" ? (
                    <select
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {STATUS_VALUES.map((st) => (
                        <option key={st.value} value={st.value}>
                          {st.label}
                        </option>
                      ))}
                    </select>
                  ) : selectedField === "dob" ? (
                    <input
                      type="date"
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      required
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : selectedField === "gender" ? (
                    <select
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  ) : selectedField === "seat_type" ? (
                    <select
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="Regular">Regular</option>
                      <option value="Supernumerary">Supernumerary</option>
                    </select>
                  ) : selectedField === "reservation_category" ? (
                    <select
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="General">General</option>
                      <option value="OBC">OBC</option>
                      <option value="SC">SC</option>
                      <option value="ST">ST</option>
                      <option value="EWS">EWS</option>
                    </select>
                  ) : ["nri", "oci", "foreign_national"].includes(selectedField) ? (
                    <select
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="Yes">Yes</option>
                      <option value="No">No</option>
                    </select>
                  ) : (
                    <input
                      type="text"
                      placeholder={`Enter new ${selectedField}`}
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      required
                      className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  )}
                </div>
              </div>

              {/* Step 4: Reason */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  4. Reason / Justification <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="Provide an official explanation for why this locked record requires change..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  required
                  className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Step 5: Evidence Attachment */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  5. Evidence Document (PDF / Image)
                </label>
                <div className="border border-dashed border-slate-300 rounded-lg p-4 bg-slate-50 text-center">
                  <input
                    type="file"
                    accept=".pdf,image/png,image/jpeg"
                    onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                    className="block w-full text-xs text-slate-500 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Attach withdrawal letter, gazette notification, affidavit, or transfer certificate (max 10 MB).
                  </p>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={isSubmitting}
                  className="flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <LoadingSpinner size="sm" /> Submitting...
                    </>
                  ) : (
                    "Submit to AICTE"
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
