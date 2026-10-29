import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";
import { RoleBadge } from "../components/ui/Badge";
import { ShieldAlert } from "lucide-react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function UnauthorizedPage() {
  useDocumentTitle("403 Access Restricted");
  const { user, logout } = useAuth();
  const location = useLocation();
  const attemptedPath = (location.state as { attemptedPath?: string })?.attemptedPath;

  const dashboardPath =
    user?.role === "aicte_admin" || user?.role === "aicte_officer"
      ? "/aicte/overview"
      : user?.role === "verifier"
      ? "/verifier/search"
      : "/college/dashboard";

  return (
    <div className="max-w-lg mx-auto py-12 text-center space-y-6">
      <div className="w-16 h-16 rounded-2xl bg-red-100 text-red-700 mx-auto flex items-center justify-center shadow-sm">
        <ShieldAlert className="w-8 h-8" />
      </div>

      <div className="space-y-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-red-600 font-mono">
          HTTP 403 Forbidden
        </span>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Access Restricted</h1>
        <p className="text-sm text-slate-600 max-w-sm mx-auto">
          Your current account role does not have authorization to view this section of the portal.
        </p>
      </div>

      {user && (
        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-left max-w-sm mx-auto space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Current Role:</span>
            <RoleBadge role={user.role} />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Account:</span>
            <span className="font-mono text-slate-700 truncate max-w-[180px]">{user.email}</span>
          </div>
          {attemptedPath && (
            <div className="flex justify-between items-center">
              <span className="text-slate-500">Requested:</span>
              <span className="font-mono text-slate-700 truncate max-w-[180px]">{attemptedPath}</span>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        <Link to={dashboardPath}>
          <Button variant="primary">Go to your dashboard</Button>
        </Link>
        <Link to="/">
          <Button variant="outline">Return to home</Button>
        </Link>
        <Button variant="ghost" onClick={logout} className="text-red-600 hover:text-red-700 hover:bg-red-50">
          Sign out
        </Button>
      </div>
    </div>
  );
}
