import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getComplianceList } from "../api/analytics";
import { downloadReportFile } from "../api/reports";
import type { ComplianceViolation } from "../types/analytics";
import { NoticeModal } from "../components/action/NoticeModal";
import { Button } from "../components/ux4g/Button";
import { FlagBadge } from "../components/ux4g/Badge";
import { Spinner } from "../components/ux4g/Spinner";
import { Icon } from "../components/ux4g/Icon";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ux4g/Table";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

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
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className="text-xs font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border"
              style={{
                backgroundColor: "var(--ux4g-color-red-50)",
                color: "var(--ux4g-color-red-800)",
                borderColor: "var(--ux4g-color-red-300)",
              }}
            >
              AICTE Compliance Oversight
            </span>
            <span className="text-xs ux4g-text-neutral-secondary font-medium">
              &bull; Section 12 Regulatory Monitor
            </span>
          </div>
          <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight">
            Over-Intake Compliance & Red List
          </h1>
          <p className="text-xs ux4g-text-neutral-secondary mt-1">
            Real-time identification of institutions admitting students beyond statutory AICTE approved regular capacity
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Academic Year Selector */}
          <div className="flex items-center gap-1.5 ux4g-bg-neutral-soft border ux4g-border-neutral-subtle rounded-lg px-2.5 py-1.5 text-xs">
            <Icon name="calendar_month" size="xs" color="inherit" className="ux4g-text-neutral-secondary" />
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold ux4g-text-neutral-primary focus:outline-none cursor-pointer"
              aria-label="Select Academic Year"
            >
              <option value="2026-27">Academic Year 2026-27</option>
              <option value="2025-26">Academic Year 2025-26 (History)</option>
            </select>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={loadData}
            leftIcon={<Icon name="refresh" size="xs" color="inherit" />}
          >
            Refresh
          </Button>

          {/* Export Actions */}
          <div className="flex items-center gap-1.5 border-l ux4g-border-neutral-subtle pl-3">
            <Button
              size="sm"
              variant="outline"
              disabled={downloading !== null}
              onClick={() => handleExport("csv")}
              leftIcon={<Icon name="download" size="xs" color="inherit" />}
            >
              CSV
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={downloading !== null}
              onClick={() => handleExport("xlsx")}
              leftIcon={<Icon name="download" size="xs" color="inherit" />}
            >
              Excel
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={downloading !== null}
              onClick={() => handleExport("pdf")}
              leftIcon={<Icon name="download" size="xs" color="inherit" />}
            >
              PDF
            </Button>
          </div>
        </div>
      </div>

      {/* Red-List Alert Banner */}
      <div
        className="p-5 rounded-xl border-2 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm"
        style={{
          borderColor: "var(--ux4g-color-red-400)",
          backgroundColor: "var(--ux4g-color-red-50)",
        }}
      >
        <div className="flex items-start gap-3">
          <span
            className="p-2 rounded-xl text-white shrink-0 mt-0.5"
            style={{ backgroundColor: "var(--ux4g-color-red-700)" }}
          >
            <Icon name="warning" size="s" color="inherit" />
          </span>
          <div>
            <h3 className="font-bold text-sm" style={{ color: "var(--ux4g-color-red-950)" }}>
              Statutory Quota Over-Enrolment Mandate
            </h3>
            <p className="text-xs mt-0.5 max-w-3xl" style={{ color: "var(--ux4g-color-red-900)" }}>
              Institutions on this list have enrolled students above approved intake. Regular admissions exceeding capacity violate AICTE Approval Process Handbooks. AICTE officers may issue statutory compliance directives or initiate intake de-allocation.
            </p>
          </div>
        </div>

        <div
          className="flex items-center gap-6 shrink-0 border-t md:border-t-0 md:border-l pt-3 md:pt-0 md:pl-6 text-xs"
          style={{ borderColor: "var(--ux4g-color-red-200)" }}
        >
          <div>
            <p className="ux4g-text-neutral-secondary font-medium">Over-Intake Courses</p>
            <p className="text-2xl font-bold" style={{ color: "var(--ux4g-color-red-700)" }}>
              {filteredViolations.length}
            </p>
          </div>
          <div>
            <p className="ux4g-text-neutral-secondary font-medium">Total Excess Students</p>
            <p className="text-2xl font-bold" style={{ color: "var(--ux4g-color-red-800)" }}>
              +{totalOvershoot}
            </p>
          </div>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full md:w-80">
          <Icon name="search" size="xs" color="inherit" className="ux4g-text-neutral-secondary absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by college name, AICTE ID, course, or state..."
            className="w-full pl-9 pr-3 py-2 text-xs border ux4g-border-neutral-subtle rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ux4g-bg-neutral-elevated ux4g-text-neutral-primary"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
          <div className="flex items-center gap-2">
            <Icon name="filter_alt" size="xs" color="inherit" className="ux4g-text-neutral-secondary" />
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="px-2.5 py-1.5 border ux4g-border-neutral-subtle rounded-lg text-xs font-medium ux4g-text-neutral-primary ux4g-bg-neutral-elevated focus:outline-none"
              aria-label="Filter by state"
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
            <span className="ux4g-text-neutral-secondary">Min Overshoot:</span>
            <select
              value={minOvershoot}
              onChange={(e) => setMinOvershoot(Number(e.target.value))}
              className="px-2 py-1.5 border ux4g-border-neutral-subtle rounded-lg text-xs font-semibold ux4g-text-neutral-primary ux4g-bg-neutral-elevated focus:outline-none"
              aria-label="Filter by minimum overshoot"
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
      <div className="ux4g-bg-neutral-elevated border ux4g-border-neutral-subtle rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <Spinner size="m" />
            <p className="text-xs ux4g-text-neutral-secondary">Scanning institutional student databases...</p>
          </div>
        ) : filteredViolations.length === 0 ? (
          <div className="py-16 text-center ux4g-text-neutral-secondary text-xs">
            <Icon name="verified_user" size="l" color="success" className="mx-auto mb-2" />
            <p className="font-bold ux4g-text-neutral-primary text-sm">No Compliance Violations Found</p>
            <p className="ux4g-text-neutral-secondary mt-1">
              All institutions match approved intake limits matching your filter criteria.
            </p>
          </div>
        ) : (
          <div
            tabIndex={0}
            role="region"
            aria-label="Compliance violations table"
            className="overflow-x-auto w-full focus:outline-none"
          >
            <Table className="min-w-[800px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Institution & AICTE ID</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Course Program</TableHead>
                  <TableHead className="text-center">Approved Intake</TableHead>
                  <TableHead className="text-center">Regular Admitted</TableHead>
                  <TableHead className="text-center">Excess Overshoot</TableHead>
                  <TableHead className="text-center">Supernumerary (Adm/Max)</TableHead>
                  <TableHead className="text-right">Action Directives</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredViolations.map((v, i) => (
                  <TableRow key={`${v.institution_id}-${v.course_id}-${i}`}>
                    <TableCell>
                      <div className="font-bold ux4g-text-neutral-primary">{v.institution_name}</div>
                      <div className="font-mono text-[10px] ux4g-text-neutral-secondary">{v.aicte_id}</div>
                    </TableCell>
                    <TableCell className="font-medium ux4g-text-neutral-primary">{v.state}</TableCell>
                    <TableCell>
                      <span className="font-medium ux4g-text-neutral-primary">{v.course_name}</span>
                      <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] ux4g-bg-neutral-soft ux4g-text-neutral-secondary border ux4g-border-neutral-subtle">
                        {v.level}
                      </span>
                    </TableCell>
                    <TableCell className="text-center font-bold ux4g-text-neutral-primary">
                      {v.approved_intake}
                    </TableCell>
                    <TableCell className="text-center font-bold" style={{ color: "var(--ux4g-color-red-700)" }}>
                      {v.regular_admitted}
                    </TableCell>
                    <TableCell className="text-center">
                      <FlagBadge level="exception" label={`+${v.overshoot} Overshoot`} />
                    </TableCell>
                    <TableCell className="text-center ux4g-text-neutral-secondary">
                      <span className="font-medium ux4g-text-neutral-primary">{v.supernumerary_admitted}</span>
                      <span> / {v.supernumerary_allowed}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="sm"
                          variant="danger"
                          className="text-xs"
                          leftIcon={<Icon name="send" size="xs" color="inherit" />}
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
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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
