import React, { useCallback, useEffect, useState } from "react";
import {
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  RefreshCw,
  Building2,
  Calendar,
  AlertCircle,
  FileCheck,
} from "lucide-react";
import { downloadReportFile, fetchReportPreview } from "../api/reports";
import { listInstitutions, type InstitutionResponse } from "../api/institutions";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import type {
  ReportFilterState,
  ReportFormat,
  ReportPreviewResponse,
  ReportType,
} from "../types/reports";

interface ReportMeta {
  id: ReportType;
  title: string;
  badge: string;
  description: string;
  requiresCollege?: boolean;
}

const REPORT_CATALOG: ReportMeta[] = [
  {
    id: "enrolment-by-state-course",
    title: "Enrolment by State and Course",
    badge: "National",
    description: "Sanctioned intake, student admissions, and capacity fill rate by region and discipline.",
  },
  {
    id: "seat-utilisation",
    title: "Seat Utilisation & Quota Compliance",
    badge: "Oversight",
    description: "Course-level intake quota monitoring, over-intake overshoot tracking, and vacancy analysis.",
  },
  {
    id: "colleges-with-exceptions",
    title: "Colleges with Exceptions Register",
    badge: "Compliance",
    description: "Recorded validation exceptions, written college justifications, and uploaded evidence files.",
  },
  {
    id: "duplicate-enrolments",
    title: "Cross-College Duplicate Enrolments",
    badge: "Integrity",
    description: "Multi-institution concurrent enrolments with privacy-masked APAAR IDs and status.",
  },
  {
    id: "year-over-year-trends",
    title: "Year-over-Year (YoY) Admission Trends",
    badge: "Trends",
    description: "Comparative admissions growth and intake shifts between 2025-26 history and 2026-27.",
  },
  {
    id: "accreditation-snapshot",
    title: "Accreditation Compliance Snapshot",
    badge: "Institutional",
    description: "Single-college accreditation portfolio, seat declarations, flags, and anomaly risk assessment.",
    requiresCollege: true,
  },
  {
    id: "college-submission",
    title: "College Student Submission Register",
    badge: "Roster",
    description: "Institutional student admission roster with official submission receipt.",
    requiresCollege: true,
  },
];

const STATES = [
  "All States (National)",
  "Delhi",
  "Gujarat",
  "Karnataka",
  "Maharashtra",
  "Rajasthan",
  "Tamil Nadu",
  "Uttar Pradesh",
  "West Bengal",
];

export const AicteReportsPage: React.FC = () => {
  useDocumentTitle("Reports & Statutory Exports");
  const [selectedReport, setSelectedReport] = useState<ReportType>("enrolment-by-state-course");
  const [filters, setFilters] = useState<ReportFilterState>({
    academic_year: "2026-27",
    state: "",
    course: "",
    institution_id: undefined,
  });

  const [institutions, setInstitutions] = useState<InstitutionResponse[]>([]);
  const [preview, setPreview] = useState<ReportPreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);
  const [downloadingFormat, setDownloadingFormat] = useState<ReportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load institutions list for single-college reports
  useEffect(() => {
    async function loadInstitutions() {
      try {
        const data = await listInstitutions();
        setInstitutions(data.items || []);
        if (data.items?.length > 0 && !filters.institution_id) {
          setFilters((prev) => ({ ...prev, institution_id: data.items[0].id }));
        }
      } catch {
        // Fallback silently if unauthenticated or error
      }
    }
    loadInstitutions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch preview when report type or filters change
  const loadPreview = useCallback(async () => {
    setLoadingPreview(true);
    setError(null);
    try {
      const data = await fetchReportPreview(selectedReport, filters);
      setPreview(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load report preview data.");
      setPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  }, [selectedReport, filters]);

  useEffect(() => {
    // Only load preview if report doesn't require college or college is selected
    const activeMeta = REPORT_CATALOG.find((r) => r.id === selectedReport);
    if (!activeMeta?.requiresCollege || filters.institution_id) {
      loadPreview();
    }
  }, [selectedReport, filters.academic_year, filters.state, filters.institution_id, loadPreview]);

  // Handle Export / Download
  const handleDownload = async (format: ReportFormat) => {
    setDownloadingFormat(format);
    setError(null);
    try {
      await downloadReportFile(selectedReport, format, filters);
    } catch (err: any) {
      setError(err?.message || `Failed to download ${format.toUpperCase()} report.`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const activeMeta = REPORT_CATALOG.find((r) => r.id === selectedReport) || REPORT_CATALOG[0];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white p-6 rounded-xl shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-blue-600/60 text-blue-200 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-blue-400/30">
                AICTE Central Oversight
              </span>
              <span className="text-xs text-blue-300 font-mono">SPEC.md §17</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">National Reports & Data Exports</h1>
            <p className="text-sm text-blue-200 mt-1 max-w-2xl">
              Official regulatory exports in CSV, Microsoft Excel (XLSX), and high-resolution PDF formats.
              Certified under the AICTE Approval Process Handbook (APH) and EduTrace National Framework.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadPreview}
              disabled={loadingPreview}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm font-medium transition backdrop-blur-sm"
              title="Refresh Preview"
            >
              <RefreshCw className={`w-4 h-4 ${loadingPreview ? "animate-spin" : ""}`} />
              Refresh Data
            </button>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Catalog Sidebar & Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Report Catalog Selector */}
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1 mb-2">
            Regulatory Reports Catalog
          </h2>
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100 overflow-hidden">
            {REPORT_CATALOG.map((item) => {
              const isSelected = selectedReport === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setSelectedReport(item.id)}
                  className={`w-full text-left p-3.5 transition flex flex-col gap-1 ${
                    isSelected
                      ? "bg-blue-50/80 border-l-4 border-blue-600 text-blue-900"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs leading-snug">{item.title}</span>
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                        isSelected
                          ? "bg-blue-200 text-blue-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {item.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                    {item.description}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Filters, Export Bar, Preview Table */}
        <div className="lg:col-span-3 space-y-6">
          {/* Filter & Export Toolbar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h2 className="font-bold text-slate-900 text-base">{activeMeta.title}</h2>
                <p className="text-xs text-slate-500">{activeMeta.description}</p>
              </div>

              {/* Export Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownload("csv")}
                  disabled={downloadingFormat !== null || loadingPreview}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  {downloadingFormat === "csv" ? "Generating..." : "CSV"}
                </button>

                <button
                  onClick={() => handleDownload("xlsx")}
                  disabled={downloadingFormat !== null || loadingPreview}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-xs font-semibold border border-emerald-300 transition"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  {downloadingFormat === "xlsx" ? "Generating..." : "Excel (XLSX)"}
                </button>

                <button
                  onClick={() => handleDownload("pdf")}
                  disabled={downloadingFormat !== null || loadingPreview}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition shadow-sm"
                >
                  <FileText className="w-3.5 h-3.5" />
                  {downloadingFormat === "pdf" ? "Rendering PDF..." : "PDF Report"}
                </button>
              </div>
            </div>

            {/* Filter Inputs Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Academic Year */}
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 uppercase mb-1">
                  Academic Year
                </label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                  <select
                    value={filters.academic_year}
                    onChange={(e) => setFilters({ ...filters, academic_year: e.target.value })}
                    className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="2026-27">2026-27 (Current Active)</option>
                    <option value="2025-26">2025-26 (Central History)</option>
                  </select>
                </div>
              </div>

              {/* State Filter (if not single-college report) */}
              {!activeMeta.requiresCollege ? (
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 uppercase mb-1">
                    State / Territory
                  </label>
                  <div className="relative">
                    <Filter className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                    <select
                      value={filters.state || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          state: e.target.value.includes("All") ? "" : e.target.value,
                        })
                      }
                      className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                    >
                      {STATES.map((s) => (
                        <option key={s} value={s.includes("All") ? "" : s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ) : (
                /* College Picker (when report requires college) */
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-semibold text-slate-600 uppercase mb-1">
                    Select Institution
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                    <select
                      value={filters.institution_id || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, institution_id: Number(e.target.value) })
                      }
                      className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium truncate"
                    >
                      {institutions.map((inst) => (
                        <option key={inst.id} value={inst.id}>
                          {inst.name} ({inst.aicte_id}) - {inst.state}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Optional Course Search */}
              {!activeMeta.requiresCollege && (
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 uppercase mb-1">
                    Discipline Search
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Computer Science"
                    value={filters.course || ""}
                    onChange={(e) => setFilters({ ...filters, course: e.target.value })}
                    onKeyDown={(e) => e.key === "Enter" && loadPreview()}
                    className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Key Summary Metrics Cards */}
          {preview?.summary_boxes && preview.summary_boxes.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {preview.summary_boxes.map((box, idx) => (
                <div
                  key={idx}
                  className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between"
                >
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    {box.label}
                  </span>
                  <div className="mt-1">
                    <span className="text-xl font-bold text-slate-900">{box.value}</span>
                    {box.detail && (
                      <span className="block text-[10px] text-blue-600 font-medium truncate mt-0.5">
                        {box.detail}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Interactive Live Preview Data Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-bold text-slate-800">
                  Data Preview ({preview?.total_records ?? 0} records)
                </span>
              </div>
              <span className="text-[11px] text-slate-500">
                Generated: {preview?.generated_at ?? "-"}
              </span>
            </div>

            {loadingPreview ? (
              <div className="p-12 text-center text-slate-500 text-sm">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
                Aggregating official repository records...
              </div>
            ) : preview ? (
              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-800 text-white uppercase text-[10px] font-semibold sticky top-0 z-10">
                    <tr>
                      {preview.columns.map((col, idx) => (
                        <th key={idx} className="px-3 py-2.5 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {preview.rows.map((row, rIdx) => (
                      <tr
                        key={rIdx}
                        className={rIdx % 2 === 0 ? "bg-white hover:bg-slate-50" : "bg-slate-50/60 hover:bg-slate-100/60"}
                      >
                        {row.map((cell, cIdx) => (
                          <td
                            key={cIdx}
                            className={`px-3 py-2 whitespace-nowrap ${
                              typeof cell === "number"
                                ? "text-right font-mono"
                                : typeof cell === "string" && cell.includes("OVER INTAKE")
                                ? "text-red-600 font-bold"
                                : "text-slate-700"
                            }`}
                          >
                            {cell ?? "-"}
                          </td>
                        ))}
                      </tr>
                    ))}

                    {/* Totals Row */}
                    {preview.totals_row && (
                      <tr className="bg-blue-50 font-bold text-slate-900 border-t-2 border-slate-300">
                        {preview.totals_row.map((cell, idx) => (
                          <td
                            key={idx}
                            className={`px-3 py-2.5 whitespace-nowrap ${
                              typeof cell === "number" ? "text-right font-mono" : ""
                            }`}
                          >
                            {cell ?? "-"}
                          </td>
                        ))}
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-400 text-xs">
                No preview data available for the selected filters.
              </div>
            )}

            {/* Notes Footer */}
            {preview?.notes && preview.notes.length > 0 && (
              <div className="p-3 bg-slate-50/80 border-t border-slate-100 text-[11px] text-slate-500 space-y-0.5">
                {preview.notes.map((note, idx) => (
                  <p key={idx}>&bull; {note}</p>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default AicteReportsPage;
