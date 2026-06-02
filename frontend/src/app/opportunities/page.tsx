"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Zap,
  Plus,
  Send,
  X,
  Loader2,
  Pencil,
  Trash2,
  Search,
} from "lucide-react";
import {
  fetchOpportunities,
  createOpportunity,
  updateOpportunity,
  deleteOpportunity,
  createPortfolio,
  fetchPortfolios,
} from "@/lib/api";
import type { Opportunity, PortfolioSummary } from "@/lib/api";

type StatusFilter = "all" | "scoped" | "floated" | "submitted";

const STATUS_COLORS: Record<string, string> = {
  scoped: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  floated: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  submitted: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
};

function formatUSD(val?: number) {
  if (val == null) return "—";
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
  return `$${val.toFixed(0)}`;
}

function formatNum(val?: number, decimals = 1) {
  if (val == null) return "—";
  return val.toLocaleString(undefined, { maximumFractionDigits: decimals });
}

function formatPct(val?: number) {
  if (val == null) return "—";
  return `${val.toFixed(1)}%`;
}

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showAddForm, setShowAddForm] = useState(false);
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [portfolioName, setPortfolioName] = useState("");
  const [sending, setSending] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (statusFilter !== "all") params.status = statusFilter;
      const data = await fetchOpportunities(params);
      setOpportunities(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filtered = opportunities.filter((o) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      o.project_name.toLowerCase().includes(q) ||
      o.province.toLowerCase().includes(q) ||
      (o.district?.toLowerCase().includes(q) ?? false)
    );
  });

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map((o) => o.id)));
    }
  };

  const handleSendToPortfolio = async () => {
    if (selected.size === 0) return;
    try {
      const data = await fetchPortfolios();
      setPortfolios(data);
    } catch {
      /* ignore */
    }
    setShowPortfolioModal(true);
  };

  const handleCreatePortfolio = async () => {
    if (!portfolioName.trim()) return;
    setSending(true);
    try {
      await createPortfolio({
        name: portfolioName,
        opportunity_ids: Array.from(selected),
      });
      setShowPortfolioModal(false);
      setPortfolioName("");
      setSelected(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create portfolio");
    } finally {
      setSending(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteOpportunity(id);
      setOpportunities((prev) => prev.filter((o) => o.id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
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
            <span className="text-sm text-slate-300">Opportunities</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/analyze" className="text-sm text-slate-400 hover:text-white transition">
              New Analysis
            </Link>
            <Link href="/projects" className="text-sm text-slate-400 hover:text-white transition">
              Projects
            </Link>
            <Link href="/opportunities" className="text-sm text-white font-medium">
              Opportunities
            </Link>
            <Link href="/portfolios" className="text-sm text-slate-400 hover:text-white transition">
              Portfolios
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 w-64 focus:outline-none focus:border-emerald-500/50"
              />
            </div>

            <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-lg p-0.5">
              {(["all", "scoped", "floated", "submitted"] as StatusFilter[]).map(
                (s) => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition capitalize ${
                      statusFilter === s
                        ? "bg-emerald-500/20 text-emerald-300"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {s}
                  </button>
                )
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {selected.size > 0 && (
              <button
                onClick={handleSendToPortfolio}
                className="flex items-center gap-2 rounded-lg bg-afcen-gold/20 border border-afcen-gold/30 px-4 py-2 text-sm font-medium text-afcen-gold hover:bg-afcen-gold/30 transition"
              >
                <Send className="h-4 w-4" />
                Send to Portfolio ({selected.size})
              </button>
            )}
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-400 transition"
            >
              <Plus className="h-4 w-4" />
              Add Opportunity
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
            {error}
            <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
          </div>
        )}

        {/* Table */}
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/5 border-b border-white/10">
                  <th className="w-10 px-3 py-3">
                    <input
                      type="checkbox"
                      checked={filtered.length > 0 && selected.size === filtered.length}
                      onChange={toggleAll}
                      className="rounded border-white/20 bg-transparent accent-emerald-500"
                    />
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Project Name</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Province</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Program</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Connections</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">PUE Value Chains</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">PV (kWp)</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Battery (kWh)</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Dist. Lines (m)</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Total CAPEX</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">$/Connection</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Grant/Conn</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">LCOE</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">IRR</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Payback (yr)</th>
                  <th className="px-3 py-3 w-20"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {loading ? (
                  <tr>
                    <td colSpan={17} className="px-6 py-16 text-center">
                      <Loader2 className="h-6 w-6 text-emerald-400 animate-spin mx-auto mb-2" />
                      <span className="text-slate-400 text-sm">Loading opportunities...</span>
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={17} className="px-6 py-16 text-center">
                      <p className="text-slate-400 text-sm">
                        {opportunities.length === 0
                          ? "No opportunities yet. Add your first project to the pipeline."
                          : "No opportunities match your filters."}
                      </p>
                    </td>
                  </tr>
                ) : (
                  filtered.map((opp) => (
                    <tr
                      key={opp.id}
                      className={`hover:bg-white/3 transition ${
                        selected.has(opp.id) ? "bg-emerald-500/5" : ""
                      }`}
                    >
                      <td className="px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={selected.has(opp.id)}
                          onChange={() => toggleSelect(opp.id)}
                          className="rounded border-white/20 bg-transparent accent-emerald-500"
                        />
                      </td>
                      <td className="px-3 py-2.5 text-white font-medium whitespace-nowrap">
                        {opp.project_name}
                      </td>
                      <td className="px-3 py-2.5 text-slate-300">{opp.province}</td>
                      <td className="px-3 py-2.5">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${
                            STATUS_COLORS[opp.status] || "text-slate-400"
                          }`}
                        >
                          {opp.status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-slate-300 text-xs">{opp.program_name}</td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatNum(opp.connections_targeted, 0)}
                      </td>
                      <td className="px-3 py-2.5 text-slate-300 text-xs max-w-[160px]">
                        {opp.pue_value_chains?.slice(0, 3).join(", ") || "—"}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatNum(opp.pv_capacity_kwp)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatNum(opp.battery_capacity_kwh)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatNum(opp.distribution_line_length_m, 0)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-white font-medium tabular-nums">
                        {formatUSD(opp.total_capex_usd)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatUSD(opp.cost_per_connection_usd)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatUSD(opp.grant_per_connection_usd)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {opp.lcoe_usd_kwh != null
                          ? `$${opp.lcoe_usd_kwh.toFixed(3)}`
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatPct(opp.irr_pct)}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">
                        {formatNum(opp.payback_years)}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setEditingId(opp.id)}
                            className="p-1.5 rounded hover:bg-white/10 text-slate-500 hover:text-white transition"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(opp.id)}
                            className="p-1.5 rounded hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer summary */}
        {filtered.length > 0 && (
          <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
            <span>
              {filtered.length} opportunit{filtered.length === 1 ? "y" : "ies"}
              {selected.size > 0 && ` · ${selected.size} selected`}
            </span>
            <span>
              Total CAPEX: {formatUSD(filtered.reduce((s, o) => s + (o.total_capex_usd || 0), 0))}
              {" · "}
              Total Connections: {formatNum(filtered.reduce((s, o) => s + (o.connections_targeted || 0), 0), 0)}
            </span>
          </div>
        )}
      </main>

      {/* Add Opportunity Modal */}
      {showAddForm && (
        <AddOpportunityModal
          onClose={() => setShowAddForm(false)}
          onCreated={(opp) => {
            setOpportunities((prev) => [opp, ...prev]);
            setShowAddForm(false);
          }}
        />
      )}

      {/* Edit Opportunity Modal */}
      {editingId && (
        <EditOpportunityModal
          opportunity={opportunities.find((o) => o.id === editingId)!}
          onClose={() => setEditingId(null)}
          onUpdated={(updated) => {
            setOpportunities((prev) =>
              prev.map((o) => (o.id === updated.id ? updated : o))
            );
            setEditingId(null);
          }}
        />
      )}

      {/* Send to Portfolio Modal */}
      {showPortfolioModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-afcen-navy-light border border-white/10 rounded-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-white mb-1">Send to Portfolio</h3>
            <p className="text-sm text-slate-400 mb-5">
              Create a new portfolio with {selected.size} selected project{selected.size !== 1 ? "s" : ""}.
            </p>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Portfolio Name</label>
            <input
              type="text"
              value={portfolioName}
              onChange={(e) => setPortfolioName(e.target.value)}
              placeholder="e.g. Enabel Batch 1 — Zambezia"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 mb-5"
              autoFocus
            />

            {portfolios.length > 0 && (
              <div className="mb-5">
                <p className="text-xs text-slate-400 mb-2">Or add to existing portfolio:</p>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {portfolios.map((p) => (
                    <button
                      key={p.id}
                      className="w-full text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-slate-300 transition"
                      onClick={async () => {
                        setSending(true);
                        try {
                          const res = await fetch(
                            `${process.env.NEXT_PUBLIC_API_URL || "https://amiable-spontaneity-production.up.railway.app"}/api/portfolios/${p.id}/opportunities`,
                            {
                              method: "POST",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({ opportunity_ids: Array.from(selected) }),
                            }
                          );
                          if (!res.ok) throw new Error("Failed");
                          setShowPortfolioModal(false);
                          setSelected(new Set());
                        } catch {
                          setError("Failed to add to portfolio");
                        } finally {
                          setSending(false);
                        }
                      }}
                    >
                      {p.name}
                      <span className="text-xs text-slate-500 ml-2">
                        ({p.opportunity_count} projects)
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setShowPortfolioModal(false)}
                className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={handleCreatePortfolio}
                disabled={!portfolioName.trim() || sending}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 text-sm font-semibold text-white hover:bg-emerald-400 transition disabled:opacity-50"
              >
                {sending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Create Portfolio
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Add Opportunity Modal ──────────────────────────────────────

function AddOpportunityModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (opp: Opportunity) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    project_name: "",
    province: "",
    district: "",
    status: "scoped" as const,
    program_name: "Enabel",
    connections_targeted: "",
    pue_value_chains: "",
    pv_capacity_kwp: "",
    battery_capacity_kwh: "",
    distribution_line_length_m: "",
    total_capex_usd: "",
    cost_per_connection_usd: "",
    grant_per_connection_usd: "",
    lcoe_usd_kwh: "",
    irr_pct: "",
    payback_years: "",
  });

  const handleSubmit = async () => {
    if (!form.project_name || !form.province) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        project_name: form.project_name,
        province: form.province,
        status: form.status,
        program_name: form.program_name,
      };
      if (form.district) data.district = form.district;
      if (form.connections_targeted) data.connections_targeted = Number(form.connections_targeted);
      if (form.pue_value_chains)
        data.pue_value_chains = form.pue_value_chains.split(",").map((s) => s.trim());
      if (form.pv_capacity_kwp) data.pv_capacity_kwp = Number(form.pv_capacity_kwp);
      if (form.battery_capacity_kwh) data.battery_capacity_kwh = Number(form.battery_capacity_kwh);
      if (form.distribution_line_length_m)
        data.distribution_line_length_m = Number(form.distribution_line_length_m);
      if (form.total_capex_usd) data.total_capex_usd = Number(form.total_capex_usd);
      if (form.cost_per_connection_usd)
        data.cost_per_connection_usd = Number(form.cost_per_connection_usd);
      if (form.grant_per_connection_usd)
        data.grant_per_connection_usd = Number(form.grant_per_connection_usd);
      if (form.lcoe_usd_kwh) data.lcoe_usd_kwh = Number(form.lcoe_usd_kwh);
      if (form.irr_pct) data.irr_pct = Number(form.irr_pct);
      if (form.payback_years) data.payback_years = Number(form.payback_years);

      const opp = await createOpportunity(data as any);
      onCreated(opp);
    } catch {
      /* handled */
    } finally {
      setSaving(false);
    }
  };

  const field = (
    label: string,
    key: keyof typeof form,
    type: string = "text",
    placeholder?: string
  ) => (
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
          <h3 className="text-lg font-semibold text-white">Add Opportunity</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {field("Project Name *", "project_name", "text", "e.g. Megaza 60kWp")}
          {field("Province *", "province", "text", "e.g. Zambezia")}
          {field("District", "district", "text", "e.g. Mocuba")}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
            <select
              value={form.status}
              onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as any }))}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500/50"
            >
              <option value="scoped">Scoped</option>
              <option value="floated">Floated</option>
              <option value="submitted">Submitted</option>
            </select>
          </div>
          {field("Program Name", "program_name", "text", "Enabel")}
          {field("Connections Targeted", "connections_targeted", "number")}
          <div className="col-span-2">
            {field("PUE Value Chains (comma-separated)", "pue_value_chains", "text", "e.g. Agriculture, Fisheries, Retail")}
          </div>
          {field("PV Capacity (kWp)", "pv_capacity_kwp", "number")}
          {field("Battery Storage (kWh)", "battery_capacity_kwh", "number")}
          {field("Distribution Lines (m)", "distribution_line_length_m", "number")}
          {field("Total CAPEX (USD)", "total_capex_usd", "number")}
          {field("Cost per Connection (USD)", "cost_per_connection_usd", "number")}
          {field("Grant per Connection (USD)", "grant_per_connection_usd", "number")}
          {field("LCOE (USD/kWh)", "lcoe_usd_kwh", "number", "e.g. 0.35")}
          {field("IRR (%)", "irr_pct", "number", "e.g. 12.5")}
          {field("Payback Period (years)", "payback_years", "number")}
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
            disabled={!form.project_name || !form.province || saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 text-sm font-semibold text-white hover:bg-emerald-400 transition disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Add Opportunity
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Edit Opportunity Modal ─────────────────────────────────────

function EditOpportunityModal({
  opportunity,
  onClose,
  onUpdated,
}: {
  opportunity: Opportunity;
  onClose: () => void;
  onUpdated: (opp: Opportunity) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    project_name: opportunity.project_name,
    province: opportunity.province,
    district: opportunity.district || "",
    status: opportunity.status,
    program_name: opportunity.program_name,
    connections_targeted: opportunity.connections_targeted?.toString() || "",
    pue_value_chains: opportunity.pue_value_chains?.join(", ") || "",
    pv_capacity_kwp: opportunity.pv_capacity_kwp?.toString() || "",
    battery_capacity_kwh: opportunity.battery_capacity_kwh?.toString() || "",
    distribution_line_length_m: opportunity.distribution_line_length_m?.toString() || "",
    total_capex_usd: opportunity.total_capex_usd?.toString() || "",
    cost_per_connection_usd: opportunity.cost_per_connection_usd?.toString() || "",
    grant_per_connection_usd: opportunity.grant_per_connection_usd?.toString() || "",
    lcoe_usd_kwh: opportunity.lcoe_usd_kwh?.toString() || "",
    irr_pct: opportunity.irr_pct?.toString() || "",
    payback_years: opportunity.payback_years?.toString() || "",
  });

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        project_name: form.project_name,
        province: form.province,
        status: form.status,
        program_name: form.program_name,
      };
      if (form.district) data.district = form.district;
      if (form.connections_targeted) data.connections_targeted = Number(form.connections_targeted);
      if (form.pue_value_chains)
        data.pue_value_chains = form.pue_value_chains.split(",").map((s) => s.trim());
      if (form.pv_capacity_kwp) data.pv_capacity_kwp = Number(form.pv_capacity_kwp);
      if (form.battery_capacity_kwh) data.battery_capacity_kwh = Number(form.battery_capacity_kwh);
      if (form.distribution_line_length_m)
        data.distribution_line_length_m = Number(form.distribution_line_length_m);
      if (form.total_capex_usd) data.total_capex_usd = Number(form.total_capex_usd);
      if (form.cost_per_connection_usd)
        data.cost_per_connection_usd = Number(form.cost_per_connection_usd);
      if (form.grant_per_connection_usd)
        data.grant_per_connection_usd = Number(form.grant_per_connection_usd);
      if (form.lcoe_usd_kwh) data.lcoe_usd_kwh = Number(form.lcoe_usd_kwh);
      if (form.irr_pct) data.irr_pct = Number(form.irr_pct);
      if (form.payback_years) data.payback_years = Number(form.payback_years);

      const updated = await updateOpportunity(opportunity.id, data as any);
      onUpdated(updated);
    } catch {
      /* handled */
    } finally {
      setSaving(false);
    }
  };

  const field = (
    label: string,
    key: keyof typeof form,
    type: string = "text",
    placeholder?: string
  ) => (
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
          <h3 className="text-lg font-semibold text-white">Edit Opportunity</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {field("Project Name", "project_name")}
          {field("Province", "province")}
          {field("District", "district")}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
            <select
              value={form.status}
              onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as any }))}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500/50"
            >
              <option value="scoped">Scoped</option>
              <option value="floated">Floated</option>
              <option value="submitted">Submitted</option>
            </select>
          </div>
          {field("Program Name", "program_name")}
          {field("Connections Targeted", "connections_targeted", "number")}
          <div className="col-span-2">
            {field("PUE Value Chains (comma-separated)", "pue_value_chains", "text")}
          </div>
          {field("PV Capacity (kWp)", "pv_capacity_kwp", "number")}
          {field("Battery Storage (kWh)", "battery_capacity_kwh", "number")}
          {field("Distribution Lines (m)", "distribution_line_length_m", "number")}
          {field("Total CAPEX (USD)", "total_capex_usd", "number")}
          {field("Cost per Connection (USD)", "cost_per_connection_usd", "number")}
          {field("Grant per Connection (USD)", "grant_per_connection_usd", "number")}
          {field("LCOE (USD/kWh)", "lcoe_usd_kwh", "number")}
          {field("IRR (%)", "irr_pct", "number")}
          {field("Payback Period (years)", "payback_years", "number")}
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
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 text-sm font-semibold text-white hover:bg-emerald-400 transition disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
