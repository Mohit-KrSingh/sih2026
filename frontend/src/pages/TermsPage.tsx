import React from "react";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PRODUCT_NAME, DEMO_MODE_NOTICE } from "../brand";

/**
 * Terms of Service Page
 */
export const TermsPage: React.FC = () => {
  useDocumentTitle("Terms of Service");

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      <header className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ux4g-bg-neutral-subtle ux4g-text-neutral-secondary border ux4g-border-neutral-subtle">
          <span>Operational Guidelines & Prototype Terms</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight leading-tight ux4g-text-neutral-primary">
          Terms of Service
        </h1>
        <p className="text-base leading-relaxed ux4g-text-neutral-secondary">
          Guidelines and conditions governing the use of the {PRODUCT_NAME} demonstration platform.
        </p>
      </header>

      <section className="p-4 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft space-y-2">
        <h2 className="text-base font-bold ux4g-text-neutral-primary">Demo Status Notice</h2>
        <p className="text-sm ux4g-text-neutral-secondary leading-relaxed">
          {DEMO_MODE_NOTICE} All data processed on this instance consists of simulated test records generated for evaluation purposes. No actual Aadhaar, identity, or academic records are collected or stored.
        </p>
      </section>

      <section className="space-y-4 text-sm leading-relaxed ux4g-text-neutral-secondary">
        <h2 className="text-lg font-bold ux4g-text-neutral-primary">1. Permitted Purpose</h2>
        <p>
          The {PRODUCT_NAME} platform is designed to demonstrate end-to-end institutional student data submission, rule-based compliance verification against approved AICTE intake, and authorized student consent-driven verification under the Smart India Hackathon initiative.
        </p>

        <h2 className="text-lg font-bold ux4g-text-neutral-primary">2. Data Ownership and Integrity</h2>
        <p>
          Institutions are solely responsible for ensuring the accuracy of student admission counts and seat declarations. Approved intake limits, course approvals, and official contact records remain under the strict regulatory ownership of AICTE and cannot be modified without formal approval.
        </p>

        <h2 className="text-lg font-bold ux4g-text-neutral-primary">3. Verification and Consent Governance</h2>
        <p>
          Third-party verifiers may only query academic credentials following explicit, scoped, time-bound consent granted by the registered student. Academic identity queries are cryptographically logged to an immutable hash chain.
        </p>

        <div className="pt-4 border-t ux4g-border-neutral-subtle">
          <Link to="/privacy" className="font-semibold underline hover:ux4g-text-brand-primary">
            View our DPDP Privacy Charter &rarr;
          </Link>
        </div>
      </section>
    </div>
  );
};
