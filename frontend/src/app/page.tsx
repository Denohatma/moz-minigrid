import Link from "next/link";
import { MapPin, FileBarChart, Zap, Download } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900">
      <header className="border-b border-white/10">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap className="h-8 w-8 text-emerald-400" />
            <span className="text-xl font-bold text-white">Moz</span>
          </div>
          <nav className="flex items-center gap-6">
            <Link
              href="/analyze"
              className="text-sm text-slate-300 hover:text-white transition"
            >
              New Analysis
            </Link>
            <Link
              href="/projects"
              className="text-sm text-slate-300 hover:text-white transition"
            >
              Projects
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-24">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-white tracking-tight">
            Mini-Grid Prefeasibility
            <br />
            <span className="text-emerald-400">for Mozambique</span>
          </h1>
          <p className="mt-6 text-lg text-slate-300 max-w-2xl mx-auto">
            Generate investment-grade prefeasibility studies for solar + battery
            mini-grid sites from GPS coordinates. Powered by geospatial data and
            financial modeling.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/analyze"
              className="rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:bg-emerald-400 transition"
            >
              Start New Analysis
            </Link>
            <Link
              href="/analyze?mode=batch"
              className="rounded-lg bg-white/10 px-6 py-3 text-sm font-semibold text-white hover:bg-white/20 transition"
            >
              Batch Upload
            </Link>
          </div>
        </div>

        <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard
            icon={<MapPin className="h-6 w-6 text-emerald-400" />}
            title="Drop a Pin"
            description="Click on the map or enter GPS coordinates. The system auto-detects the settlement, extracts solar resource, population, and grid proximity data."
          />
          <FeatureCard
            icon={<FileBarChart className="h-6 w-6 text-emerald-400" />}
            title="Full Financial Model"
            description="LCOE, IRR, NPV, tariff affordability, and subsidy gap analysis. Sensitivity analysis across 6 key parameters."
          />
          <FeatureCard
            icon={<Download className="h-6 w-6 text-emerald-400" />}
            title="Investment-Grade Reports"
            description="Download professional PDF reports and editable Excel financial models ready for investment committee review."
          />
        </div>
      </main>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl bg-white/5 border border-white/10 p-6">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm text-slate-400">{description}</p>
    </div>
  );
}
