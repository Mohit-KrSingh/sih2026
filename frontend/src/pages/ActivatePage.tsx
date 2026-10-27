import React, { useState } from "react";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { ArrowRight, Building2, CheckCircle2, ShieldCheck } from "lucide-react";

export function ActivatePage() {
  const [aicteId, setAicteId] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [matchedCollege, setMatchedCollege] = useState<{
    id: string;
    name: string;
    state: string;
    email: string;
  } | null>(null);

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    if (!aicteId.trim()) return;
    setIsSearching(true);

    setTimeout(() => {
      // Mock demonstration match based on AICTE seed master
      setMatchedCollege({
        id: aicteId.trim(),
        name: "Pune Institute of Advanced Engineering & Technology",
        state: "Maharashtra",
        email: "c***t@piaet-pune.edu.in",
      });
      setIsSearching(false);
    }, 400);
  };

  return (
    <div className="max-w-3xl mx-auto py-6 space-y-8">
      <div className="text-center space-y-3">
        <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-800 mx-auto flex items-center justify-center shadow-sm">
          <Building2 className="w-6 h-6" />
        </div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
          Activate Your Institution Account
        </h1>
        <p className="text-sm text-slate-600 max-w-xl mx-auto">
          AICTE approved institutions must claim their institution profile and complete verification
          to manage student APAAR records.
        </p>
      </div>

      {/* Activation Steps Flow */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
          <span className="font-bold text-blue-600 font-mono text-sm">01</span>
          <p className="font-semibold text-slate-800">Claim AICTE ID</p>
          <p className="text-slate-500 text-[11px]">Query approved master directory</p>
        </div>

        <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
          <span className="font-bold text-blue-600 font-mono text-sm">02</span>
          <p className="font-semibold text-slate-800">Official OTP</p>
          <p className="text-slate-500 text-[11px]">Sent strictly to on-file contact</p>
        </div>

        <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
          <span className="font-bold text-blue-600 font-mono text-sm">03</span>
          <p className="font-semibold text-slate-800">Signatory Check</p>
          <p className="text-slate-500 text-[11px]">Identity verification & letter upload</p>
        </div>

        <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
          <span className="font-bold text-blue-600 font-mono text-sm">04</span>
          <p className="font-semibold text-slate-800">AICTE Approval</p>
          <p className="text-slate-500 text-[11px]">Officer review & MFA credentials</p>
        </div>
      </div>

      {/* Claim Lookup Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="text-base font-bold text-slate-900">Step 1: Enter AICTE Permanent Institute ID</h3>
        <p className="text-xs text-slate-500">
          Your unique AICTE approval number as listed in the current Approval Process Handbook.
        </p>

        <form onSubmit={handleLookup} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 items-end">
            <div className="flex-1 w-full">
              <Input
                label="AICTE Institute Identifier"
                placeholder="e.g. 1-10000001"
                value={aicteId}
                onChange={(e) => setAicteId(e.target.value)}
                hint="Sample seed ID: 1-10000001 or 1-10000002"
                required
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSearching}
              loadingText="Querying..."
              className="shrink-0 mb-0.5 sm:mb-1 w-full sm:w-auto"
            >
              Verify institution
            </Button>
          </div>
        </form>

        {matchedCollege && (
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-xs space-y-3 animate-fadeIn">
            <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>Institution Verified in AICTE Master Directory</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700">
              <div>
                <span className="text-slate-500">Institution Name:</span>
                <p className="font-semibold text-slate-900">{matchedCollege.name}</p>
              </div>
              <div>
                <span className="text-slate-500">State:</span>
                <p className="font-semibold text-slate-900">{matchedCollege.state}</p>
              </div>
              <div>
                <span className="text-slate-500">Official On-File Contact:</span>
                <p className="font-mono text-slate-900">{matchedCollege.email}</p>
              </div>
              <div>
                <span className="text-slate-500">Next Step:</span>
                <p className="text-slate-700">Dispatch OTP to official on-file email</p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-emerald-200/80">
              <span className="text-[11px] text-emerald-800">
                Full 5-step interactive activation wizard will proceed in T11.
              </span>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  // Ready for T11 activation wizard flow
                }}
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
              >
                Send OTP to official contact
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Security notice */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 space-y-2">
        <h4 className="font-semibold text-slate-800 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Strict Contact Verification Policy
        </h4>
        <p>
          Per SPEC.md Section 11, OTP codes are delivered exclusively to registered institutional
          addresses in the AICTE master directory. User-supplied contact info cannot be used for
          account activation.
        </p>
      </div>
    </div>
  );
}
