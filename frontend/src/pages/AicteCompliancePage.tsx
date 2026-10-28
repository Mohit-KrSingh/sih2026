import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getComplianceList } from "../api/analytics";
import { downloadReportFile } from "../api/reports";
import type { ComplianceViolation } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { Button } from "../components/ui/Button";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  AlertOctagon,
  Calendar,
  Download,
  Filter,
  RefreshCw,
  Search,
  Send,
  Shield,
} from "lucide-react";

export function AicteCompliancePage() {
  useDocumentTitle("Compliance & Over-Intake Oversight");
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [stateFilter, setStateFilter] = useState("");
  const [minOvershoot, setMinOvershoot] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [violations, setViolations] = useState<ComplianceViolation[]>([]);
  const [selectedNoticeCollege, setSelectedNoticeCollege] = useState<{
    id: number;
    name: string;
    aicteId: string;
    overshoot: number;
  } | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleExport = async (format: "csv" | "xlsx" | "pdf") => {
    setDownloading(format);
    try {
      await downloadReportFile("seat-utilisation", format, {
        academic_year: academicYear,
        state: stateFilter || undefined,
      });
    } catch (err: any) {
      alert(err?.message || "Failed to download report");
    } finally {
      setDownloading(null);
    }
  };

  async function loadData() {
    setLoading(true);
    try {
      const res = await getComplianceList({
        academic_year: academicYear,
        state: stateFilter || undefined,
        min_overshoot: minOvershoot,
      });
      setViolations(res.violations || []);
    } catch (err) {
      console.error("Failed to load compliance violations:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [academicYear, stateFilter, minOvershoot]);

  const filteredViolations = violations.filter((v) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      v.institution_name.toLowerCase().includes(q) ||
      v.aicte_id.toLowerCase().includes(q) ||
      v.course_name.toLowerCase().includes(q) ||
      v.state.toLowerCase().includes(q)
    );
  });

  const uniqueStates = Array.from(new Set(violations.map((v) => v.state))).filter(Boolean);
  const totalOvershoot = filteredViolations.reduce((acc, v) => acc + v.overshoot, 0);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-full border border-rose-200">
              AICTE Compliance Oversight
            </span>
            <span className="text-xs text-slate-500 font-medium">&bull; Section 12 Regulatory Monitor</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Over-Intake Compliance & Red List
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time tracking of institutions admitting regular students beyond authorized quotas
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
              <option value="2025-26">Academic Year 2025-26 (History)</option>
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

      {/* Red-List Alert Banner */}
      <div className="p-5 rounded-xl border-2 border-rose-300 bg-rose-50/50 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="p-2 rounded-xl bg-rose-600 text-white shrink-0 mt-0.5">
            <AlertOctagon className="w-5 h-5" />
          </span>
          <div>
            <h3 className="font-bold text-rose-950 text-sm">
              Statutory Quota Over-Enrolment Mandate
            </h3>
            <p className="text-xs text-rose-800 mt-0.5 max-w-3xl">
              Institutions on this list have enrolled students above approved intake. Regular admissions exceeding capacity violate AICTE Approval Process Handbooks. AICTE officers may issue statutory compliance directives or initiate intake de-allocation.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6 shrink-0 border-t md:border-t-0 md:border-l border-rose-200 pt-3 md:pt-0 md:pl-6 text-xs">
          <div>
            <p className="text-slate-500 font-medium">Over-Intake Courses</p>
            <p className="text-2xl font-bold text-rose-600">{filteredViolations.length}</p>
          </div>
          <div>
            <p className="text-slate-500 font-medium">Total Excess Students</p>
            <p className="text-2xl font-bold text-rose-700">+{totalOvershoot}</p>
          </div>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by college name, AICTE ID, course, or state..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 focus:outline-none"
            >
              <option value="">All States ({uniqueStates.length})</option>
              {uniqueStates.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-500">Min Overshoot:</span>
            <select
              value={minOvershoot}
              onChange={(e) => setMinOvershoot(Number(e.target.value))}
              className="px-2 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none"
            >
              <option value={1}>&ge; 1 Student</option>
              <option value={5}>&ge; 5 Students</option>
              <option value={10}>&ge; 10 Students</option>
              <option value={20}>&ge; 20 Students</option>
            </select>
          </div>
        </div>
      </div>

      {/* Violations Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <LoadingSpinner size="md" />
            <p className="text-xs text-slate-500">Scanning institutional student databases...</p>
          </div>
        ) : filteredViolations.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <Shield className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
            <p className="font-bold text-slate-800 text-sm">No Compliance Violations Found</p>
            <p className="text-slate-500 mt-1">
              All institutions match approved intake limits matching your filter criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">Institution & AICTE ID</th>
                  <th className="py-3 px-4">State</th>
                  <th className="py-3 px-4">Course Program</th>
                  <th className="py-3 px-4 text-center">Approved Intake</th>
                  <th className="py-3 px-4 text-center">Regular Admitted</th>
                  <th className="py-3 px-4 text-center">Excess Overshoot</th>
                  <th className="py-3 px-4 text-center">Supernumerary (Adm/Max)</th>
                  <th className="py-3 px-4 text-right">Action Directives</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredViolations.map((v, i) => (
                  <tr key={`${v.institution_id}-${v.course_id}-${i}`} className="hover:bg-rose-50/20 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{v.institution_name}</div>
                      <div className="font-mono text-[10px] text-slate-500">{v.aicte_id}</div>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-700">{v.state}</td>
                    <td className="py-3.5 px-4">
                      <span className="font-medium text-slate-900">{v.course_name}</span>
                      <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200">
                        {v.level}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-bold text-slate-700">
                      {v.approved_intake}
                    </td>
                    <td className="py-3.5 px-4 text-center font-bold text-rose-700">
                      {v.regular_admitted}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                        +{v.overshoot} Overshoot
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center text-slate-600">
                      <span className="font-medium text-slate-800">{v.supernumerary_admitted}</span>
                      <span className="text-slate-400"> / {v.supernumerary_allowed}</span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="sm"
                          variant="danger"
                          className="text-xs"
                          leftIcon={<Send className="w-3.5 h-3.5" />}
                          onClick={() =>
                            setSelectedNoticeCollege({
                              id: v.institution_id,
                              name: v.institution_name,
                              aicteId: v.aicte_id,
                              overshoot: v.overshoot,
                            })
                          }
                        >
                          Issue notice
                        </Button>
                        <Link
                          to={`/aicte/explore?state=${encodeURIComponent(v.state)}&institution_id=${v.institution_id}&course_id=${v.course_id}`}
                        >
                          <Button size="sm" variant="outline" className="text-xs">
                            Drill down
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
          defaultSubject={`Immediate Clarification Required: Over-Intake of +${selectedNoticeCollege.overshoot} Students`}
          defaultMessage={`Upon automated validation against approved AICTE records for academic year ${academicYear}, your institution has exceeded approved regular intake quota by +${selectedNoticeCollege.overshoot} students. You are required to submit an official explanation or rectify records within 5 statutory working days.`}
          onSuccess={loadData}
        />
      )}
    </div>
  );
}
