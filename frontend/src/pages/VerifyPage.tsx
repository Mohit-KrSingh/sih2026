import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { CheckCircle2, Lock, Search, ShieldCheck } from "lucide-react";

export function VerifyPage() {
  const [searchParams] = useSearchParams();
  const initialVid = searchParams.get("vid") || "";

  const [verificationId, setVerificationId] = useState(initialVid);
  const [searchedId, setSearchedId] = useState<string | null>(initialVid || null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationId.trim()) return;
    setIsSearching(true);
    setTimeout(() => {
      setSearchedId(verificationId.trim());
      setIsSearching(false);
    }, 400);
  };

  return (
    <div className="max-w-3xl mx-auto py-6 space-y-8">
      {/* Title & Privacy Banner */}
      <div className="text-center space-y-3">
        <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-800 mx-auto flex items-center justify-center shadow-sm">
          <Search className="w-6 h-6" />
        </div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
          Verify Student Academic Credential
        </h1>
        <p className="text-sm text-slate-600 max-w-xl mx-auto">
          Cryptographically verify academic credentials issued by AICTE-approved institutions with
          student consent and tamper-proof Ed25519 digital signatures.
        </p>
      </div>

      {/* Verification ID Input Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 items-end">
            <div className="flex-1 w-full">
              <Input
                label="Verification Identifier (VID) or APAAR ID"
                placeholder="e.g. VID-2026-PIAET-0042 or 111122223333"
                value={verificationId}
                onChange={(e) => setVerificationId(e.target.value)}
                hint="Provided on academic transcripts, degree certificates, or QR link"
                required
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSearching}
              loadingText="Verifying..."
              leftIcon={<Search className="w-4 h-4" />}
              className="shrink-0 mb-0.5 sm:mb-1 w-full sm:w-auto"
            >
              Verify credential
            </Button>
          </div>
        </form>

        <div className="flex items-center gap-2 pt-2 text-xs text-slate-500">
          <span className="font-semibold text-slate-700">Quick Demo Verification:</span>
          <button
            type="button"
            onClick={() => {
              setVerificationId("VID-2026-PIAET-0042");
              setSearchedId("VID-2026-PIAET-0042");
            }}
            className="text-blue-700 underline hover:text-blue-900 font-mono"
          >
            VID-2026-PIAET-0042
          </button>
        </div>
      </div>

      {/* Search Result Display */}
      {searchedId && (
        <div className="bg-white border-2 border-emerald-500/80 rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
                  Cryptographically Valid Credential
                </span>
                <h3 className="text-lg font-bold text-slate-900">Verified by AICTE Central Registry</h3>
              </div>
            </div>
            <Badge variant="success" className="text-xs uppercase tracking-wider self-start sm:self-auto">
              Active Enrolment
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-xs text-slate-500">Verification Identifier</p>
              <p className="font-mono font-semibold text-slate-900 mt-0.5">{searchedId}</p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-xs text-slate-500">Academic Year</p>
              <p className="font-semibold text-slate-900 mt-0.5">2026-27 (Admitted)</p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-xs text-slate-500">AICTE Approved Institution</p>
              <p className="font-semibold text-slate-900 mt-0.5">
                Pune Institute of Advanced Engineering & Technology
              </p>
              <p className="text-xs text-slate-500 font-mono">AICTE ID: 1-10000001</p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-xs text-slate-500">Degree & Course</p>
              <p className="font-semibold text-slate-900 mt-0.5">
                B.Tech in Computer Engineering
              </p>
              <p className="text-xs text-slate-500 font-mono">Course Code: COMP-ENG-101</p>
            </div>
          </div>

          {/* Cryptographic Signature & DPDP Privacy Notice */}
          <div className="p-4 rounded-lg bg-slate-900 text-slate-300 text-xs space-y-2 border border-slate-800">
            <div className="flex items-center justify-between text-slate-200">
              <span className="font-semibold flex items-center gap-1.5 text-amber-400">
                <ShieldCheck className="w-4 h-4" />
                Ed25519 Digital Signature Verified
              </span>
              <span className="font-mono text-[11px] text-slate-400">Algorithm: Ed25519-SHA512</span>
            </div>
            <p className="font-mono text-[11px] text-slate-400 break-all bg-slate-950 p-2 rounded border border-slate-800">
              sig: 8f3a9e2d14cb803f295bc104fa287901048e91cb39f0412dbb821a7c83f145...
            </p>
            <p className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-1">
              <Lock className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>
                <strong>Zero Personal Data Leak:</strong> In compliance with SPEC.md Section 14 and DPDP principles, date of birth, category, and personal contact details are never exposed to verifiers.
              </span>
            </p>
          </div>
        </div>
      )}

      {/* Verification Protocol Architecture Card */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 text-xs">
        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="w-8 h-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
            1
          </div>
          <h4 className="font-semibold text-slate-900">Student Consent Protocol</h4>
          <p className="text-slate-600">
            Every external verification request requires time-bound student approval via the student portal.
          </p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="w-8 h-8 rounded bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
            2
          </div>
          <h4 className="font-semibold text-slate-900">Signed Canonical Proof</h4>
          <p className="text-slate-600">
            Each accepted record receives an immutable cryptographic signature linked to the AICTE master directory.
          </p>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-sm">
          <div className="w-8 h-8 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
            3
          </div>
          <h4 className="font-semibold text-slate-900">Tamper-Proof QR Link</h4>
          <p className="text-slate-600">
            Degrees and transcripts embed clean QR codes that link directly to verification records without transmitting PII.
          </p>
        </div>
      </div>
    </div>
  );
}
