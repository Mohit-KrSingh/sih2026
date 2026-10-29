import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getStudent, type StudentResponse } from "../api/students";
import { getInstitutionFlags } from "../api/justifications";
import type { ValidationFlagDetail } from "../types/validation";
import { Badge, FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { ErrorState } from "../components/ui/ErrorState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Copy,
  Edit,
  GraduationCap,
  Hash,
  ShieldAlert,
  User,
} from "lucide-react";

export function StudentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const institutionId = user?.institution_id ?? 1;

  const [student, setStudent] = useState<StudentResponse | null>(null);
  const [flags, setFlags] = useState<ValidationFlagDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedApaar, setCopiedApaar] = useState(false);

  useDocumentTitle(student ? `${student.name} - Student Record` : "Student Record");

  useEffect(() => {
    let isMounted = true;
    async function loadStudentData() {
      if (!id) return;
      setIsLoading(true);
      setError(null);
      try {
        const studentId = parseInt(id, 10);
        const [studentData, flagsData] = await Promise.all([
          getStudent(institutionId, studentId),
          getInstitutionFlags(institutionId).catch(() => ({ items: [] })),
        ]);

        if (isMounted) {
          setStudent(studentData);
          const studentFlags = (flagsData.items || []).filter(
            (f) => f.student?.id === studentId || f.student_id === studentId
          );
          setFlags(studentFlags);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load student record.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadStudentData();
    return () => {
      isMounted = false;
    };
  }, [id, institutionId]);

  const copyApaar = () => {
    if (!student?.apaar_id) return;
    navigator.clipboard.writeText(student.apaar_id);
    setCopiedApaar(true);
    setTimeout(() => setCopiedApaar(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-slate-600">Loading student details...</p>
      </div>
    );
  }

  if (error || !student) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ErrorState
          title="Student record not found"
          message={error || "The requested student could not be located."}
          onRetry={() => navigate("/college/students")}
        />
        <div className="mt-4">
          <Link to="/college/students" className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1.5">
            <ArrowLeft className="w-4 h-4" /> Back to Student Directory
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 space-y-6">
      {/* Breadcrumb / Back Link */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="space-y-1">
          <Link
            to="/college/students"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition mb-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Student Directory
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{student.name}</h1>
            <Badge
              variant={
                student.status === "verified"
                  ? "success"
                  : student.status === "flagged"
                  ? "danger"
                  : student.status === "valid"
                  ? "primary"
                  : "neutral"
              }
            >
              {student.status.toUpperCase()}
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Student record ID #{student.id} &bull; Academic Year: {student.academic_year}
          </p>
        </div>

        {user?.role !== "college_viewer" && (
          <div className="flex items-center gap-2">
            <Link to={`/college/students/${student.id}/edit`}>
              <Button variant="primary" size="sm" className="flex items-center gap-1.5">
                <Edit className="w-4 h-4" /> Edit record
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Primary Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Identity & APAAR Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm border-b border-slate-100 pb-2">
            <User className="w-4 h-4 text-blue-600" />
            <span>Identity & APAAR</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-500 block">APAAR ID</span>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="font-mono font-bold text-slate-900 text-sm">{student.apaar_id}</span>
                <button
                  onClick={copyApaar}
                  aria-label="Copy APAAR ID"
                  title="Copy APAAR ID"
                  className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-700"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
                {copiedApaar && <span className="text-[10px] text-emerald-600 font-medium">Copied!</span>}
              </div>
            </div>

            <div>
              <span className="text-slate-500 block">Enrolment Number</span>
              <span className="font-mono text-slate-900 font-medium">{student.enrolment_no || "Not assigned"}</span>
            </div>

            <div>
              <span className="text-slate-500 block">Gender & Category</span>
              <span className="text-slate-900 font-medium">
                {student.gender} &bull; {student.reservation_category}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Date of Birth (Encrypted at rest)</span>
              <span className="font-mono text-slate-900 font-medium">{student.dob}</span>
            </div>
          </div>
        </div>

        {/* Academic & Quota Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm border-b border-slate-100 pb-2">
            <GraduationCap className="w-4 h-4 text-blue-600" />
            <span>Enrolment & Programme</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-500 block">Course / Programme</span>
              <span className="text-slate-900 font-semibold block">
                {student.course_name || `Course ID #${student.course_id || "Unassigned"}`}
              </span>
              {student.branch && (
                <span className="text-slate-500 text-[11px]">
                  Branch: {student.branch}
                </span>
              )}
            </div>

            <div>
              <span className="text-slate-500 block">Seat Type & Quota</span>
              <span className="inline-block font-semibold text-slate-900">
                {student.seat_type} Quota
              </span>
              <span className="text-slate-500 ml-1">({student.admission_mode})</span>
            </div>

            <div>
              <span className="text-slate-500 block">Admission Date</span>
              <span className="text-slate-900 font-medium">{student.admission_date}</span>
            </div>

            <div>
              <span className="text-slate-500 block">Academic Year</span>
              <span className="font-medium text-slate-900">{student.academic_year}</span>
            </div>
          </div>
        </div>

        {/* Special Quota & Domicile Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm border-b border-slate-100 pb-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            <span>Special Quota & Domicile</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-slate-500 block">NRI Quota</span>
                <span className="font-medium text-slate-900">{student.nri ? "Yes" : "No"}</span>
              </div>
              <div>
                <span className="text-slate-500 block">OCI Quota</span>
                <span className="font-medium text-slate-900">{student.oci ? "Yes" : "No"}</span>
              </div>
            </div>

            <div>
              <span className="text-slate-500 block">Foreign National</span>
              <span className="font-medium text-slate-900">
                {student.foreign_national ? `Yes (${student.country || "Country unspecified"})` : "No"}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Verification Status</span>
              <div className="flex items-center gap-1.5 mt-0.5">
                {student.status === "verified" ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700 font-medium">Cryptographically Certified</span>
                  </>
                ) : student.status === "flagged" ? (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    <span className="text-amber-700 font-medium">Pending Validation Resolution</span>
                  </>
                ) : (
                  <>
                    <Hash className="w-3.5 h-3.5 text-blue-600" />
                    <span className="text-slate-700 font-medium">Draft Record</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Validation Flags Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-600" />
            <h2 className="text-base font-bold text-slate-900">Validation Flags for this Student</h2>
          </div>
          <span className="text-xs text-slate-500">
            {flags.length} {flags.length === 1 ? "flag" : "flags"} detected
          </span>
        </div>

        {flags.length === 0 ? (
          <div className="py-6 text-center text-slate-500 text-xs">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="font-semibold text-slate-700">No Validation Issues Found</p>
            <p>This student record satisfies all cheap checks, cross-registry lookups, and intake quotas.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {flags.map((flag) => (
              <div key={flag.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="space-y-1 max-w-2xl">
                  <div className="flex items-center gap-2">
                    <FlagBadge level={flag.level} />
                    <span className="font-mono font-semibold text-slate-900">{flag.rule_code}</span>
                    {flag.field && <span className="text-slate-500 text-[11px]">field: {flag.field}</span>}
                    <Badge variant={flag.status === "resolved" ? "success" : flag.status === "justified" ? "warning" : "danger"}>
                      {flag.status.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-slate-700 font-medium">{flag.message}</p>
                  {flag.fix_hint && <p className="text-blue-700 text-[11px] bg-blue-50/60 p-1 rounded">{flag.fix_hint}</p>}
                </div>

                <div className="flex items-center gap-2">
                  <Link to={`/college/validation/${flag.id}`}>
                    <Button variant="outline" size="sm">
                      View flag details
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
