import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ux4g/Button";
import { Input } from "../components/ux4g/Input";
import { FormField } from "../components/ux4g/FormField";
import { Card, CardBody } from "../components/ux4g/Card";
import { Badge } from "../components/ux4g/Badge";
import { Alert } from "../components/ux4g/Alert";
import { Icon } from "../components/ux4g/Icon";
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

  const fromLocation = (
    location.state as { from?: { pathname: string; search?: string; hash?: string } }
  )?.from;
  const returnUrl = fromLocation
    ? `${fromLocation.pathname}${fromLocation.search || ""}${fromLocation.hash || ""}`
    : null;

  const getTargetDashboard = (userRole?: string) => {
    if (returnUrl) return returnUrl;
    if (
      userRole === "college_admin" ||
      userRole === "college_staff" ||
      userRole === "college_viewer"
    ) {
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
      setError(
        err instanceof Error ? err.message : "Sign-in failed. Check your email and password."
      );
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
      setError(
        err instanceof Error
          ? err.message
          : "Invalid code. Enter the 6-digit code from your authenticator app."
      );
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
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-soft mx-auto flex items-center justify-center shadow-sm">
          <Icon name="shield" size="lg" color="primary" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold ux4g-text-neutral-primary tracking-tight">AICTE Central Portal</h1>
        <p className="text-xs ux4g-text-neutral-secondary">
          Restricted access for authorized AICTE administrators and compliance officers.
        </p>
      </div>

      {error && (
        <Alert variant="error" title="Sign-in Error">
          {error}
        </Alert>
      )}

      <Card variant="outline" className="p-6">
        <CardBody className="p-0">
          {pendingMfa ? (
            /* MFA Step */
            <form onSubmit={handleMfaSubmit} className="space-y-4" data-testid="aicte-mfa-form">
              <div className="p-3 border ux4g-border-primary ux4g-bg-primary-soft rounded-lg flex items-center gap-3">
                <Icon name="verified_user" size="md" color="primary" className="shrink-0" aria-hidden="true" />
                <div className="text-xs ux4g-text-neutral-primary">
                  <p className="font-semibold">Security Verification: Multi-Factor Authentication</p>
                  <p className="ux4g-text-neutral-secondary">Enter your 6-digit TOTP authenticator code.</p>
                </div>
              </div>

              <FormField
                id="aicte-mfa-input"
                label="Authenticator Code"
                hint="6-digit authenticator code"
                required
              >
                <Input
                  id="aicte-mfa-input"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={8}
                  placeholder="123456"
                  required
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  autoFocus
                />
              </FormField>

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
                  variant="primary"
                  className="w-1/2"
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
              <FormField id="aicte-email-input" label="Official AICTE Email" required>
                <Input
                  id="aicte-email-input"
                  type="email"
                  placeholder="officer@aicte-india.org"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                />
              </FormField>

              <FormField id="aicte-password-input" label="Password" required>
                <Input
                  id="aicte-password-input"
                  type="password"
                  placeholder="••••••••••••"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </FormField>

              <Button
                type="submit"
                variant="primary"
                fullWidth
                isLoading={isLoading}
                loadingText="Signing in..."
                leftIcon={<Icon name="key" size="xs" color="inherit" aria-hidden="true" />}
              >
                Sign in to AICTE portal
              </Button>
            </form>
          )}
        </CardBody>
      </Card>

      {/* Demo AICTE Credentials Helper */}
      {!pendingMfa && (
        <div className="border ux4g-border-neutral-subtle ux4g-bg-neutral-soft rounded-xl p-4 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold ux4g-text-neutral-primary flex items-center gap-1.5">
              <Icon name="key" size="xs" color="primary" aria-hidden="true" />
              Demo AICTE Accounts
            </span>
            <span className="ux4g-text-neutral-secondary font-mono text-[11px]">Password: Demo@12345</span>
          </div>

          <div className="space-y-1.5">
            <button
              type="button"
              aria-label="Fill demo credentials for AICTE System Administrator"
              onClick={() => quickFill("aicte_admin@aicte-india.org")}
              className="w-full text-left p-2 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated hover:border-current transition flex justify-between items-center"
            >
              <div>
                <p className="font-medium ux4g-text-neutral-primary">AICTE System Administrator</p>
                <p className="text-[11px] ux4g-text-neutral-secondary font-mono">aicte_admin@aicte-india.org</p>
              </div>
              <Badge variant="primary">aicte_admin</Badge>
            </button>

            <button
              type="button"
              aria-label="Fill demo credentials for AICTE Compliance Officer"
              onClick={() => quickFill("aicte_officer@aicte-india.org")}
              className="w-full text-left p-2 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated hover:border-current transition flex justify-between items-center"
            >
              <div>
                <p className="font-medium ux4g-text-neutral-primary">AICTE Compliance Officer</p>
                <p className="text-[11px] ux4g-text-neutral-secondary font-mono">aicte_officer@aicte-india.org</p>
              </div>
              <Badge variant="neutral">aicte_officer</Badge>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
