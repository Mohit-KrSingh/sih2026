import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getPrivacyPolicy,
  FALLBACK_PRIVACY_DATA,
  type PrivacyPolicyResponse,
} from "../api/privacy";
import { Button } from "../components/ui/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  EyeOff,
  FileCheck2,
  KeyRound,
  Lock,
  Mail,
  MapPin,
  Scale,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";

export function PrivacyPage() {
  useDocumentTitle("DPDP Privacy Architecture & Charter");
  const [policy, setPolicy] = useState<PrivacyPolicyResponse>(FALLBACK_PRIVACY_DATA);
  const [activeTab, setActiveTab] = useState<"collected" | "prohibited">("collected");

  useEffect(() => {
    getPrivacyPolicy().then((data) => {
      setPolicy(data);
    });
  }, []);

  return (
    <div className="space-y-10 max-w-6xl mx-auto py-2">
      {/* Hero Header */}
      <section className="text-center space-y-4 max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold tracking-wide border border-emerald-200">
          <ShieldCheck className="w-4 h-4 text-emerald-700" />
          <span>Digital Personal Data Protection (DPDP) Act, 2023 Compliant</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
          Privacy Policy & Data Minimisation Charter
        </h1>
        <p className="text-base text-slate-600 leading-relaxed">
          The AICTE Central Repository enforces strict data minimisation, cryptographic field
          protection, and student-consented verification for all technical higher education
          institutions across India.
        </p>
      </section>

      {/* DPDP Core Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center mx-auto mb-2">
            <Scale className="w-5 h-5" />
          </div>
          <div className="text-2xl font-bold text-slate-900">16 Fields Only</div>
          <div className="text-xs text-slate-500 font-medium">Strict Data Minimisation</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto mb-2">
            <UserCheck className="w-5 h-5" />
          </div>
          <div className="text-2xl font-bold text-slate-900">100% Consented</div>
          <div className="text-xs text-slate-500 font-medium">Student Gated Verification</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <div className="w-9 h-9 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center mx-auto mb-2">
            <Clock className="w-5 h-5" />
          </div>
          <div className="text-2xl font-bold text-slate-900">24-Hour TTL</div>
          <div className="text-xs text-slate-500 font-medium">Single-Use Consent Tokens</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <div className="w-9 h-9 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center mx-auto mb-2">
            <Lock className="w-5 h-5" />
          </div>
          <div className="text-2xl font-bold text-slate-900">AES-128 / Fernet</div>
          <div className="text-xs text-slate-500 font-medium">Encrypted DOB at Rest</div>
        </div>
      </div>

      {/* Statutory Roles & Fiduciary Notice */}
      <div className="bg-gradient-to-r from-slate-900 to-blue-950 text-white rounded-2xl p-6 sm:p-8 shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <span className="text-xs font-semibold tracking-wider uppercase text-blue-300">
              Statutory Data Fiduciary Notice
            </span>
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              {policy.data_fiduciary.name}
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              {policy.data_fiduciary.ministry} &bull; Operating under the statutory authority of the{" "}
              <strong className="text-white">{policy.data_fiduciary.statutory_mandate}</strong>.
              All personal student data is processed with legal accountability and strict purpose
              limitation.
            </p>
          </div>
          <div className="shrink-0 flex flex-col sm:flex-row gap-3">
            <Link to="/student">
              <Button
                variant="primary"
                className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
              >
                <UserCheck className="w-4 h-4 mr-2" />
                Student Portal
              </Button>
            </Link>
            <Link to="/verify">
              <Button
                variant="outline"
                className="w-full sm:w-auto text-white border-slate-600 hover:bg-slate-800"
              >
                <FileCheck2 className="w-4 h-4 mr-2" />
                Verify Record
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Four Core Pillars Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pillar 1: Purpose Limitation */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-700">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">1. Purpose Limitation</h3>
              <p className="text-xs text-slate-500">Lawful regulatory processing mandates</p>
            </div>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            Data collected by the AICTE Central Repository is processed strictly for official
            higher educational accreditation, quota accounting, and academic verification. It is
            strictly barred from commercial profiling, monetization, or third-party resale.
          </p>
          <ul className="space-y-2 text-xs text-slate-700">
            {policy.purpose_limitation.map((item, index) => (
              <li key={index} className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Pillar 2: Consent Architecture */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">2. Student Consent Framework</h3>
              <p className="text-xs text-slate-500">Autonomous time-bound verification authority</p>
            </div>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            No employer, verifier, or third party can view student academic credentials without
            prior, authenticated student consent.
          </p>
          <div className="space-y-2.5 text-xs text-slate-700">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                <strong>24-Hour Statutory Expiry:</strong> All consent requests expire after 24
                hours; expired requests cannot be approved.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                <strong>Single-Use Protocol:</strong> Approved consents serve exactly one verifier
                read and are instantly consumed.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <EyeOff className="w-4 h-4 text-purple-600 shrink-0" />
              <span>
                <strong>Zero Personal Data Disclosure:</strong> Verifiers never see Date of Birth,
                reservation category, or personal contacts.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0" />
              <span>
                <strong>Audited Decisions:</strong> Every request, student decision, and verifier
                read writes to the immutable hash chain.
              </span>
            </div>
          </div>
        </div>

        {/* Pillar 3: Cryptographic Safeguards */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-purple-50 text-purple-700">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">3. Cryptographic Safeguards</h3>
              <p className="text-xs text-slate-500">Hardware-grade encryption and log masking</p>
            </div>
          </div>
          <div className="space-y-3 text-xs text-slate-700">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="font-semibold text-slate-900 block mb-1">
                Date of Birth Encryption:
              </span>
              <p className="text-slate-600 leading-relaxed">
                {policy.cryptographic_safeguards.dob_encryption}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="font-semibold text-slate-900 block mb-1">
                Runtime Log Redaction:
              </span>
              <p className="text-slate-600 leading-relaxed">
                {policy.cryptographic_safeguards.apaar_log_redaction}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="font-semibold text-slate-900 block mb-1">
                Verifiable Credentials:
              </span>
              <p className="text-slate-600 leading-relaxed">
                {policy.cryptographic_safeguards.verifiable_credentials}
              </p>
            </div>
          </div>
        </div>

        {/* Pillar 4: Data Principal Rights */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-amber-50 text-amber-700">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">4. Student Statutory Rights</h3>
              <p className="text-xs text-slate-500">Rights under Chapter III of the DPDP Act 2023</p>
            </div>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            As Data Principals, enrolled students exercise autonomous rights over their academic
            records and verification requests.
          </p>
          <ul className="space-y-2 text-xs text-slate-700">
            {policy.data_principal_rights.map((right, index) => (
              <li key={index} className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>{right}</span>
              </li>
            ))}
          </ul>
          <div className="pt-2">
            <Link to="/student" className="inline-flex items-center text-xs font-semibold text-blue-600 hover:text-blue-700">
              Manage consent on the Student Portal <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Link>
          </div>
        </div>
      </div>

      {/* Interactive Data Minimisation Matrix */}
      <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              Data Minimisation Specification (SPEC.md Section 8)
            </h3>
            <p className="text-xs text-slate-500">
              Comparison of strictly collected fields versus prohibited personal data categories
            </p>
          </div>
          <div className="inline-flex p-1 bg-slate-100 rounded-lg border border-slate-200 shrink-0">
            <button
              type="button"
              onClick={() => setActiveTab("collected")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                activeTab === "collected"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Collected Fields ({policy.data_minimisation.collected_fields.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("prohibited")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                activeTab === "prohibited"
                  ? "bg-white text-rose-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Prohibited Fields ({policy.data_minimisation.prohibited_fields.length})
            </button>
          </div>
        </div>

        {activeTab === "collected" ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Group</th>
                  <th className="py-3 px-4">Field Name</th>
                  <th className="py-3 px-4">Purpose & Description</th>
                  <th className="py-3 px-4">Storage Security</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {policy.data_minimisation.collected_fields.map((f, i) => (
                  <tr key={i} className="hover:bg-slate-50/60 transition">
                    <td className="py-2.5 px-4 font-medium text-slate-900">{f.group}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-blue-700">{f.field}</td>
                    <td className="py-2.5 px-4 text-slate-600">{f.description}</td>
                    <td className="py-2.5 px-4">
                      {f.storage.includes("Encrypted") ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 text-[11px] font-semibold border border-purple-200">
                          <Lock className="w-3 h-3 mr-1" />
                          Encrypted at Rest
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[11px] font-medium border border-slate-200">
                          {f.storage}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rose-50 text-rose-900 font-semibold border-b border-rose-100">
                <tr>
                  <th className="py-3 px-4">Prohibited Data Category</th>
                  <th className="py-3 px-4">Statutory Justification & Hard Rule</th>
                  <th className="py-3 px-4">System Enforcement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {policy.data_minimisation.prohibited_fields.map((p, i) => (
                  <tr key={i} className="hover:bg-rose-50/30 transition">
                    <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                      <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                      <span>{p.field}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-600 max-w-md">{p.reason}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 text-[11px] font-semibold border border-rose-200">
                        <ShieldAlert className="w-3 h-3 mr-1" />
                        Hard Rule: Excluded from Schema
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Minimal Consented Disclosure Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 shadow-sm space-y-3">
        <div className="flex items-center gap-3 text-blue-900">
          <EyeOff className="w-5 h-5 text-blue-700 shrink-0" />
          <h4 className="font-bold text-sm">
            Strict Minimal Disclosure on Approved Employer Verifications
          </h4>
        </div>
        <p className="text-xs text-slate-700 leading-relaxed">
          When a student grants consent to a registered verifier, the released record is strictly
          limited to academic proof:
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          {policy.consent_framework.minimal_disclosure_fields.map((field, i) => (
            <span
              key={i}
              className="inline-flex items-center px-2.5 py-1 rounded bg-white border border-blue-200 text-blue-800 text-xs font-mono font-medium shadow-2xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
              {field}
            </span>
          ))}
          <span className="inline-flex items-center px-2.5 py-1 rounded bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium line-through">
            Date of Birth
          </span>
          <span className="inline-flex items-center px-2.5 py-1 rounded bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium line-through">
            Reservation Category
          </span>
          <span className="inline-flex items-center px-2.5 py-1 rounded bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium line-through">
            Phone / Email
          </span>
        </div>
      </div>

      {/* Statutory Grievance Redressal Card */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 shadow-sm space-y-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              Statutory Grievance Redressal & Data Protection Officer (DPO)
            </h3>
            <p className="text-xs text-slate-500">
              In accordance with Section 13 of the Digital Personal Data Protection Act, 2023
            </p>
          </div>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          Students, academic institutions, and verified organisations may contact the designated
          Data Protection Officer for any inquiries regarding data handling, consent revocation, or
          statutory privacy rights.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Data Protection Officer
            </div>
            <div className="text-sm font-bold text-slate-900">
              {policy.grievance_redressal.officer}
            </div>
            <div className="text-xs text-slate-600">{policy.grievance_redressal.designation}</div>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Official Email & SLA
            </div>
            <div className="flex items-center gap-1.5 text-sm font-mono font-semibold text-blue-700">
              <Mail className="w-4 h-4 text-slate-500" />
              <a
                href={`mailto:${policy.grievance_redressal.email}`}
                className="hover:underline"
              >
                {policy.grievance_redressal.email}
              </a>
            </div>
            <div className="text-xs text-emerald-700 font-medium">
              Resolution SLA: {policy.grievance_redressal.resolution_sla}
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Registered Office
            </div>
            <div className="flex items-start gap-1.5 text-xs text-slate-600 leading-relaxed">
              <MapPin className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
              <span>{policy.grievance_redressal.address}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Return Home Footer Action */}
      <div className="flex justify-center pt-2">
        <Link to="/">
          <Button variant="outline" className="px-6 text-slate-700">
            Return to Home Page
          </Button>
        </Link>
      </div>
    </div>
  );
}
export default PrivacyPage;
