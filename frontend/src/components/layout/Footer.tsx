import { Link } from "react-router-dom";
import { PRODUCT_NAME } from "../../brand";

export function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400 text-xs border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3 text-slate-300">
            <span className="font-semibold text-white">{PRODUCT_NAME} Verification Engine</span>
            <span>&bull;</span>
            <span>All India Council for Technical Education (AICTE)</span>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              to="/privacy"
              className="text-slate-300 hover:text-white hover:underline transition font-medium text-[11px]"
            >
              DPDP Privacy Policy
            </Link>
            <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-medium">
              Demo mode: APAAR registry is simulated
            </span>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 gap-2">
          <p>
            Designed in accordance with Digital Personal Data Protection (DPDP) principles: purpose
            limitation, data minimisation, and consent-gated verification.{" "}
            <Link to="/privacy" className="text-blue-400 hover:text-blue-300 underline ml-1">
              Read Charter
            </Link>
          </p>
          <p className="shrink-0">Smart India Hackathon 2026</p>
        </div>
      </div>
    </footer>
  );
}
