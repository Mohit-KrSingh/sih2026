import React, { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { Badge, RoleBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import type { Role } from "../types/auth";
import {
  CheckCircle2,
  Shield,
  ShieldAlert,
  UserPlus,
  Users,
} from "lucide-react";

interface StaffMember {
  id: number;
  name: string;
  email: string;
  role: Role;
  department: string;
  status: "active" | "invited" | "disabled";
  lastLogin: string;
}

export function StaffManagementPage() {
  const { user } = useAuth();
  useDocumentTitle("Staff Account Management");

  const isCollegeAdmin = user?.role === "college_admin";

  const [staffList, setStaffList] = useState<StaffMember[]>([
    {
      id: 1,
      name: "Institution Admin",
      email: user?.email || "admin@institution.edu.in",
      role: (user?.role as Role) || "college_admin",
      department: "Registrar's Office",
      status: "active",
      lastLogin: "Active now",
    },
    {
      id: 2,
      name: "Dr. Rajesh Kulkarni",
      email: "staff.admissions@mmit-mumbai.ac.in",
      role: "college_staff",
      department: "Admissions & Enrolment Cell",
      status: "active",
      lastLogin: "Today, 11:20 AM",
    },
    {
      id: 3,
      name: "Pooja Verma",
      email: "viewer.audit@mmit-mumbai.ac.in",
      role: "college_viewer",
      department: "Internal Quality Assurance Cell (IQAC)",
      status: "active",
      lastLogin: "Yesterday, 04:45 PM",
    },
  ]);

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("college_staff");
  const [inviteDept, setInviteDept] = useState("Admissions Cell");
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail || !inviteName) return;

    const newStaff: StaffMember = {
      id: Date.now(),
      name: inviteName,
      email: inviteEmail,
      role: inviteRole,
      department: inviteDept,
      status: "invited",
      lastLogin: "Invitation sent",
    };

    setStaffList([...staffList, newStaff]);
    setSuccessToast(`Staff invitation sent to ${inviteEmail} with role '${inviteRole}'.`);
    setShowInviteModal(false);
    setInviteEmail("");
    setInviteName("");
    setTimeout(() => setSuccessToast(null), 4000);
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">College Portal</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Staff Account Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage institutional operator accounts, RBAC permissions, and delegate upload capabilities.
          </p>
        </div>

        {isCollegeAdmin && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowInviteModal(true)}
            className="flex items-center gap-1.5"
          >
            <UserPlus className="w-4 h-4" /> Add Staff Member
          </Button>
        )}
      </div>

      {successToast && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Staff Accounts Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">Institutional Users ({staffList.length})</h2>
          </div>
          <span className="text-xs text-slate-500">Institution ID #{user?.institution_id ?? 1}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Staff Member</th>
                <th className="py-3 px-4">Role & Permissions</th>
                <th className="py-3 px-4">Department</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Last Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {staffList.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50/60 transition">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900">{m.name}</div>
                    <div className="font-mono text-[11px] text-slate-500">{m.email}</div>
                  </td>
                  <td className="py-3 px-4">
                    <RoleBadge role={m.role} />
                  </td>
                  <td className="py-3 px-4 text-slate-700">{m.department}</td>
                  <td className="py-3 px-4">
                    <Badge variant={m.status === "active" ? "success" : m.status === "invited" ? "warning" : "neutral"}>
                      {m.status.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-[11px]">{m.lastLogin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Role Matrix & Statutory Governance Note */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-xs border-b border-slate-100 pb-2">
            <Shield className="w-4 h-4 text-blue-600" />
            <span>Role-Based Access Control (RBAC) Matrix</span>
          </div>
          <div className="text-xs space-y-2 text-slate-600">
            <div className="flex justify-between border-b border-slate-100 py-1">
              <span className="font-semibold text-slate-800">college_admin:</span>
              <span>Full control &bull; Final Submission &bull; Staff & API Keys</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 py-1">
              <span className="font-semibold text-slate-800">college_staff:</span>
              <span>Student entry &bull; Bulk CSV Upload &bull; Resolve Flags</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="font-semibold text-slate-800">college_viewer:</span>
              <span>Read-only access to records, compliance reports, and audits</span>
            </div>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 shadow-sm space-y-2 text-xs text-blue-900">
          <div className="flex items-center gap-2 font-bold text-blue-950">
            <ShieldAlert className="w-4 h-4 text-blue-700" />
            <span>Hard Rule 1: AICTE Data Protection</span>
          </div>
          <p className="leading-relaxed">
            Institutional operators never edit AICTE-owned data (approved intake quotas, course sanctions, approval status,
            or official notification contacts). Discrepancies can only be raised through official Change Requests with
            statutory evidence.
          </p>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900">Add Staff Account</h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInviteSubmit} className="space-y-4 text-xs">
              <Input
                label="Full Name"
                placeholder="Dr. Rajesh Kulkarni"
                required
                value={inviteName}
                onChange={(e) => setInviteName(e.target.value)}
              />

              <Input
                label="Official Institution Email"
                type="email"
                placeholder="rajesh@institution.edu.in"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />

              <Select
                label="Role Assignment"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as Role)}
                options={[
                  { value: "college_staff", label: "college_staff (Data Entry & Uploads)" },
                  { value: "college_viewer", label: "college_viewer (Read-Only Inspection)" },
                ]}
              />

              <Input
                label="Department / Unit"
                placeholder="Admissions Cell"
                value={inviteDept}
                onChange={(e) => setInviteDept(e.target.value)}
              />

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setShowInviteModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm">
                  Send Invitation
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
