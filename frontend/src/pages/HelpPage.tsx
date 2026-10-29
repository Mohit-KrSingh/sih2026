import React from "react";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { en } from "../copy/en";

/**
 * Help and glossary page
 */
export const HelpPage: React.FC = () => {
  useDocumentTitle(en.help.title);

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      <header className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ux4g-bg-neutral-subtle ux4g-text-neutral-secondary border ux4g-border-neutral-subtle">
          <span>System terminology and user guidance</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight leading-tight ux4g-text-neutral-primary">
          {en.help.title}
        </h1>
        <p className="text-base leading-relaxed ux4g-text-neutral-secondary">
          {en.help.subtitle}
        </p>
      </header>

      <section className="space-y-6">
        <h2 className="text-xl font-bold ux4g-text-neutral-primary">{en.help.regulatoryHeading}</h2>
        <dl className="space-y-4">
          {en.help.terms.map((item, idx) => (
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
          &larr; Return to home
        </Link>
        <Link to="/privacy" className="font-semibold underline hover:ux4g-text-brand-primary">
          Read DPDP privacy charter &rarr;
        </Link>
      </div>
    </div>
  );
};
