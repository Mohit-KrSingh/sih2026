import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHealthApi, type HealthResponse } from "../api/health";
import { Button } from "../components/ui/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { APAAR_EXPLAINER, PRODUCT_NAME, TAGLINE } from "../brand";
import {
  ArrowRight,
  Building2,
  ExternalLink,
  Lock,
  Search,
  Server,
  ShieldCheck,
  UserCheck,
} from "lucide-react";

export function HomePage() {
  useDocumentTitle("National Student Registry & Verification Portal");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  useEffect(() => {
    getHealthApi()
      .then((data) => {
        setHealth(data);
        setLoadingHealth(false);
      })
      .catch(() => {
        setLoadingHealth(false);
      });
  }, []);

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center max-w-4xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-xs font-semibold tracking-wide border border-blue-200">
          <ShieldCheck className="w-4 h-4 text-blue-700" />
          <span>AICTE Smart India Hackathon 2026 Initiative</span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          {PRODUCT_NAME}: <br className="hidden sm:inline" />
          <span className="text-blue-700">{TAGLINE}</span>
        </h1>
        <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          National platform for AICTE-approved institutions to upload APAAR-keyed student data,
          automatically detect over-admissions & duplicate enrolments, and offer privacy-first cryptographic verification.
        </p>
        <p className="text-xs sm:text-sm text-slate-700 max-w-2xl mx-auto bg-slate-100 py-2 px-4 rounded-lg border border-slate-200 leading-normal">
          <strong>What is an APAAR ID?</strong> {APAAR_EXPLAINER}
        </p>
      </section>

      {/* The Four Entry Cards (SPEC.md Section 1 & Section 19) */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">System Entry Portals</h2>
          <span className="text-xs text-slate-500 font-medium">Select your portal to continue</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1: Activate College */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100 group-hover:scale-105 transition-transform">
                <Building2 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Activate College</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Claim your institution with verified AICTE master records, OTP verification to official contacts, and authorization letter upload.
              </p>
            </div>
            <div className="pt-6">
              <Link to="/activate" className="w-full block">
                <Button variant="outline" size="sm" className="w-full justify-between" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Begin activation
                </Button>
              </Link>
            </div>
          </div>

          {/* Card 2: College Login */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center border border-blue-100 group-hover:scale-105 transition-transform">
                <Lock className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">College Login</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Declare approved course seat allocations, upload student records via CSV/API, resolve validation flags, and submit data.
              </p>
            </div>
            <div className="pt-6">
              <Link to="/login/college" className="w-full block">
                <Button variant="primary" size="sm" className="w-full justify-between" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Sign in as college
                </Button>
              </Link>
            </div>
          </div>

          {/* Card 3: AICTE Login */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center border border-indigo-100 group-hover:scale-105 transition-transform">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">AICTE Login</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Monitor live intake compliance, resolve duplicate enrolment alerts, inspect ML anomaly clusters, and review submissions.
              </p>
            </div>
            <div className="pt-6">
              <Link to="/login/aicte" className="w-full block">
                <Button variant="secondary" size="sm" className="w-full justify-between" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Sign in to AICTE
                </Button>
              </Link>
            </div>
          </div>

          {/* Card 4: Verify Student Record */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center border border-amber-100 group-hover:scale-105 transition-transform">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Verify Record</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Authorized employers and regulators verify student credentials via cryptographic Ed25519 signature and student consent.
              </p>
            </div>
            <div className="pt-6">
              <Link to="/verify" className="w-full block">
                <Button variant="outline" size="sm" className="w-full justify-between" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Verify credential
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Live System Connectivity & Architecture Stats */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Server className="w-4 h-4 text-blue-600" />
              System Architecture & Health Status
            </h3>
            <p className="text-xs text-slate-500">Live connectivity check with backend engine and persistence layers</p>
          </div>
          {loadingHealth ? (
            <span className="text-xs text-slate-600">Pinging backend...</span>
          ) : health ? (
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="text-xs font-semibold text-emerald-700 uppercase" data-testid="overall-status">
                {health.status}
              </span>
              <span className="text-xs text-slate-600 font-mono">v{health.version}</span>
            </div>
          ) : (
            <span className="text-xs text-rose-600 font-medium">Backend unreachable</span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Relational Store</p>
              <p className="text-sm font-bold text-slate-800">PostgreSQL 16</p>
              <p className="text-xs text-slate-500">26 tables & hash-chain audit</p>
            </div>
            <span
              className={`px-2.5 py-1 rounded text-xs font-semibold ${
                health?.services?.database === "connected" ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"
              }`}
              data-testid="db-status"
            >
              {health?.services?.database || "Checking..."}
            </span>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Fast Cache & Rate Limit</p>
              <p className="text-sm font-bold text-slate-800">Redis 7</p>
              <p className="text-xs text-slate-500">Sliding window & OTP storage</p>
            </div>
            <span
              className={`px-2.5 py-1 rounded text-xs font-semibold ${
                health?.services?.redis === "connected" ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"
              }`}
              data-testid="redis-status"
            >
              {health?.services?.redis || "Checking..."}
            </span>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Validation Engine</p>
              <p className="text-sm font-bold text-slate-800">Deterministic Engine</p>
              <p className="text-xs text-slate-500">Pure rule functions & RapidFuzz</p>
            </div>
            <span className="px-2.5 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-800">
              Ready
            </span>
          </div>
        </div>
      </section>

      {/* Demo Accounts Quick-Fill Guide */}
      <section className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-800/80 pb-3">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-amber-400" />
              Evaluation Demo Accounts (SIH 2026)
            </h3>
            <p className="text-xs text-blue-200">
              Pre-seeded institutional and officer accounts. Standard password: <code className="bg-blue-800 px-1 py-0.5 rounded font-mono text-amber-300">Demo@12345</code>
            </p>
          </div>
          <span className="text-xs text-amber-300 bg-blue-950/80 border border-blue-700 px-2.5 py-1 rounded-full font-medium">
            Demo Mode Active
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-blue-950/60 rounded border border-blue-800/60 space-y-1">
            <p className="font-semibold text-amber-300">AICTE Central Admin</p>
            <p className="font-mono text-[11px] text-slate-200 truncate">aicte_admin@aicte-india.org</p>
            <p className="text-[11px] text-blue-200">System admin & audit log</p>
            <Link to="/login/aicte" className="inline-flex items-center text-amber-300 hover:underline pt-1 text-[11px]">
              Use account <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="p-3 bg-blue-950/60 rounded border border-blue-800/60 space-y-1">
            <p className="font-semibold text-amber-300">AICTE Compliance Officer</p>
            <p className="font-mono text-[11px] text-slate-200 truncate">aicte_officer@aicte-india.org</p>
            <p className="text-[11px] text-blue-200">Review queue & intake monitor</p>
            <Link to="/login/aicte" className="inline-flex items-center text-amber-300 hover:underline pt-1 text-[11px]">
              Use account <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="p-3 bg-blue-950/60 rounded border border-blue-800/60 space-y-1">
            <p className="font-semibold text-amber-300">College Admin (Stage 1)</p>
            <p className="font-mono text-[11px] text-slate-200 truncate">admin@piaet-pune.edu.in</p>
            <p className="text-[11px] text-blue-200">Pune Inst. of Adv. Engg & Tech</p>
            <Link to="/login/college" className="inline-flex items-center text-amber-300 hover:underline pt-1 text-[11px]">
              Use account <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="p-3 bg-blue-950/60 rounded border border-blue-800/60 space-y-1">
            <p className="font-semibold text-amber-300">Student Consent Portal</p>
            <p className="font-mono text-[11px] text-slate-200 truncate">APAAR: 111122223333</p>
            <p className="text-[11px] text-blue-200">Aarav Sharma (consent history)</p>
            <Link to="/student" className="inline-flex items-center text-amber-300 hover:underline pt-1 text-[11px]">
              Open portal <ExternalLink className="w-3 h-3 ml-1" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
