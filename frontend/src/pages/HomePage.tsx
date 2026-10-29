import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getHealthApi, type HealthResponse } from "../api/health";
import { Button } from "../components/ux4g/Button";
import { Card, CardBody } from "../components/ux4g/Card";
import { Badge } from "../components/ux4g/Badge";
import { Icon } from "../components/ux4g/Icon";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { APAAR_EXPLAINER, PRODUCT_NAME, TAGLINE } from "../brand";

export function HomePage() {
  useDocumentTitle("National Student Registry & Verification Portal");
  const navigate = useNavigate();
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
    <div className="space-y-12 py-4">
      {/* Hero Section */}
      <section className="text-center max-w-4xl mx-auto space-y-4 pt-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border ux4g-border-neutral-subtle ux4g-bg-neutral-soft text-xs font-semibold tracking-wide">
          <Icon name="verified_user" size="xs" color="primary" aria-hidden="true" />
          <span className="ux4g-text-neutral-secondary">AICTE Smart India Hackathon 2026 Initiative</span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold ux4g-text-neutral-primary tracking-tight leading-tight">
          {PRODUCT_NAME}: <br className="hidden sm:inline" />
          <span className="ux4g-text-brand-primary">{TAGLINE}</span>
        </h1>
        <p className="text-base sm:text-lg ux4g-text-neutral-secondary max-w-2xl mx-auto leading-relaxed">
          National platform for AICTE-approved institutions to upload APAAR-keyed student data,
          automatically detect over-admissions &amp; duplicate enrolments, and offer privacy-first cryptographic verification.
        </p>
        <div className="text-xs sm:text-sm ux4g-text-neutral-primary max-w-2xl mx-auto p-4 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft leading-relaxed text-left flex items-start gap-3">
          <Icon name="info" size="sm" color="primary" className="shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <strong className="ux4g-text-neutral-primary">What is an APAAR ID?</strong>{" "}
            <span className="ux4g-text-neutral-secondary">{APAAR_EXPLAINER}</span>
          </div>
        </div>
      </section>

      {/* The Four Entry Cards (SPEC Section 1 & Section 19) */}
      <section aria-labelledby="entry-portals-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <h2 id="entry-portals-heading" className="text-xl font-bold ux4g-text-neutral-primary">
            System Entry Portals
          </h2>
          <span className="text-xs ux4g-text-neutral-secondary font-medium">Select your portal to continue</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1: Activate College */}
          <Card variant="outline" className="flex flex-col justify-between hover:border-current transition-all">
            <CardBody className="space-y-3 p-6 flex flex-col justify-between h-full">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center border ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
                  <Icon name="domain_add" size="lg" color="primary" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-bold ux4g-text-neutral-primary">Activate College</h3>
                <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
                  Claim your institution with verified AICTE master records, OTP verification to official contacts, and authorization letter upload.
                </p>
              </div>
              <div className="pt-6">
                <Button
                  variant="outline"
                  size="s"
                  fullWidth
                  onClick={() => navigate("/activate")}
                  rightIcon={<Icon name="arrow_forward" size="xs" color="inherit" aria-hidden="true" />}
                >
                  Begin activation
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Card 2: College Login */}
          <Card variant="outline" className="flex flex-col justify-between hover:border-current transition-all">
            <CardBody className="space-y-3 p-6 flex flex-col justify-between h-full">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center border ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
                  <Icon name="lock" size="lg" color="primary" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-bold ux4g-text-neutral-primary">College Login</h3>
                <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
                  Declare approved course seat allocations, upload student records via CSV/API, resolve validation flags, and submit data.
                </p>
              </div>
              <div className="pt-6">
                <Button
                  variant="primary"
                  size="s"
                  fullWidth
                  onClick={() => navigate("/login/college")}
                  rightIcon={<Icon name="arrow_forward" size="xs" color="inherit" aria-hidden="true" />}
                >
                  Sign in as college
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Card 3: AICTE Login */}
          <Card variant="outline" className="flex flex-col justify-between hover:border-current transition-all">
            <CardBody className="space-y-3 p-6 flex flex-col justify-between h-full">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center border ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
                  <Icon name="shield" size="lg" color="primary" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-bold ux4g-text-neutral-primary">AICTE Login</h3>
                <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
                  Monitor live intake compliance, resolve duplicate enrolment alerts, inspect ML anomaly clusters, and review submissions.
                </p>
              </div>
              <div className="pt-6">
                <Button
                  variant="tonal-primary"
                  size="s"
                  fullWidth
                  onClick={() => navigate("/login/aicte")}
                  rightIcon={<Icon name="arrow_forward" size="xs" color="inherit" aria-hidden="true" />}
                >
                  Sign in to AICTE
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Card 4: Verify Student Record */}
          <Card variant="outline" className="flex flex-col justify-between hover:border-current transition-all">
            <CardBody className="space-y-3 p-6 flex flex-col justify-between h-full">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center border ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
                  <Icon name="search" size="lg" color="primary" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-bold ux4g-text-neutral-primary">Verify Record</h3>
                <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
                  Authorized employers and regulators verify student credentials via cryptographic Ed25519 signature and student consent.
                </p>
              </div>
              <div className="pt-6">
                <Button
                  variant="outline"
                  size="s"
                  fullWidth
                  onClick={() => navigate("/verify")}
                  rightIcon={<Icon name="arrow_forward" size="xs" color="inherit" aria-hidden="true" />}
                >
                  Verify credential
                </Button>
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Small link to student portal (REBRAND_TASKS R06) */}
        <div className="p-4 rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-soft flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <Icon name="account_circle" size="md" color="primary" aria-hidden="true" />
            <span className="ux4g-text-neutral-secondary">
              Are you an enrolled student? Access your credentials, check which colleges hold your records, and manage third-party verification requests.
            </span>
          </div>
          <Link to="/student" className="shrink-0 font-semibold ux4g-text-brand-primary hover:underline flex items-center gap-1">
            <span>Student Consent Portal</span>
            <Icon name="open_in_new" size="xs" color="inherit" aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* How it Works - 4 Steps (SPEC §1 & REBRAND_TASKS R06) */}
      <section aria-labelledby="how-it-works-heading" className="space-y-4">
        <div className="space-y-1">
          <h2 id="how-it-works-heading" className="text-xl font-bold ux4g-text-neutral-primary">
            How EduTrace Works
          </h2>
          <p className="text-xs ux4g-text-neutral-secondary">
            End-to-end statutory validation and verification workflow in four secure steps.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated space-y-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ux4g-bg-primary-soft ux4g-text-brand-primary">
              1
            </div>
            <h3 className="text-sm font-bold ux4g-text-neutral-primary">Institution Activation</h3>
            <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
              Colleges claim their profile using on-file AICTE master records, OTP verification to official contacts, and authorization letters.
            </p>
          </div>

          <div className="p-4 rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated space-y-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ux4g-bg-primary-soft ux4g-text-brand-primary">
              2
            </div>
            <h3 className="text-sm font-bold ux4g-text-neutral-primary">Student Data Upload</h3>
            <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
              Institutions declare course seat quotas and upload student enrollment records keyed by the national 12-digit APAAR ID via CSV or API.
            </p>
          </div>

          <div className="p-4 rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated space-y-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ux4g-bg-primary-soft ux4g-text-brand-primary">
              3
            </div>
            <h3 className="text-sm font-bold ux4g-text-neutral-primary">Automated Validation</h3>
            <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
              Deterministic validation engine detects formatting errors, over-admissions against approved intake, and cross-college duplicate enrollments.
            </p>
          </div>

          <div className="p-4 rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated space-y-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ux4g-bg-primary-soft ux4g-text-brand-primary">
              4
            </div>
            <h3 className="text-sm font-bold ux4g-text-neutral-primary">Central Repository &amp; Verification</h3>
            <p className="text-xs ux4g-text-neutral-secondary leading-relaxed">
              Approved records receive tamper-proof Ed25519 digital signatures, QR codes, and are verifiable by employers with DPDP student consent.
            </p>
          </div>
        </div>
      </section>

      {/* Live System Connectivity & Architecture Stats */}
      <section aria-labelledby="architecture-status-heading" className="rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b ux4g-border-neutral-subtle pb-3">
          <div>
            <h3 id="architecture-status-heading" className="text-base font-bold ux4g-text-neutral-primary flex items-center gap-2">
              <Icon name="dns" size="sm" color="primary" aria-hidden="true" />
              System Architecture &amp; Health Status
            </h3>
            <p className="text-xs ux4g-text-neutral-secondary">Live connectivity check with backend engine and persistence layers</p>
          </div>
          {loadingHealth ? (
            <span className="text-xs ux4g-text-neutral-secondary">Pinging backend...</span>
          ) : health ? (
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full ux4g-bg-success" />
              <span className="text-xs font-semibold ux4g-text-success uppercase" data-testid="overall-status">
                {health.status}
              </span>
              <span className="text-xs ux4g-text-neutral-secondary font-mono">v{health.version}</span>
            </div>
          ) : (
            <span className="text-xs ux4g-text-error font-medium">Backend unreachable</span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div className="p-4 rounded-lg ux4g-bg-neutral-soft border ux4g-border-neutral-subtle flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold ux4g-text-neutral-secondary uppercase tracking-wider">Relational Store</p>
              <p className="text-sm font-bold ux4g-text-neutral-primary">PostgreSQL 16</p>
              <p className="text-xs ux4g-text-neutral-secondary">26 tables &amp; hash-chain audit</p>
            </div>
            <span
              className={`px-2.5 py-1 rounded text-xs font-semibold ${
                health?.services?.database === "connected" ? "ux4g-bg-success-soft ux4g-text-success" : "ux4g-bg-neutral-subtle ux4g-text-neutral-primary"
              }`}
              data-testid="db-status"
            >
              {health?.services?.database || "Checking..."}
            </span>
          </div>

          <div className="p-4 rounded-lg ux4g-bg-neutral-soft border ux4g-border-neutral-subtle flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold ux4g-text-neutral-secondary uppercase tracking-wider">Fast Cache &amp; Rate Limit</p>
              <p className="text-sm font-bold ux4g-text-neutral-primary">Redis 7</p>
              <p className="text-xs ux4g-text-neutral-secondary">Sliding window &amp; OTP storage</p>
            </div>
            <span
              className={`px-2.5 py-1 rounded text-xs font-semibold ${
                health?.services?.redis === "connected" ? "ux4g-bg-success-soft ux4g-text-success" : "ux4g-bg-neutral-subtle ux4g-text-neutral-primary"
              }`}
              data-testid="redis-status"
            >
              {health?.services?.redis || "Checking..."}
            </span>
          </div>

          <div className="p-4 rounded-lg ux4g-bg-neutral-soft border ux4g-border-neutral-subtle flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold ux4g-text-neutral-secondary uppercase tracking-wider">Validation Engine</p>
              <p className="text-sm font-bold ux4g-text-neutral-primary">Deterministic Engine</p>
              <p className="text-xs ux4g-text-neutral-secondary">Pure rule functions &amp; RapidFuzz</p>
            </div>
            <span className="px-2.5 py-1 rounded text-xs font-semibold ux4g-bg-primary-soft ux4g-text-brand-primary">
              Ready
            </span>
          </div>
        </div>
      </section>

      {/* Demo Accounts Quick-Fill Guide */}
      <section aria-labelledby="demo-accounts-heading" className="rounded-xl border ux4g-border-neutral-subtle ux4g-bg-neutral-elevated p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b ux4g-border-neutral-subtle pb-3">
          <div>
            <h3 id="demo-accounts-heading" className="text-base font-bold ux4g-text-neutral-primary flex items-center gap-2">
              <Icon name="badge" size="sm" color="primary" aria-hidden="true" />
              Evaluation Demo Accounts (SIH 2026)
            </h3>
            <p className="text-xs ux4g-text-neutral-secondary">
              Pre-seeded institutional and officer accounts. Standard password:{" "}
              <code className="ux4g-bg-neutral-soft px-1.5 py-0.5 rounded font-mono text-xs border ux4g-border-neutral-subtle">
                Demo@12345
              </code>
            </p>
          </div>
          <Badge variant="primary">Demo Mode Active</Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="p-3 ux4g-bg-neutral-soft rounded-lg border ux4g-border-neutral-subtle space-y-1">
            <p className="font-semibold ux4g-text-neutral-primary">AICTE Central Admin</p>
            <p className="font-mono text-[11px] ux4g-text-neutral-secondary truncate">aicte_admin@aicte-india.org</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">System admin &amp; audit log</p>
            <Link to="/login/aicte" className="inline-flex items-center ux4g-text-brand-primary hover:underline pt-1 text-[11px] font-semibold">
              Use account <Icon name="arrow_forward" size="xs" color="inherit" className="ml-1" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-3 ux4g-bg-neutral-soft rounded-lg border ux4g-border-neutral-subtle space-y-1">
            <p className="font-semibold ux4g-text-neutral-primary">AICTE Compliance Officer</p>
            <p className="font-mono text-[11px] ux4g-text-neutral-secondary truncate">aicte_officer@aicte-india.org</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">Review queue &amp; intake monitor</p>
            <Link to="/login/aicte" className="inline-flex items-center ux4g-text-brand-primary hover:underline pt-1 text-[11px] font-semibold">
              Use account <Icon name="arrow_forward" size="xs" color="inherit" className="ml-1" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-3 ux4g-bg-neutral-soft rounded-lg border ux4g-border-neutral-subtle space-y-1">
            <p className="font-semibold ux4g-text-neutral-primary">College Admin (Stage 1)</p>
            <p className="font-mono text-[11px] ux4g-text-neutral-secondary truncate">admin@piaet-pune.edu.in</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">Pune Inst. of Adv. Engg &amp; Tech</p>
            <Link to="/login/college" className="inline-flex items-center ux4g-text-brand-primary hover:underline pt-1 text-[11px] font-semibold">
              Use account <Icon name="arrow_forward" size="xs" color="inherit" className="ml-1" aria-hidden="true" />
            </Link>
          </div>

          <div className="p-3 ux4g-bg-neutral-soft rounded-lg border ux4g-border-neutral-subtle space-y-1">
            <p className="font-semibold ux4g-text-neutral-primary">Student Consent Portal</p>
            <p className="font-mono text-[11px] ux4g-text-neutral-secondary truncate">APAAR: 111122223333</p>
            <p className="text-[11px] ux4g-text-neutral-secondary">Aarav Sharma (consent history)</p>
            <Link to="/student" className="inline-flex items-center ux4g-text-brand-primary hover:underline pt-1 text-[11px] font-semibold">
              Open portal <Icon name="open_in_new" size="xs" color="inherit" className="ml-1" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

