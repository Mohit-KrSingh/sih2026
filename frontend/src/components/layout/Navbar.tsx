import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { RoleBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { LogOut, Menu, X } from "lucide-react";
import { PRODUCT_NAME } from "../../brand";
import { EduTraceIcon } from "../brand/EduTraceLogo";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-40">
      {/* Top micro-bar: Government of India / AICTE header */}
      <div className="bg-slate-950 text-slate-400 text-[11px] py-1 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-300">All India Council for Technical Education</span>
            <span>&bull;</span>
            <span>Ministry of Education, Govt. of India</span>
          </div>
          <div className="flex items-center space-x-3">
            <span className="hidden sm:inline">One Nation, One Student ID</span>
            <span className="text-amber-400 font-mono text-[10px] bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800/40">
              SIH 2026
            </span>
          </div>
        </div>
      </div>

      {/* Main navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-lg bg-blue-700 flex items-center justify-center text-white font-bold text-lg shadow-sm group-hover:bg-blue-600 transition">
              <EduTraceIcon size={22} className="text-amber-300" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">{PRODUCT_NAME}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-blue-800/80 text-blue-200 border border-blue-700 font-medium">
                  Central Portal
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-tight">
                Student Data Management & Verification System
              </p>
            </div>
          </Link>

          {/* Desktop Links */}
          <nav className="hidden md:flex items-center space-x-1 lg:space-x-2 text-sm font-medium">
            <Link
              to="/"
              className={`px-3 py-1.5 rounded-md transition ${
                isActive("/") ? "bg-slate-800 text-white font-semibold" : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Home
            </Link>
            <Link
              to="/activate"
              className={`px-3 py-1.5 rounded-md transition ${
                isActive("/activate") ? "bg-slate-800 text-white font-semibold" : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Activate College
            </Link>
            <Link
              to="/verify"
              className={`px-3 py-1.5 rounded-md transition ${
                isActive("/verify") ? "bg-slate-800 text-white font-semibold" : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Verify Record
            </Link>
            <Link
              to="/student"
              className={`px-3 py-1.5 rounded-md transition ${
                isActive("/student") ? "bg-slate-800 text-white font-semibold" : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Student Portal
            </Link>
            <Link
              to="/privacy"
              className={`px-3 py-1.5 rounded-md transition ${
                isActive("/privacy") ? "bg-slate-800 text-white font-semibold" : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Privacy & DPDP
            </Link>
          </nav>

          {/* Right actions: User menu or login buttons */}
          <div className="hidden md:flex items-center space-x-3">
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-3 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
                <div className="text-right">
                  <p className="text-xs font-semibold text-slate-200 leading-tight truncate max-w-[160px]">
                    {user.email}
                  </p>
                  <RoleBadge role={user.role} className="mt-0.5 text-[10px]" />
                </div>
                <Link
                  to={
                    user.role === "aicte_admin" || user.role === "aicte_officer"
                      ? "/aicte/overview"
                      : user.role === "verifier"
                      ? "/verifier/search"
                      : "/college/dashboard"
                  }
                  className="px-2.5 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition"
                >
                  Dashboard
                </Link>
                <button
                  onClick={logout}
                  title="Sign out of account"
                  className="text-slate-400 hover:text-red-400 p-1 rounded transition"
                  aria-label="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link to="/login/college">
                  <Button variant="outline" size="sm" className="bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700">
                    College Login
                  </Button>
                </Link>
                <Link to="/login/aicte">
                  <Button variant="primary" size="sm" className="bg-blue-600 hover:bg-blue-500">
                    AICTE Login
                  </Button>
                </Link>
              </div>
            )}
          </div>

          {/* Mobile hamburger button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-900 px-4 pt-2 pb-4 space-y-2">
          <Link
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:bg-slate-800"
          >
            Home
          </Link>
          <Link
            to="/activate"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:bg-slate-800"
          >
            Activate College
          </Link>
          <Link
            to="/verify"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:bg-slate-800"
          >
            Verify Record
          </Link>
          <Link
            to="/student"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:bg-slate-800"
          >
            Student Portal
          </Link>
          <Link
            to="/privacy"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:bg-slate-800"
          >
            Privacy & DPDP
          </Link>

          <div className="pt-4 border-t border-slate-800 space-y-2">
            {isAuthenticated && user ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400 truncate">{user.email}</span>
                  <RoleBadge role={user.role} />
                </div>
                <Link
                  to={
                    user.role === "aicte_admin" || user.role === "aicte_officer"
                      ? "/aicte/overview"
                      : user.role === "verifier"
                      ? "/verifier/search"
                      : "/college/dashboard"
                  }
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-center w-full py-2 bg-blue-600 text-white rounded font-medium text-sm"
                >
                  Go to Dashboard
                </Link>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-red-400 border-red-900/40 bg-slate-950"
                >
                  Sign Out
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Link to="/login/college" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full bg-slate-800 border-slate-700 text-slate-200">
                    College Login
                  </Button>
                </Link>
                <Link to="/login/aicte" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="primary" size="sm" className="w-full bg-blue-600">
                    AICTE Login
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
