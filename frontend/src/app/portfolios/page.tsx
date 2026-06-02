"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Zap,
  Briefcase,
  Loader2,
  X,
  Users,
  BarChart3,
  ArrowLeft,
  Plus,
  Eye,
  Check,
  Star,
  Clock,
  FileText,
  Trash2,
} from "lucide-react";
import {
  fetchPortfolios,
  fetchPortfolio,
  fetchSubmissions,
  createSubmission,
  updateSubmission,
  deletePortfolio,
} from "@/lib/api";
import type {
  PortfolioSummary,
  Portfolio,
  Submission,
  Opportunity,
} from "@/lib/api";

const PORTFOLIO_STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  published: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  under_review: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  awarded: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  closed: "bg-red-500/20 text-red-300 border-red-500/30",
};

const SUBMISSION_STATUS_COLORS: Record<string, string> = {
  pending: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  under_review: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  shortlisted: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  accepted: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  rejected: "bg-red-500/20 text-red-300 border-red-500/30",
};

function formatUSD(val?: number) {
  if (val == null) return "—";
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
  return `$${val.toFixed(0)}`;
}

export default function PortfoliosPage() {
  const [view, setView] = useState<"list" | "detail">("list");
  const [portfoliosList, setPortfoliosList] = useState<PortfolioSummary[]>([]);
  const [activePortfolio, setActivePortfolio] = useState<Portfolio | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddSubmission, setShowAddSubmission] = useState(false);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchPortfolios();
      setPortfoliosList(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const openPortfolio = async (id: string) => {
    setLoading(true);
    try {
      const [port, subs] = await Promise.all([
        fetchPortfolio(id),
        fetchSubmissions(id),
      ]);
      setActivePortfolio(port);
      setSubmissions(subs);
      setView("detail");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (subId: string, newStatus: string) => {
    if (!activePortfolio) return;
    try {
      const updated = await updateSubmission(activePortfolio.id, subId, {
        status: newStatus as any,
      });
      setSubmissions((prev) =>
        prev.map((s) => (s.id === subId ? updated : s))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update");
    }
  };

  const handleDeletePortfolio = async (id: string) => {
    try {
      await deletePortfolio(id);
      setPortfoliosList((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  return (
    <div className="min-h-screen bg-afcen-navy">
      {/* Header */}
      <header className="border-b border-white/10 sticky top-0 z-40 bg-afcen-navy/95 backdrop-blur">
        <div className="mx-auto max-w-[1600px] px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Zap className="h-6 w-6 text-emerald-400" />
              <span className="font-bold text-white">Moz</span>
            </Link>
            <span className="text-slate-600">/</span>
            {view === "detail" && activePortfolio ? (
              <>
                <button
                  onClick={() => { setView("list"); setActivePortfolio(null); }}
                  className="text-sm text-slate-400 hover:text-white transition"
                >
                  Portfolios
                </button>
                <span className="text-slate-600">/</span>
                <span className="text-sm text-white">{activePortfolio.name}</span>
              </>
            ) : (
              <span className="text-sm text-slate-300">Portfolios</span>
            )}
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/analyze" className="text-sm text-slate-400 hover:text-white transition">
              New Analysis
            </Link>
            <Link href="/projects" className="text-sm text-slate-400 hover:text-white transition">
              Projects
            </Link>
            <Link href="/opportunities" className="text-sm text-slate-400 hover:text-white transition">
              Opportunities
            </Link>
            <Link href="/portfolios" className="text-sm text-white font-medium">
              Portfolios
            </Link>
          </nav>
        </div>
      </header>

      {error && (
        <div className="mx-auto max-w-[1600px] px-6 mt-4">
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
            {error}
            <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {loading && view === "list" ? (
          <div className="flex flex-col items-center py-24">
            <Loader2 className="h-6 w-6 text-emerald-400 animate-spin mb-2" />
            <span className="text-slate-400 text-sm">Loading portfolios...</span>
          </div>
        ) : view === "list" ? (
          <PortfolioList
            portfolios={portfoliosList}
            onOpen={openPortfolio}
            onDelete={handleDeletePortfolio}
          />
        ) : activePortfolio ? (
          <PortfolioDetail
            portfolio={activePortfolio}
            submissions={submissions}
            onBack={() => { setView("list"); setActivePortfolio(null); loadList(); }}
            onStatusChange={handleStatusChange}
            onAddSubmission={() => setShowAddSubmission(true)}
            onSubmissionAdded={(sub) => setSubmissions((prev) => [sub, ...prev])}
            showAddSubmission={showAddSubmission}
            onCloseAddSubmission={() => setShowAddSubmission(false)}
          />
        ) : null}
      </main>
    </div>
  );
}

// ── Portfolio List View ────────────────────────────────────────

function PortfolioList({
  portfolios,
  onOpen,
  onDelete,
}: {
  portfolios: PortfolioSummary[];
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  if (portfolios.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Briefcase className="h-12 w-12 text-slate-600 mb-4" />
        <h2 className="text-xl font-semibold text-white">No portfolios yet</h2>
        <p className="mt-2 text-sm text-slate-400 max-w-md">
          Select opportunities from the pipeline and send them to a portfolio to start
          receiving bidder submissions.
        </p>
        <Link
          href="/opportunities"
          className="mt-6 rounded-lg bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 transition"
        >
          Go to Opportunities
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {portfolios.map((p) => (
        <div
          key={p.id}
          className="rounded-xl border border-white/10 bg-white/3 hover:bg-white/5 transition cursor-pointer group"
        >
          <div className="p-5" onClick={() => onOpen(p.id)}>
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-white font-semibold text-base group-hover:text-emerald-300 transition">
                {p.name}
              </h3>
              <span
                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${
                  PORTFOLIO_STATUS_COLORS[p.status] || ""
                }`}
              >
                {p.status.replace("_", " ")}
              </span>
            </div>
            {p.description && (
              <p className="text-sm text-slate-400 mb-4 line-clamp-2">{p.description}</p>
            )}
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <FileText className="h-3.5 w-3.5" />
                {p.opportunity_count} project{p.opportunity_count !== 1 ? "s" : ""}
              </span>
              <span className="flex items-center gap-1">
                <Users className="h-3.5 w-3.5" />
                {p.submission_count} submission{p.submission_count !== 1 ? "s" : ""}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {new Date(p.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
          <div className="border-t border-white/5 px-5 py-2.5 flex items-center justify-between">
            <button
              onClick={() => onOpen(p.id)}
              className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition"
            >
              <Eye className="h-3.5 w-3.5" />
              View Details
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(p.id); }}
              className="text-xs text-slate-500 hover:text-red-400 flex items-center gap-1 transition"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Portfolio Detail View ──────────────────────────────────────

function PortfolioDetail({
  portfolio,
  submissions,
  onBack,
  onStatusChange,
  onAddSubmission,
  onSubmissionAdded,
  showAddSubmission,
  onCloseAddSubmission,
}: {
  portfolio: Portfolio;
  submissions: Submission[];
  onBack: () => void;
  onStatusChange: (subId: string, status: string) => void;
  onAddSubmission: () => void;
  onSubmissionAdded: (sub: Submission) => void;
  showAddSubmission: boolean;
  onCloseAddSubmission: () => void;
}) {
  const [tab, setTab] = useState<"projects" | "submissions" | "comparison">("projects");

  const totalCapex = portfolio.opportunities.reduce(
    (s, o) => s + (o.total_capex_usd || 0),
    0
  );
  const totalConnections = portfolio.opportunities.reduce(
    (s, o) => s + (o.connections_targeted || 0),
    0
  );

  return (
    <div>
      {/* Portfolio header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          All Portfolios
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{portfolio.name}</h1>
            {portfolio.description && (
              <p className="text-slate-400 mt-1">{portfolio.description}</p>
            )}
          </div>
          <span
            className={`inline-flex px-3 py-1 rounded-full text-sm font-medium border capitalize ${
              PORTFOLIO_STATUS_COLORS[portfolio.status] || ""
            }`}
          >
            {portfolio.status.replace("_", " ")}
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mt-5">
          <StatCard label="Projects" value={portfolio.opportunities.length.toString()} />
          <StatCard label="Total CAPEX" value={formatUSD(totalCapex)} />
          <StatCard label="Total Connections" value={totalConnections.toLocaleString()} />
          <StatCard label="Submissions" value={submissions.length.toString()} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-white/10 mb-6">
        {(["projects", "submissions", "comparison"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition capitalize ${
              tab === t
                ? "text-emerald-400 border-emerald-400"
                : "text-slate-400 border-transparent hover:text-white"
            }`}
          >
            {t === "comparison" ? "Bidder Comparison" : t}
          </button>
        ))}
        <div className="ml-auto">
          <button
            onClick={onAddSubmission}
            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-400 transition"
          >
            <Plus className="h-4 w-4" />
            Add Submission
          </button>
        </div>
      </div>

      {/* Tab content */}
      {tab === "projects" && (
        <ProjectsTab opportunities={portfolio.opportunities} />
      )}
      {tab === "submissions" && (
        <SubmissionsTab
          submissions={submissions}
          onStatusChange={onStatusChange}
        />
      )}
      {tab === "comparison" && (
        <ComparisonTab
          submissions={submissions}
          portfolio={portfolio}
        />
      )}

      {/* Add submission modal */}
      {showAddSubmission && (
        <AddSubmissionModal
          portfolioId={portfolio.id}
          onClose={onCloseAddSubmission}
          onCreated={(sub) => {
            onSubmissionAdded(sub);
            onCloseAddSubmission();
          }}
        />
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/3 p-4">
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}

// ── Projects Tab ───────────────────────────────────────────────

function ProjectsTab({ opportunities }: { opportunities: Opportunity[] }) {
  return (
    <div className="rounded-xl border border-white/10 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-white/5 border-b border-white/10">
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Project</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Province</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Status</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase">Connections</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase">PV (kWp)</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase">CAPEX</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase">LCOE</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase">IRR</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {opportunities.map((opp) => (
            <tr key={opp.id} className="hover:bg-white/3">
              <td className="px-4 py-2.5 text-white font-medium">{opp.project_name}</td>
              <td className="px-4 py-2.5 text-slate-300">{opp.province}</td>
              <td className="px-4 py-2.5">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${
                  opp.status === "scoped" ? "bg-blue-500/20 text-blue-300 border-blue-500/30"
                  : opp.status === "floated" ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                  : "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                }`}>
                  {opp.status}
                </span>
              </td>
              <td className="px-4 py-2.5 text-right text-slate-300 tabular-nums">
                {opp.connections_targeted?.toLocaleString() || "—"}
              </td>
              <td className="px-4 py-2.5 text-right text-slate-300 tabular-nums">
                {opp.pv_capacity_kwp?.toFixed(1) || "—"}
              </td>
              <td className="px-4 py-2.5 text-right text-white font-medium tabular-nums">
                {formatUSD(opp.total_capex_usd)}
              </td>
              <td className="px-4 py-2.5 text-right text-slate-300 tabular-nums">
                {opp.lcoe_usd_kwh != null ? `$${opp.lcoe_usd_kwh.toFixed(3)}` : "—"}
              </td>
              <td className="px-4 py-2.5 text-right text-slate-300 tabular-nums">
                {opp.irr_pct != null ? `${opp.irr_pct.toFixed(1)}%` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Submissions Tab ────────────────────────────────────────────

function SubmissionsTab({
  submissions,
  onStatusChange,
}: {
  submissions: Submission[];
  onStatusChange: (id: string, status: string) => void;
}) {
  if (submissions.length === 0) {
    return (
      <div className="flex flex-col items-center py-16 text-center">
        <Users className="h-10 w-10 text-slate-600 mb-3" />
        <p className="text-slate-400 text-sm">No submissions yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {submissions.map((sub) => (
        <div
          key={sub.id}
          className="rounded-xl border border-white/10 bg-white/3 p-5"
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <h4 className="text-white font-semibold">{sub.bidder_name}</h4>
              {sub.bidder_organization && (
                <p className="text-sm text-slate-400">{sub.bidder_organization}</p>
              )}
              {sub.contact_email && (
                <p className="text-xs text-slate-500 mt-0.5">{sub.contact_email}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${
                SUBMISSION_STATUS_COLORS[sub.status] || ""
              }`}>
                {sub.status.replace("_", " ")}
              </span>
              <select
                value={sub.status}
                onChange={(e) => onStatusChange(sub.id, e.target.value)}
                className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none"
              >
                <option value="pending">Pending</option>
                <option value="under_review">Under Review</option>
                <option value="shortlisted">Shortlisted</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 md:grid-cols-6 gap-4 text-sm">
            <MetricCell label="Proposed CAPEX" value={formatUSD(sub.proposed_capex_usd)} />
            <MetricCell label="Grant Ask" value={formatUSD(sub.proposed_grant_ask_usd)} />
            <MetricCell label="Proposed Tariff" value={sub.proposed_tariff_usd_kwh != null ? `$${sub.proposed_tariff_usd_kwh.toFixed(3)}/kWh` : "—"} />
            <MetricCell label="Proposed LCOE" value={sub.proposed_lcoe_usd_kwh != null ? `$${sub.proposed_lcoe_usd_kwh.toFixed(3)}/kWh` : "—"} />
            <MetricCell label="IRR" value={sub.proposed_irr_pct != null ? `${sub.proposed_irr_pct.toFixed(1)}%` : "—"} />
            <MetricCell label="Timeline" value={sub.proposed_timeline_months != null ? `${sub.proposed_timeline_months} months` : "—"} />
          </div>

          {sub.technical_approach && (
            <div className="mt-4 p-3 rounded-lg bg-white/3 border border-white/5">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Technical Approach</p>
              <p className="text-sm text-slate-300">{sub.technical_approach}</p>
            </div>
          )}

          {(sub.scoring_total != null) && (
            <div className="mt-4 flex items-center gap-4">
              <ScoreBar label="Technical" score={sub.scoring_technical} />
              <ScoreBar label="Financial" score={sub.scoring_financial} />
              <ScoreBar label="Experience" score={sub.scoring_experience} />
              <div className="ml-auto flex items-center gap-2">
                <Star className="h-4 w-4 text-afcen-gold" />
                <span className="text-white font-bold">{sub.scoring_total?.toFixed(1)}</span>
                <span className="text-xs text-slate-500">/ 100</span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-white font-medium tabular-nums">{value}</p>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score?: number }) {
  if (score == null) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 w-16">{label}</span>
      <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full bg-emerald-400"
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="text-xs text-slate-300 tabular-nums w-6">{score.toFixed(0)}</span>
    </div>
  );
}

// ── Comparison Tab ─────────────────────────────────────────────

function ComparisonTab({
  submissions,
  portfolio,
}: {
  submissions: Submission[];
  portfolio: Portfolio;
}) {
  if (submissions.length < 2) {
    return (
      <div className="flex flex-col items-center py-16 text-center">
        <BarChart3 className="h-10 w-10 text-slate-600 mb-3" />
        <p className="text-slate-400 text-sm">
          Add at least 2 submissions to compare bidders side by side.
        </p>
      </div>
    );
  }

  const sorted = [...submissions].sort(
    (a, b) => (b.scoring_total || 0) - (a.scoring_total || 0)
  );
  const bestCapex = Math.min(
    ...submissions.filter((s) => s.proposed_capex_usd != null).map((s) => s.proposed_capex_usd!)
  );
  const bestLcoe = Math.min(
    ...submissions.filter((s) => s.proposed_lcoe_usd_kwh != null).map((s) => s.proposed_lcoe_usd_kwh!)
  );
  const bestIrr = Math.max(
    ...submissions.filter((s) => s.proposed_irr_pct != null).map((s) => s.proposed_irr_pct!)
  );
  const bestTimeline = Math.min(
    ...submissions.filter((s) => s.proposed_timeline_months != null).map((s) => s.proposed_timeline_months!)
  );

  const rows: { label: string; key: string; format: (s: Submission) => string; best: (s: Submission) => boolean }[] = [
    {
      label: "Proposed CAPEX",
      key: "capex",
      format: (s) => formatUSD(s.proposed_capex_usd),
      best: (s) => s.proposed_capex_usd === bestCapex,
    },
    {
      label: "Grant Ask",
      key: "grant",
      format: (s) => formatUSD(s.proposed_grant_ask_usd),
      best: () => false,
    },
    {
      label: "Proposed Tariff",
      key: "tariff",
      format: (s) =>
        s.proposed_tariff_usd_kwh != null
          ? `$${s.proposed_tariff_usd_kwh.toFixed(3)}/kWh`
          : "—",
      best: () => false,
    },
    {
      label: "Proposed LCOE",
      key: "lcoe",
      format: (s) =>
        s.proposed_lcoe_usd_kwh != null
          ? `$${s.proposed_lcoe_usd_kwh.toFixed(3)}/kWh`
          : "—",
      best: (s) => s.proposed_lcoe_usd_kwh === bestLcoe,
    },
    {
      label: "Proposed IRR",
      key: "irr",
      format: (s) =>
        s.proposed_irr_pct != null ? `${s.proposed_irr_pct.toFixed(1)}%` : "—",
      best: (s) => s.proposed_irr_pct === bestIrr,
    },
    {
      label: "Timeline",
      key: "timeline",
      format: (s) =>
        s.proposed_timeline_months != null
          ? `${s.proposed_timeline_months} months`
          : "—",
      best: (s) => s.proposed_timeline_months === bestTimeline,
    },
    {
      label: "Technical Score",
      key: "scoring_tech",
      format: (s) => (s.scoring_technical != null ? s.scoring_technical.toFixed(1) : "—"),
      best: () => false,
    },
    {
      label: "Financial Score",
      key: "scoring_fin",
      format: (s) => (s.scoring_financial != null ? s.scoring_financial.toFixed(1) : "—"),
      best: () => false,
    },
    {
      label: "Experience Score",
      key: "scoring_exp",
      format: (s) => (s.scoring_experience != null ? s.scoring_experience.toFixed(1) : "—"),
      best: () => false,
    },
    {
      label: "Total Score",
      key: "scoring_total",
      format: (s) => (s.scoring_total != null ? s.scoring_total.toFixed(1) : "—"),
      best: (s) => s.scoring_total === sorted[0]?.scoring_total && s.scoring_total != null,
    },
  ];

  return (
    <div className="rounded-xl border border-white/10 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-white/5 border-b border-white/10">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase w-40">
                Metric
              </th>
              {sorted.map((s) => (
                <th key={s.id} className="px-4 py-3 text-center min-w-[160px]">
                  <p className="text-white font-semibold text-sm">{s.bidder_name}</p>
                  {s.bidder_organization && (
                    <p className="text-xs text-slate-500 font-normal">{s.bidder_organization}</p>
                  )}
                  <span className={`mt-1 inline-flex px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${
                    SUBMISSION_STATUS_COLORS[s.status] || ""
                  }`}>
                    {s.status.replace("_", " ")}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((row) => (
              <tr key={row.key} className="hover:bg-white/3">
                <td className="px-4 py-2.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  {row.label}
                </td>
                {sorted.map((s) => (
                  <td
                    key={s.id}
                    className={`px-4 py-2.5 text-center tabular-nums ${
                      row.best(s)
                        ? "text-emerald-300 font-semibold"
                        : "text-slate-300"
                    }`}
                  >
                    {row.format(s)}
                    {row.best(s) && (
                      <Check className="h-3.5 w-3.5 text-emerald-400 inline ml-1" />
                    )}
                  </td>
                ))}
              </tr>
            ))}

            {/* Technical Approach row */}
            <tr className="hover:bg-white/3">
              <td className="px-4 py-2.5 text-xs font-medium text-slate-400 uppercase tracking-wider align-top">
                Technical Approach
              </td>
              {sorted.map((s) => (
                <td key={s.id} className="px-4 py-2.5 text-xs text-slate-300 max-w-[200px]">
                  {s.technical_approach || "—"}
                </td>
              ))}
            </tr>

            {/* Experience row */}
            <tr className="hover:bg-white/3">
              <td className="px-4 py-2.5 text-xs font-medium text-slate-400 uppercase tracking-wider align-top">
                Experience
              </td>
              {sorted.map((s) => (
                <td key={s.id} className="px-4 py-2.5 text-xs text-slate-300 max-w-[200px]">
                  {s.experience_summary || "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Add Submission Modal ───────────────────────────────────────

function AddSubmissionModal({
  portfolioId,
  onClose,
  onCreated,
}: {
  portfolioId: string;
  onClose: () => void;
  onCreated: (sub: Submission) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    bidder_name: "",
    bidder_organization: "",
    contact_email: "",
    proposed_capex_usd: "",
    proposed_grant_ask_usd: "",
    proposed_tariff_usd_kwh: "",
    proposed_lcoe_usd_kwh: "",
    proposed_irr_pct: "",
    proposed_timeline_months: "",
    technical_approach: "",
    experience_summary: "",
    scoring_technical: "",
    scoring_financial: "",
    scoring_experience: "",
  });

  const handleSubmit = async () => {
    if (!form.bidder_name) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        portfolio_id: portfolioId,
        bidder_name: form.bidder_name,
      };
      if (form.bidder_organization) data.bidder_organization = form.bidder_organization;
      if (form.contact_email) data.contact_email = form.contact_email;
      if (form.proposed_capex_usd) data.proposed_capex_usd = Number(form.proposed_capex_usd);
      if (form.proposed_grant_ask_usd)
        data.proposed_grant_ask_usd = Number(form.proposed_grant_ask_usd);
      if (form.proposed_tariff_usd_kwh)
        data.proposed_tariff_usd_kwh = Number(form.proposed_tariff_usd_kwh);
      if (form.proposed_lcoe_usd_kwh)
        data.proposed_lcoe_usd_kwh = Number(form.proposed_lcoe_usd_kwh);
      if (form.proposed_irr_pct) data.proposed_irr_pct = Number(form.proposed_irr_pct);
      if (form.proposed_timeline_months)
        data.proposed_timeline_months = Number(form.proposed_timeline_months);
      if (form.technical_approach) data.technical_approach = form.technical_approach;
      if (form.experience_summary) data.experience_summary = form.experience_summary;
      if (form.scoring_technical) data.scoring_technical = Number(form.scoring_technical);
      if (form.scoring_financial) data.scoring_financial = Number(form.scoring_financial);
      if (form.scoring_experience) data.scoring_experience = Number(form.scoring_experience);
      if (form.scoring_technical && form.scoring_financial && form.scoring_experience) {
        data.scoring_total =
          (Number(form.scoring_technical) +
            Number(form.scoring_financial) +
            Number(form.scoring_experience)) /
          3;
      }

      const sub = await createSubmission(portfolioId, data as any);
      onCreated(sub);
    } catch {
      /* handled */
    } finally {
      setSaving(false);
    }
  };

  const field = (label: string, key: keyof typeof form, type = "text", placeholder?: string) => (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1">{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-afcen-navy-light border border-white/10 rounded-xl w-full max-w-2xl p-6 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-white">Add Bidder Submission</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Bidder Information</p>
          <div className="grid grid-cols-2 gap-4">
            {field("Bidder Name *", "bidder_name", "text", "e.g. SunFunder")}
            {field("Organization", "bidder_organization")}
            {field("Contact Email", "contact_email", "email")}
          </div>

          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold pt-3">Financial Proposal</p>
          <div className="grid grid-cols-2 gap-4">
            {field("Proposed CAPEX (USD)", "proposed_capex_usd", "number")}
            {field("Grant Ask (USD)", "proposed_grant_ask_usd", "number")}
            {field("Proposed Tariff ($/kWh)", "proposed_tariff_usd_kwh", "number", "e.g. 0.35")}
            {field("Proposed LCOE ($/kWh)", "proposed_lcoe_usd_kwh", "number", "e.g. 0.28")}
            {field("Proposed IRR (%)", "proposed_irr_pct", "number")}
            {field("Timeline (months)", "proposed_timeline_months", "number")}
          </div>

          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold pt-3">Technical Details</p>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Technical Approach</label>
            <textarea
              value={form.technical_approach}
              onChange={(e) => setForm((p) => ({ ...p, technical_approach: e.target.value }))}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Experience Summary</label>
            <textarea
              value={form.experience_summary}
              onChange={(e) => setForm((p) => ({ ...p, experience_summary: e.target.value }))}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>

          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold pt-3">Scoring (0–100)</p>
          <div className="grid grid-cols-3 gap-4">
            {field("Technical Score", "scoring_technical", "number")}
            {field("Financial Score", "scoring_financial", "number")}
            {field("Experience Score", "scoring_experience", "number")}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!form.bidder_name || saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 text-sm font-semibold text-white hover:bg-emerald-400 transition disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Add Submission
          </button>
        </div>
      </div>
    </div>
  );
}
