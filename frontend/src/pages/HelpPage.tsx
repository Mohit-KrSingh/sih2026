import React from "react";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PRODUCT_NAME, APAAR_EXPLAINER } from "../brand";

/**
 * Help & Glossary Page
 */
export const HelpPage: React.FC = () => {
  useDocumentTitle("Help & Glossary");

  const terms = [
    {
      term: "APAAR ID",
      definition: APAAR_EXPLAINER,
    },
    {
      term: "Approved Intake",
      definition:
        "The statutory maximum ceiling of regular student enrolments sanctioned by AICTE for a given course and academic year. Over-admission beyond this threshold triggers regulatory review.",
    },
    {
      term: "Supernumerary Seats",
      definition:
        "Special quota seats (e.g. Tuition Fee Waiver, J&K quota, PMSSS, NRI/OCI, Foreign National) permitted above the approved intake with formal sanction. Counted separately from regular admissions.",
    },
    {
      term: "Validation Exception",
      definition:
        "A compliance finding that requires a formal written justification and supporting document from the institution before final submission can be accepted by AICTE.",
    },
    {
      term: "Consent-Gated Verification",
      definition:
        "A secure protocol where third-party employers or verification agencies cannot view student academic credentials without active, cryptographic consent authorized by the student via OTP.",
    },
    {
      term: "Hash-Chained Audit Log",
      definition:
        "An immutable, append-only cryptographic ledger where each administrative state transition and verifier access record is hashed with the SHA-256 hash of the preceding entry.",
    },
  ];

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      <header className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ux4g-bg-neutral-subtle ux4g-text-neutral-secondary border ux4g-border-neutral-subtle">
          <span>System Terminology & User Guidance</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight leading-tight ux4g-text-neutral-primary">
          Help & Glossary
        </h1>
        <p className="text-base leading-relaxed ux4g-text-neutral-secondary">
          Clear definitions of key regulatory, technical, and domain concepts utilized across {PRODUCT_NAME}.
        </p>
      </header>

      <section className="space-y-6">
        <h2 className="text-xl font-bold ux4g-text-neutral-primary">Regulatory & Academic Terms</h2>
        <dl className="space-y-4">
          {terms.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-lg border ux4g-border-neutral-subtle ux4g-bg-neutral-soft space-y-1"
            >
              <dt className="text-base font-bold ux4g-text-neutral-primary">{item.term}</dt>
              <dd className="text-sm leading-relaxed ux4g-text-neutral-secondary">{item.definition}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="pt-4 border-t ux4g-border-neutral-subtle flex items-center justify-between text-sm">
        <Link to="/" className="font-semibold underline hover:ux4g-text-brand-primary">
          &larr; Return to Home
        </Link>
        <Link to="/privacy" className="font-semibold underline hover:ux4g-text-brand-primary">
          Read DPDP Privacy Charter &rarr;
        </Link>
      </div>
    </div>
  );
};
