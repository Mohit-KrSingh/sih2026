import { useEffect, useState } from "react";

interface HealthData {
  status: string;
  timestamp: string;
  version: string;
  services: {
    database: string;
    redis: string;
  };
  demo_mode: boolean;
}

export function App() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiBase = (import.meta.env.VITE_API_BASE_URL as string) || "";

  useEffect(() => {
    fetch(`${apiBase}/api/v1/health`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Health check returned status ${res.status}`);
        }
        return res.json();
      })
      .then((data: HealthData) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [apiBase]);

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50 text-slate-900">
      <header className="bg-blue-900 text-white shadow-md">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-amber-500 rounded flex items-center justify-center font-bold text-blue-950 text-xl">
              A
            </div>
            <div>
              <h1 className="text-xl font-bold leading-none">APAAR</h1>
              <p className="text-xs text-blue-200">
                AICTE Student Data Management and Verification System
              </p>
            </div>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-blue-800 text-amber-300 border border-blue-700 font-medium">
            Smart India Hackathon 2026
          </span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 flex-1 w-full space-y-8">
        <section className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">System Service Connectivity</h2>
          {loading && <p className="text-sm text-slate-500">Checking API health status...</p>}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              Backend unreachable: {error}
            </div>
          )}
          {health && (
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <span className="text-sm font-medium text-slate-600">Overall Status:</span>
                <span
                  className={`px-2.5 py-0.5 rounded text-xs font-semibold uppercase ${
                    health.status === "healthy"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-amber-100 text-amber-800 border border-amber-300"
                  }`}
                  data-testid="overall-status"
                >
                  {health.status}
                </span>
                <span className="text-xs text-slate-400">v{health.version}</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded border border-slate-200 bg-slate-50 flex justify-between items-center">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide">PostgreSQL 16</p>
                    <p className="text-sm font-medium text-slate-800">Database Engine</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      health.services.database === "connected"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-rose-100 text-rose-700"
                    }`}
                    data-testid="db-status"
                  >
                    {health.services.database}
                  </span>
                </div>

                <div className="p-4 rounded border border-slate-200 bg-slate-50 flex justify-between items-center">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Redis 7</p>
                    <p className="text-sm font-medium text-slate-800">Cache & Rate Limits</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      health.services.redis === "connected"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-rose-100 text-rose-700"
                    }`}
                    data-testid="redis-status"
                  >
                    {health.services.redis}
                  </span>
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-800">System Entry Portals</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-5 bg-white border border-slate-200 rounded-lg shadow-sm hover:border-blue-400 transition">
              <h3 className="font-semibold text-slate-900">Activate College</h3>
              <p className="text-xs text-slate-500 mt-1">Claim AICTE ID with verified contacts</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-lg shadow-sm hover:border-blue-400 transition">
              <h3 className="font-semibold text-slate-900">College Login</h3>
              <p className="text-xs text-slate-500 mt-1">Upload records & declare course seats</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-lg shadow-sm hover:border-blue-400 transition">
              <h3 className="font-semibold text-slate-900">AICTE Login</h3>
              <p className="text-xs text-slate-500 mt-1">Monitor compliance, over-intake & anomalies</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-lg shadow-sm hover:border-blue-400 transition">
              <h3 className="font-semibold text-slate-900">Verify Record</h3>
              <p className="text-xs text-slate-500 mt-1">Authorized check with student consent</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-slate-100 border-t border-slate-200 py-3 text-center text-xs text-slate-600">
        <span>Demo mode: APAAR registry is simulated &bull; SIH 2026 AICTE Platform</span>
      </footer>
    </div>
  );
}

export default App;
