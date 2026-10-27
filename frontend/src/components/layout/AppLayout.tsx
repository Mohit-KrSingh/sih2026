import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Navbar } from "./Navbar";
import { Footer } from "./Footer";
import { RoleBadge } from "../ui/Badge";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  FileCheck2,
  FileText,
  KeyRound,
  LayoutDashboard,
  Shield,
  Upload,
  UserCheck,
  Users,
} from "lucide-react";

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

export function AppLayout({ children }: { children?: React.ReactNode }) {
  const { user, isAicte, isCollege } = useAuth();
  const location = useLocation();

  const collegeNav: NavItem[] = [
    { label: "Dashboard", path: "/college/dashboard", icon: <LayoutDashboard className="w-4 h-4" /> },
    { label: "Seats & Intake", path: "/college/seats", icon: <Building2 className="w-4 h-4" /> },
    { label: "Students", path: "/college/students", icon: <Users className="w-4 h-4" /> },
    { label: "Bulk Upload", path: "/college/upload", icon: <Upload className="w-4 h-4" /> },
    { label: "Validation Flags", path: "/college/validation", icon: <AlertTriangle className="w-4 h-4" /> },
    { label: "Submit Data", path: "/college/submit", icon: <CheckCircle2 className="w-4 h-4" /> },
    { label: "Staff", path: "/college/staff", icon: <UserCheck className="w-4 h-4" /> },
    { label: "API Keys", path: "/college/api-keys", icon: <KeyRound className="w-4 h-4" /> },
  ];

  const aicteNav: NavItem[] = [
    { label: "Overview", path: "/aicte/overview", icon: <LayoutDashboard className="w-4 h-4" /> },
    { label: "Approvals Queue", path: "/aicte/approvals", icon: <CheckCircle2 className="w-4 h-4" /> },
    { label: "Intake Control", path: "/aicte/intake", icon: <Building2 className="w-4 h-4" /> },
    { label: "Compliance & Over-Intake", path: "/aicte/compliance", icon: <AlertTriangle className="w-4 h-4" /> },
    { label: "Duplicates", path: "/aicte/duplicates", icon: <Users className="w-4 h-4" /> },
    { label: "Anomaly Detection", path: "/aicte/anomalies", icon: <Shield className="w-4 h-4" /> },
    { label: "Review Queue", path: "/aicte/review", icon: <FileCheck2 className="w-4 h-4" /> },
    { label: "Reports & Exports", path: "/aicte/reports", icon: <FileText className="w-4 h-4" /> },
    { label: "Audit Log Chain", path: "/aicte/audit", icon: <Shield className="w-4 h-4" /> },
  ];

  const navItems = isAicte ? aicteNav : isCollege ? collegeNav : [];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Navbar />

      {/* Sub-header with User banner & navigation tabs */}
      {user && (
        <div className="bg-white border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center font-bold text-sm">
                {user.email.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-semibold text-slate-900">{user.email}</span>
                  <RoleBadge role={user.role} />
                </div>
                {user.institution_id && (
                  <p className="text-xs text-slate-500">
                    Institution ID: <span className="font-mono font-medium">{user.institution_id}</span>
                  </p>
                )}
              </div>
            </div>

            {/* Quick role indicator */}
            <div className="text-xs text-slate-500 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Session active &bull; RBAC verified</span>
            </div>
          </div>

          {/* Tab Navigation */}
          {navItems.length > 0 && (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 overflow-x-auto scrollbar-none">
              <nav className="flex space-x-1 sm:space-x-2 border-t border-slate-100 pt-1 pb-1">
                {navItems.map((item) => {
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md whitespace-nowrap transition ${
                        active
                          ? "bg-blue-50 text-blue-700 font-semibold border-b-2 border-blue-600 rounded-b-none"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          )}
        </div>
      )}

      {/* Main app content */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {children}
      </main>

      <Footer />
    </div>
  );
}
