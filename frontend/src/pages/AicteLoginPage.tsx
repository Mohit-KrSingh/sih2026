import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { ErrorState } from "../components/ui/ErrorState";
import { KeyRound, ShieldAlert, ShieldCheck } from "lucide-react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function AicteLoginPage() {
  useDocumentTitle("AICTE Central Login");
  const { login, verifyMfa, cancelMfa, pendingMfa } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fromLocation = (location.state as { from?: { pathname: string; search?: string; hash?: string } })?.from;
  const returnUrl = fromLocation
    ? `${fromLocation.pathname}${fromLocation.search || ""}${fromLocation.hash || ""}`
    : null;

  const getTargetDashboard = (userRole?: string) => {
    if (returnUrl) return returnUrl;
    if (userRole === "college_admin" || userRole === "college_staff" || userRole === "college_viewer") {
      return "/college/dashboard";
    }
    if (userRole === "verifier") return "/verifier/search";
    return "/aicte/overview";
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await login({ email, password });
      if (!res.mfaRequired) {
        navigate(getTargetDashboard(res.user?.role), { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed. Check your email and password.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await verifyMfa(mfaCode);
      navigate(getTargetDashboard(), { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code. Enter the 6-digit code from your authenticator app.");
    } finally {
      setIsLoading(false);
    }
  };

  const quickFill = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("Demo@12345");
    setError(null);
  };

  return (
    <div className="max-w-md mx-auto py-6 space-y-6">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-800 mx-auto flex items-center justify-center shadow-sm">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AICTE Central Portal</h1>
        <p className="text-xs text-slate-500">
          Restricted access for authorized AICTE administrators and compliance officers.
        </p>
      </div>

      {error && <ErrorState message={error} />}

      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        {pendingMfa ? (
          /* MFA Step */
          <form onSubmit={handleMfaSubmit} className="space-y-4" data-testid="aicte-mfa-form">
            <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-indigo-700 shrink-0" />
              <div className="text-xs text-indigo-950">
                <p className="font-semibold">Security Verification: Multi-Factor Authentication</p>
                <p className="text-indigo-800">Enter your 6-digit TOTP authenticator code.</p>
              </div>
            </div>

            <Input
              label="Authenticator Code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={8}
              placeholder="123456"
              required
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              hint="6-digit authenticator code"
              autoFocus
            />

            <div className="flex items-center gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                className="w-1/2"
                onClick={() => {
                  cancelMfa();
                  setMfaCode("");
                  setError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="secondary"
                className="w-1/2 bg-indigo-900 hover:bg-indigo-950"
                isLoading={isLoading}
                loadingText="Verifying..."
              >
                Verify and sign in
              </Button>
            </div>
          </form>
        ) : (
          /* Credentials Step */
          <form onSubmit={handleCredentialsSubmit} className="space-y-4" data-testid="aicte-login-form">
            <Input
              label="Official AICTE Email"
              type="email"
              placeholder="officer@aicte-india.org"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />

            <Button
              type="submit"
              variant="secondary"
              className="w-full bg-indigo-900 hover:bg-indigo-950"
              isLoading={isLoading}
              loadingText="Signing in..."
            >
              Sign in to AICTE portal
            </Button>
          </form>
        )}
      </div>

      {/* Demo AICTE Credentials Helper */}
      {!pendingMfa && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-700 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-indigo-700" />
              Demo AICTE Accounts
            </span>
            <span className="text-slate-400 font-mono text-[11px]">Password: Demo@12345</span>
          </div>

          <div className="space-y-1.5">
            <button
              type="button"
              onClick={() => quickFill("aicte_admin@aicte-india.org")}
              className="w-full text-left p-2 rounded bg-white hover:bg-indigo-50 border border-slate-200 transition text-slate-800 flex justify-between items-center"
            >
              <div>
                <p className="font-medium">AICTE System Administrator</p>
                <p className="text-[11px] text-slate-500 font-mono">aicte_admin@aicte-india.org</p>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800 font-medium">
                aicte_admin
              </span>
            </button>

            <button
              type="button"
              onClick={() => quickFill("aicte_officer@aicte-india.org")}
              className="w-full text-left p-2 rounded bg-white hover:bg-indigo-50 border border-slate-200 transition text-slate-800 flex justify-between items-center"
            >
              <div>
                <p className="font-medium">AICTE Compliance Officer</p>
                <p className="text-[11px] text-slate-500 font-mono">aicte_officer@aicte-india.org</p>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-medium">
                aicte_officer
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
