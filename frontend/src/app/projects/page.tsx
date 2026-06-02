import Link from "next/link";
import { Zap, FolderOpen } from "lucide-react";

export default function ProjectsPage() {
  return (
    <div className="min-h-screen bg-slate-900">
      <header className="border-b border-white/10">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Zap className="h-6 w-6 text-emerald-400" />
              <span className="font-bold text-white">Moz</span>
            </Link>
            <span className="text-slate-500">/</span>
            <span className="text-sm text-slate-300">Projects</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/analyze" className="text-sm text-slate-400 hover:text-white transition">
              New Analysis
            </Link>
            <Link href="/projects" className="text-sm text-white font-medium">
              Projects
            </Link>
            <Link href="/opportunities" className="text-sm text-slate-400 hover:text-white transition">
              Opportunities
            </Link>
            <Link href="/portfolios" className="text-sm text-slate-400 hover:text-white transition">
              Portfolios
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <FolderOpen className="h-12 w-12 text-slate-600 mb-4" />
          <h2 className="text-xl font-semibold text-white">No projects yet</h2>
          <p className="mt-2 text-sm text-slate-400 max-w-md">
            Start a new analysis to generate your first prefeasibility study.
            Projects will be saved here for future reference.
          </p>
          <Link
            href="/analyze"
            className="mt-6 rounded-lg bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 transition"
          >
            Start New Analysis
          </Link>
        </div>
      </main>
    </div>
  );
}
