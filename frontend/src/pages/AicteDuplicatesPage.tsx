import { useEffect, useState } from "react";
import { getDuplicates } from "../api/analytics";
import { downloadReportFile } from "../api/reports";
import type { DuplicateRecord } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { FlagBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  Calendar,
  Download,
  Filter,
  RefreshCw,
  Search,
  Send,
  Shield,
  Users,
} from "lucide-react";

export function AicteDuplicatesPage() {
  useDocumentTitle("Cross-College Duplicate Admissions");
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [ruleFilter, setRuleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [duplicates, setDuplicates] = useState<DuplicateRecord[]>([]);

  const [selectedNoticeCollege, setSelectedNoticeCollege] = useState<{
    id: number;
    name: string;
    aicteId: string;
    studentName: string;
    apaarId: string;
  } | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleExport = async (format: "csv" | "xlsx" | "pdf") => {
    setDownloading(format);
    try {
      await downloadReportFile("duplicate-enrolments", format, {
        academic_year: academicYear,
      });
    } catch (err: any) {
      alert(err?.message || "Failed to download duplicate enrolments report");
    } finally {
      setDownloading(null);
    }
  };

  async function loadData() {
    setLoading(true);
    try {
      const res = await getDuplicates({
        academic_year: academicYear,
        rule_code: ruleFilter || undefined,
        status: statusFilter || undefined,
      });
      setDuplicates(res.items || []);
    } catch (err) {
      console.error("Failed to load cross-college duplicates:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [academicYear, ruleFilter, statusFilter]);

  const filteredDuplicates = duplicates.filter((d) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      d.student_name.toLowerCase().includes(q) ||
      d.apaar_id.includes(q) ||
      d.colleges.some(
        (c) =>
          c.institution_name.toLowerCase().includes(q) ||
          c.aicte_id.toLowerCase().includes(q) ||
          c.course_name.toLowerCase().includes(q)
      )
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
              Cross-College Verification
            </span>
            <span className="text-xs text-slate-500 font-medium">&bull; Spec Section 9.3 & 10</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Cross-College Duplicate Enrolments
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Detect and resolve concurrent student enrolments across two or more AICTE-approved institutions
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26</option>
            </select>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={loadData}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>

          <div className="flex items-center gap-1 border-l border-slate-200 pl-3">
            <Button
              size="sm"
              variant="outline"
              disabled={downloading !== null}
              onClick={() => handleExport("csv")}
              leftIcon={<Download className="w-3 h-3" />}
            >
              CSV
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={downloading !== null}
              onClick={() => handleExport("xlsx")}
              leftIcon={<Download className="w-3 h-3 text-emerald-600" />}
            >
              Excel
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={downloading !== null}
              onClick={() => handleExport("pdf")}
              leftIcon={<Download className="w-3 h-3 text-blue-600" />}
            >
              PDF
            </Button>
          </div>
        </div>
      </div>

      {/* Overview Alert Banner */}
      <div className="p-5 rounded-xl border border-amber-200 bg-amber-50/50 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="p-2 rounded-xl bg-amber-600 text-white shrink-0 mt-0.5">
            <Users className="w-5 h-5" />
          </span>
          <div>
            <h3 className="font-bold text-amber-950 text-sm">
              One Student, Multiple Institutions Detection
            </h3>
            <p className="text-xs text-amber-800 mt-0.5 max-w-3xl">
              Cross-college duplicate rules index students by APAAR ID and academic year. When a student is active at multiple colleges, both institutions are notified. Marking a student as withdrawn or transferred at one college automatically resolves flags at both institutions.
            </p>
          </div>
        </div>

        <div className="text-right shrink-0 border-t md:border-t-0 md:border-l border-amber-200 pt-3 md:pt-0 md:pl-6 text-xs">
          <p className="text-slate-500 font-medium">Duplicate Cases Identified</p>
          <p className="text-2xl font-bold text-amber-700">{filteredDuplicates.length}</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by student name, APAAR ID, or college..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={ruleFilter}
              onChange={(e) => setRuleFilter(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 focus:outline-none"
            >
              <option value="">All Duplicate Rules</option>
              <option value="DUP_ACTIVE_OTHER_COLLEGE">Active Other College (Warning)</option>
              <option value="DUP_SAME_COURSE_OTHER_COLLEGE">Same Course Other College (Exception)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-500">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="open">Open Alerts</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Duplicates List */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <LoadingSpinner size="md" />
            <p className="text-xs text-slate-500">Scanning central database for cross-college duplicate records...</p>
          </div>
        ) : filteredDuplicates.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <Shield className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
            <p className="font-bold text-slate-800 text-sm">No Cross-College Duplicates Found</p>
            <p className="text-slate-500 mt-1">
              All enrolled APAAR IDs are unique to their respective institutions for {academicYear}.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredDuplicates.map((dupe, idx) => (
              <div key={`${dupe.apaar_id}-${idx}`} className="p-5 hover:bg-slate-50/50 transition space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-sm">
                      {dupe.student_name.charAt(0)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-slate-900 text-sm">{dupe.student_name}</h4>
                        <span className="font-mono text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
                          APAAR: {dupe.apaar_id}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Academic Year: <strong>{dupe.academic_year}</strong> &bull; Concurrently Enrolled in {dupe.colleges.length} Institutions
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <FlagBadge level={dupe.level as any} />
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${
                        dupe.status === "open"
                          ? "bg-rose-100 text-rose-800 border border-rose-300"
                          : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      }`}
                    >
                      {dupe.status}
                    </span>
                  </div>
                </div>

                {/* Institutions Involved Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  {dupe.colleges.map((col, cIdx) => (
                    <div
                      key={`${col.institution_id}-${cIdx}`}
                      className="p-3.5 rounded-lg border border-slate-200 bg-white flex items-start justify-between gap-3 shadow-xs"
                    >
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          Institution {cIdx + 1}
                        </span>
                        <h5 className="font-bold text-slate-900 text-xs">{col.institution_name}</h5>
                        <p className="text-[11px] text-slate-500">
                          AICTE ID: <span className="font-mono font-medium">{col.aicte_id}</span>
                        </p>
                        <p className="text-xs text-slate-700">
                          Program: <span className="font-semibold">{col.course_name}</span>
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Record Status: <span className="capitalize font-medium text-slate-800">{col.status}</span>
                        </p>
                      </div>

                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs shrink-0 text-slate-700 hover:text-indigo-700"
                        leftIcon={<Send className="w-3.5 h-3.5" />}
                        onClick={() =>
                          setSelectedNoticeCollege({
                            id: col.institution_id,
                            name: col.institution_name,
                            aicteId: col.aicte_id,
                            studentName: dupe.student_name,
                            apaarId: dupe.apaar_id,
                          })
                        }
                      >
                        Notice
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Notice Action Modal */}
      {selectedNoticeCollege && (
        <NoticeModal
          isOpen={true}
          onClose={() => setSelectedNoticeCollege(null)}
          institutionId={selectedNoticeCollege.id}
          institutionName={selectedNoticeCollege.name}
          aicteId={selectedNoticeCollege.aicteId}
          defaultSubject={`Duplicate Enrolment Alert: ${selectedNoticeCollege.studentName} (${selectedNoticeCollege.apaarId})`}
          defaultMessage={`National APAAR cross-verification has flagged student ${selectedNoticeCollege.studentName} (APAAR: ${selectedNoticeCollege.apaarId}) as concurrently active in another AICTE institution for academic year ${academicYear}. Please verify statutory admission bona fides, transfer certificates, or record status updates.`}
          onSuccess={loadData}
        />
      )}
    </div>
  );
}
