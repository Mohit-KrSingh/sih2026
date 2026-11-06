import React from "react";
import { PRODUCT_NAME } from "../../brand";

interface EduTraceLogoProps {
  className?: string;
  iconOnly?: boolean;
  size?: number;
}

export const EduTraceIcon: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className = "",
}) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
    <path d="M2 17h4l2.5-4 3 7 3-5 2.5 2H22" />
  </svg>
);

export const EduTraceLogo: React.FC<EduTraceLogoProps> = ({
  className = "",
  iconOnly = false,
  size = 24,
}) => {
  if (iconOnly) {
    return <EduTraceIcon size={size} className={className} />;
  }

  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`.trim()}>
      <div className="w-8 h-8 rounded-lg ux4g-bg-primary-strong flex items-center justify-center shadow-sm shrink-0">
        <EduTraceIcon size={18} className="ux4g-text-neutral-inverse" />
      </div>
      <div className="leading-tight">
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg tracking-tight ux4g-text-neutral-primary">{PRODUCT_NAME}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium ux4g-bg-primary-soft ux4g-text-brand-primary border ux4g-border-neutral-subtle">
            Central Portal
          </span>
        </div>
      </div>
    </div>
  );
};
