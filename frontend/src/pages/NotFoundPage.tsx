import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { FileQuestion } from "lucide-react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function NotFoundPage() {
  useDocumentTitle("404 Page Not Found");
  return (
    <div className="max-w-md mx-auto py-16 text-center space-y-6">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 text-slate-500 mx-auto flex items-center justify-center">
        <FileQuestion className="w-8 h-8" />
      </div>

      <div className="space-y-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
          HTTP 404 Not Found
        </span>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Page Not Found</h1>
        <p className="text-sm text-slate-600">
          The requested address does not exist or may have been moved.
        </p>
      </div>

      <div>
        <Link to="/">
          <Button variant="primary">Return to home</Button>
        </Link>
      </div>
    </div>
  );
}
