import { useState } from "react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  Building2,
  CheckCircle2,
  Shield,
} from "lucide-react";

interface VerifierOrg {
  id: number;
  name: string;
  code: string;
  officialEmail: string;
  category: string;
  registeredAt: string;
  status: "active" | "pending_approval" | "suspended";
  verifiedCount: number;
}

export function AicteVerifiersPage() {
  useDocumentTitle("Third-Party Verifier Management");

  const [verifiers, setVerifiers] = useState<VerifierOrg[]>([
    {
      id: 1,
      name: "TCS iON Verification Services",
      code: "VR-TCS-001",
      officialEmail: "verification@tcsion.com",
      category: "Corporate Background Screener",
      registeredAt: "2026-08-15",
      status: "active",
      verifiedCount: 1420,
    },
    {
      id: 2,
      name: "HirePro Background Checks Ltd",
      code: "VR-HP-002",
      officialEmail: "screen@hirepro.in",
      category: "Employment Screener",
      registeredAt: "2026-09-01",
      status: "active",
      verifiedCount: 890,
    },
    {
      id: 3,
      name: "Wipro Talent Authentication Wing",
      code: "VR-WIP-003",
      officialEmail: "talent.auth@wipro.com",
      category: "Direct Employer",
      registeredAt: "2026-10-10",
      status: "pending_approval",
      verifiedCount: 0,
    },
    {
      id: 4,
      name: "AuthBridge Verification Agency",
      code: "VR-AB-004",
      officialEmail: "ops@authbridge.com",
      category: "Credential Verifier",
      registeredAt: "2026-07-22",
      status: "suspended",
      verifiedCount: 340,
    },
  ]);

  const [toast, setToast] = useState<string | null>(null);

  const toggleStatus = (id: number, newStatus: "active" | "suspended") => {
    setVerifiers(
      verifiers.map((v) => (v.id === id ? { ...v, status: newStatus } : v))
    );
    setToast(`Verifier organization status updated to ${newStatus.toUpperCase()}.`);
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">AICTE Central Oversight</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Third-Party Verifier Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Approve and monitor background screening organisations, employers, and authorized verification agencies.
          </p>
        </div>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* Verifier Organizations Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">Registered Verifier Organisations ({verifiers.length})</h2>
          </div>
          <span className="text-xs text-slate-500">SPEC.md Section 14 Regulatory Authority</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Organisation Name & Code</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Official Contact</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Verifications</th>
                <th className="py-3 px-4 text-right">Regulatory Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {verifiers.map((v) => (
                <tr key={v.id} className="hover:bg-slate-50/60 transition">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900">{v.name}</div>
                    <div className="font-mono text-[11px] text-slate-500">{v.code}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-700">{v.category}</td>
                  <td className="py-3 px-4 font-mono text-slate-600">{v.officialEmail}</td>
                  <td className="py-3 px-4">
                    <Badge
                      variant={
                        v.status === "active"
                          ? "success"
                          : v.status === "pending_approval"
                          ? "warning"
                          : "danger"
                      }
                    >
                      {v.status.replace("_", " ").toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-right font-medium text-slate-900">{v.verifiedCount}</td>
                  <td className="py-3 px-4 text-right">
                    {v.status === "pending_approval" && (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => toggleStatus(v.id, "active")}
                        className="text-[11px]"
                      >
                        Approve Verifier
                      </Button>
                    )}
                    {v.status === "active" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => toggleStatus(v.id, "suspended")}
                        className="text-[11px] text-red-600 hover:bg-red-50"
                      >
                        Suspend
                      </Button>
                    )}
                    {v.status === "suspended" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => toggleStatus(v.id, "active")}
                        className="text-[11px] text-emerald-600 hover:bg-emerald-50"
                      >
                        Re-activate
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* DPDP Compliance Card */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 shadow-sm space-y-2 text-xs text-blue-900">
        <div className="flex items-center gap-2 font-bold text-blue-950">
          <Shield className="w-4 h-4 text-blue-700" />
          <span>DPDP Act 2023 & Consent Protection Architecture</span>
        </div>
        <p className="leading-relaxed">
          Third-party verifiers are strictly prohibited from querying student data without explicit student consent. Every
          verification requires a 24-hour single-use OTP consent issued by the student via the APAAR Student Portal. Verifiers
          receive strictly minimized data: Institution Name, Course, Enrolment Years, Completion Status, and Cryptographic
          Verification ID. Sensitive personal details (DOB, category, address, phone) are never exposed to verifiers.
        </p>
      </div>
    </div>
  );
}
