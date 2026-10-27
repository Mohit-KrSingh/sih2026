import React, { useState } from "react";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { UserCheck } from "lucide-react";

export function StudentPortalPage() {
  const [apaarId, setApaarId] = useState("111122223333");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<"id" | "otp" | "dashboard">("id");
  const [isLoading, setIsLoading] = useState(false);

  const handleIdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apaarId.trim()) return;
    setIsLoading(true);
    setTimeout(() => {
      setStep("otp");
      setIsLoading(false);
    }, 400);
  };

  const handleOtpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setStep("dashboard");
      setIsLoading(false);
    }, 400);
  };

  return (
    <div className="max-w-3xl mx-auto py-6 space-y-8">
      <div className="text-center space-y-3">
        <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-800 mx-auto flex items-center justify-center shadow-sm">
          <UserCheck className="w-6 h-6" />
        </div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
          Student Consent & Record Portal
        </h1>
        <p className="text-sm text-slate-600 max-w-xl mx-auto">
          Access your verified APAAR academic records, view colleges holding your enrolment data, and
          approve or revoke third-party verification requests.
        </p>
      </div>

      {step === "id" && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm max-w-md mx-auto space-y-4">
          <h3 className="text-base font-bold text-slate-900">Step 1: Enter your 12-Digit APAAR ID</h3>
          <form onSubmit={handleIdSubmit} className="space-y-4">
            <Input
              label="APAAR Identification Number"
              placeholder="12-digit national ID"
              value={apaarId}
              onChange={(e) => setApaarId(e.target.value)}
              hint="Demo student ID: 111122223333 (Aarav Sharma)"
              required
            />
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              isLoading={isLoading}
              loadingText="Checking registry..."
            >
              Send verification OTP
            </Button>
          </form>
        </div>
      )}

      {step === "otp" && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm max-w-md mx-auto space-y-4">
          <h3 className="text-base font-bold text-slate-900">Step 2: Enter Verification OTP</h3>
          <p className="text-xs text-slate-500">
            A 6-digit one-time password was dispatched to your mobile number registered with APAAR registry.
          </p>
          <form onSubmit={handleOtpSubmit} className="space-y-4">
            <Input
              label="6-Digit OTP"
              placeholder="123456"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              hint="In demo mode, enter any 6 digits (e.g. 123456)"
              required
              autoFocus
            />
            <div className="flex gap-2">
              <Button type="button" variant="outline" className="w-1/2" onClick={() => setStep("id")}>
                Back
              </Button>
              <Button
                type="submit"
                variant="primary"
                className="w-1/2"
                isLoading={isLoading}
                loadingText="Verifying..."
              >
                Access records
              </Button>
            </div>
          </form>
        </div>
      )}

      {step === "dashboard" && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Academic Identity
                </span>
                <h3 className="text-lg font-bold text-slate-900">Aarav Sharma</h3>
                <p className="font-mono text-xs text-slate-500">APAAR ID: 111122223333</p>
              </div>
              <Badge variant="success">Verified in Central Registry</Badge>
            </div>

            <div className="space-y-3 pt-2">
              <h4 className="text-sm font-bold text-slate-800">Institutions Holding Your Record</h4>
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-sm text-slate-900">
                    Pune Institute of Advanced Engineering & Technology
                  </p>
                  <p className="text-xs text-slate-500">B.Tech Computer Engineering &bull; 2026-27</p>
                </div>
                <Badge variant="primary">Active Enrolment</Badge>
              </div>
            </div>

            <div className="space-y-3 pt-4 border-t border-slate-100">
              <h4 className="text-sm font-bold text-slate-800">Third-Party Verification Consent</h4>
              <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 flex justify-between items-center text-xs">
                <div>
                  <p className="font-semibold text-emerald-900">
                    Tata Consultancy Services - Background Verifications
                  </p>
                  <p className="text-emerald-700">Scope: Institution, Course, Status &bull; Expires in 24h</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="success">Consented</Badge>
                  <Button size="sm" variant="outline" className="text-xs py-1 px-2 border-red-200 text-red-700">
                    Revoke
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
