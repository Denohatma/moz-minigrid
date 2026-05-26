"""
PFS Executive Summary Generator — 5-Page Decision Brief
Mozambique Mini-Grid Pre-Feasibility Study

Distils the full PFS into a concise 5-page executive summary for
investor / donor / ARENE decision-makers.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml


# ═══════════════════════════════════════════════════════════════════════
# Colour palette (matches full PFS)
# ═══════════════════════════════════════════════════════════════════════
_GREEN = RGBColor(0x2F, 0x85, 0x5A)
_GREEN_DARK = RGBColor(0x22, 0x6B, 0x47)
_NAVY = RGBColor(0x1A, 0x20, 0x2C)
_SLATE = RGBColor(0x4A, 0x55, 0x68)
_GREY = RGBColor(0x71, 0x80, 0x96)
_RED = RGBColor(0xC5, 0x3D, 0x3D)
_AMBER = RGBColor(0xD6, 0x9E, 0x2E)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)

_HDR_BG = "2F855A"
_ALT_BG = "F0FAF4"
_BORDER = "CBD5E0"


# ═══════════════════════════════════════════════════════════════════════
# Safe accessors
# ═══════════════════════════════════════════════════════════════════════
def _g(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            return default
        if cur is None:
            return default
    return cur


def _usd(val, default="--"):
    if val is None:
        return default
    return f"USD {val:,.0f}"


def _usd_kwh(val, default="--"):
    if val is None:
        return default
    return f"USD {val:.4f}/kWh"


# ═══════════════════════════════════════════════════════════════════════
# Document helpers
# ═══════════════════════════════════════════════════════════════════════
def _setup(doc: Document):
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)
    style.paragraph_format.space_after = Pt(3)
    style.paragraph_format.space_before = Pt(0)
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)


def _h1(doc, text):
    p = doc.add_heading(text, level=1)
    for run in p.runs:
        run.font.color.rgb = _GREEN
        run.font.size = Pt(16)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)


def _h2(doc, text):
    p = doc.add_heading(text, level=2)
    for run in p.runs:
        run.font.color.rgb = _NAVY
        run.font.size = Pt(12)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)


def _para(doc, text, bold=False, italic=False, size=10, color=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    p.paragraph_format.space_after = Pt(3)
    return p


def _centered(doc, text, bold=False, size=12, color=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    return p


def _blank(doc, n=1):
    for _ in range(n):
        doc.add_paragraph()


def _bullet(doc, text, size=10):
    p = doc.add_paragraph(text, style="List Bullet")
    for run in p.runs:
        run.font.size = Pt(size)


def _add_table(doc, data, small=False, col_widths=None):
    if not data or not data[0]:
        return None
    n_rows = len(data)
    n_cols = len(data[0])
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    if col_widths and len(col_widths) == n_cols:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Inches(w)

    fs = Pt(7) if small else Pt(8)

    for i, row_data in enumerate(data):
        row = table.rows[i]
        for j, cell_text in enumerate(row_data):
            cell = row.cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_text))
            run.font.size = fs
            run.font.name = "Calibri"
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)

            if i == 0:
                run.bold = True
                run.font.color.rgb = _WHITE
                shading = parse_xml(
                    f'<w:shd {nsdecls("w")} w:fill="{_HDR_BG}" w:val="clear"/>'
                )
                cell._tc.get_or_add_tcPr().append(shading)
            elif i % 2 == 0:
                shading = parse_xml(
                    f'<w:shd {nsdecls("w")} w:fill="{_ALT_BG}" w:val="clear"/>'
                )
                cell._tc.get_or_add_tcPr().append(shading)

    _set_borders(table)
    return table


def _set_borders(table):
    tbl = table._tbl
    tbl_pr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}/>')
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{_BORDER}"/>'
        f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="{_BORDER}"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{_BORDER}"/>'
        f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="{_BORDER}"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{_BORDER}"/>'
        f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{_BORDER}"/>'
        f'</w:tblBorders>'
    )
    tbl_pr.append(borders)


def _caption(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.italic = True
    run.font.size = Pt(8)
    run.font.color.rgb = _SLATE
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(1)


# ═══════════════════════════════════════════════════════════════════════
# Main generator
# ═══════════════════════════════════════════════════════════════════════
def generate_pfs_summary(result: dict, site_name: str, output_path: str) -> str:
    """
    Generate a 5-page executive summary .docx from the same analysis result
    dict used by the full PFS template.
    """
    doc = Document()
    _setup(doc)

    # ── Extract sub-dicts ────────────────────────────────────────
    demand = result.get("demand", {})
    sizing = result.get("sizing", {})
    financial = result.get("financial", {})
    distribution = result.get("distribution", {})
    productive_use = result.get("productive_use", {})
    carbon = result.get("carbon", {})
    climate = result.get("climate", {})
    ess = result.get("ess", {})
    risk_analysis = result.get("risk_analysis", {})
    confidence = result.get("confidence", {})
    grid_risk = result.get("grid_risk", {})
    solar_resource = result.get("solar_resource", {})
    cluster = result.get("cluster", {})

    # ── Derived values ───────────────────────────────────────────
    province = _g(cluster, "admin_region") or "Unknown Province"
    district = _g(cluster, "admin_district") or "Unknown District"
    population = _g(cluster, "population") or 0
    households = _g(demand, "households") or 0
    total_hh = _g(demand, "total_settlement_households") or int(households / 0.5)
    coverage_pct = _g(demand, "coverage_pct") or 0.50
    pv_kwp = _g(sizing, "pv_kwp") or 0
    battery_kwh = _g(sizing, "battery_kwh_usable") or 0
    inverter_kva = _g(sizing, "inverter_kva") or 0
    total_capex = _g(financial, "total_capex_usd") or 0
    irr = _g(financial, "irr_pct") or 0
    payback = _g(financial, "payback_years") or 99
    lcoe = _g(financial, "lcoe_usd_kwh")
    npv = _g(financial, "npv_usd") or 0
    dscr = _g(financial, "dscr") or 0
    cost_reflective = _g(financial, "cost_reflective_tariff_usd")
    affordable_tariff = _g(financial, "affordable_tariff_usd")
    subsidy_gap_pct = _g(financial, "subsidy_gap_pct_capex") or 0
    subsidy_gap_total = _g(financial, "subsidy_gap_total_usd") or 0
    annual_energy = _g(demand, "annual_energy_kwh") or 0
    daily_energy = _g(demand, "daily_energy_kwh") or 0
    peak_kw = _g(demand, "peak_demand_kw") or 0
    pu_kwh_day = _g(demand, "productive_use_kwh_day") or _g(productive_use, "total_productive_demand_kwh_day") or 0
    pu_demand_pct = _g(productive_use, "productive_demand_pct") or 0
    dist_mv = _g(grid_risk, "dist_mv_km") or 0
    has_nightlight = _g(cluster, "has_nightlight") or False
    lat = _g(cluster, "latitude") or _g(result, "site", "latitude") or 0
    lon = _g(cluster, "longitude") or _g(result, "site", "longitude") or 0
    ghi = _g(solar_resource, "annual_ghi_kwh_m2") or _g(cluster, "ghi_kwh_m2_year") or 0
    ann_gen_kwh = _g(sizing, "annual_generation_kwh") or 0
    unmet_pct = _g(sizing, "unmet_energy_pct") or 0
    capex_per_wp = _g(financial, "capex_per_wp") or (total_capex / max(pv_kwp * 1000, 1))
    annual_opex = _g(financial, "annual_opex_usd") or 0
    dist_cost = _g(distribution, "total_network_cost_usd") or 0
    dist_per_conn = _g(distribution, "cost_per_connection_usd") or 0
    today = date.today()
    month_year = today.strftime("%B %Y")
    demand_growth = 0.03

    # Recommendation logic
    if irr > 10 and payback < 15:
        recommendation = "PROCEED TO FULL FEASIBILITY"
        rec_color = _GREEN
    elif irr > 5 and payback < 20:
        recommendation = "PROCEED WITH CONDITIONS"
        rec_color = _AMBER
    elif irr > 0 and payback < 25:
        recommendation = "CONDITIONAL GO — BLENDED FINANCE REQUIRED"
        rec_color = _AMBER
    elif subsidy_gap_pct < 80:
        recommendation = "BUNDLE / CLUSTER FOR VIABILITY"
        rec_color = RGBColor(0xED, 0x89, 0x36)
    else:
        recommendation = "HOLD — REASSESS WITH FIELD DATA"
        rec_color = _RED

    # Concession model
    if dist_mv > 50:
        concession_model = "Isolated mini-grid concession (25 yr)"
    elif dist_mv > 20:
        concession_model = "Isolated mini-grid concession (20 yr)"
    else:
        concession_model = "Isolated mini-grid with grid-arrival clause (15-20 yr)"

    # ══════════════════════════════════════════════════════════════
    # PAGE 1: COVER + DECISION DASHBOARD
    # ══════════════════════════════════════════════════════════════
    _blank(doc, 2)
    _centered(doc, "EXECUTIVE SUMMARY", bold=True, size=24, color=_GREEN)
    _centered(doc, "PRE-FEASIBILITY STUDY", bold=True, size=14, color=_SLATE)
    _blank(doc)
    _centered(doc, f"{site_name.upper()} SOLAR PV MINI-GRID", bold=True, size=18, color=_NAVY)
    _centered(doc, f"{pv_kwp:.0f} kWp Isolated Solar PV with Battery Storage",
              size=12, color=_SLATE)
    _centered(doc, f"{district}, {province}, Mozambique", size=11, color=_SLATE)
    _blank(doc)
    _centered(doc, f"{month_year}", size=10, color=_GREY)
    _centered(doc, "CONFIDENTIAL — DRAFT FOR REVIEW", bold=True, size=10, color=_RED)
    _blank(doc)

    # Decision Dashboard table
    _h2(doc, "Decision Dashboard")

    year5_energy = annual_energy * (1 + demand_growth) ** 5

    blockers = []
    if irr < 5:
        blockers.append("Low project IRR without subsidy")
    if subsidy_gap_pct > 60:
        blockers.append(f"High subsidy requirement ({subsidy_gap_pct:.0f}% CAPEX)")
    if _g(grid_risk, "risk_level") == "critical":
        blockers.append("Critical grid-arrival risk")
    if not blockers:
        blockers.append("None identified at screening stage")

    dashboard = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Recommendation", recommendation, "Connections (Rd 1)", f"{households:,} of {total_hh:,}"],
        ["Concession Model", concession_model, "Coverage", f"{coverage_pct * 100:.0f}%"],
        ["Total CAPEX", _usd(total_capex), "PV Capacity", f"{pv_kwp:.0f} kWp"],
        ["CAPEX/Wp", f"USD {capex_per_wp:.2f}/Wp", "Battery", f"{battery_kwh:.0f} kWh usable"],
        ["Project IRR", f"{irr:.1f}%", "Year-1 Demand", f"{annual_energy:,.0f} kWh/yr"],
        ["LCOE", _usd_kwh(lcoe), "Year-5 Demand", f"{year5_energy:,.0f} kWh/yr"],
        ["Payback", f"{payback:.1f} years", "PUE Share", f"{pu_demand_pct:.0f}%"],
        ["Subsidy Gap", f"{subsidy_gap_pct:.0f}% ({_usd(subsidy_gap_total)})",
         "Grid Distance", f"{dist_mv:.1f} km (MV)"],
        ["Key Blocker", "; ".join(blockers), "Grid Risk",
         (_g(grid_risk, "risk_level") or "unknown").upper()],
    ]
    _caption(doc, f"Table 1: Decision dashboard — {site_name}")
    _add_table(doc, dashboard)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # PAGE 2: SITE OVERVIEW + DEMAND
    # ══════════════════════════════════════════════════════════════
    _h1(doc, "1. Site Overview")

    area = _g(cluster, "area_km2") or 0
    num_buildings = _g(cluster, "num_buildings") or 0
    dist_road = _g(cluster, "dist_road_km") or 0
    urban_idx = min(_g(cluster, "is_urban") or 0, 2)
    urban_label = ["Rural", "Peri-urban", "Urban"][urban_idx]
    num_edu = _g(cluster, "num_education_facilities") or 0
    num_health = _g(cluster, "num_health_facilities") or 0

    _para(doc,
          f"{site_name} is a {urban_label.lower()} settlement in {district}, {province}, "
          f"Mozambique, located at {abs(lat):.4f}°S, {abs(lon):.4f}°E. The settlement has an "
          f"estimated population of {population:,} across {total_hh:,} households, with "
          f"{num_buildings:,} structures identified from satellite imagery within {area:.2f} km². "
          f"{'The area is currently unelectrified.' if not has_nightlight else 'Partial electrification (SHS) is detected.'}")

    _caption(doc, "Table 2: Site characteristics")
    site_data = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Province / District", f"{province} / {district}", "Road Access", f"{dist_road:.1f} km"],
        ["Population", f"{population:,}", "MV Grid Distance", f"{dist_mv:.1f} km"],
        ["Total Households", f"{total_hh:,}", "Schools / Health", f"{num_edu} / {num_health}"],
        ["Classification", urban_label, "Solar GHI", f"{ghi:,.0f} kWh/m²/yr"],
        ["Electrification", "No" if not has_nightlight else "Partial",
         "Elevation", f"{_g(cluster, 'elevation_m') or '--'} m"],
    ]
    _add_table(doc, site_data)

    # ── Demand ───────────────────────────────────────────────────
    _h1(doc, "2. Demand Assessment")

    residential_kwh = daily_energy - pu_kwh_day if daily_energy > pu_kwh_day else daily_energy * 0.7
    _para(doc,
          f"Round 1 targets {coverage_pct * 100:.0f}% coverage ({households:,} of {total_hh:,} "
          f"households). Total projected demand is {daily_energy:.0f} kWh/day "
          f"({annual_energy:,.0f} kWh/year), with a peak of {peak_kw:.1f} kW. Productive use "
          f"demand contributes {pu_kwh_day:.0f} kWh/day ({pu_demand_pct:.0f}% of total), "
          f"ensuring system utilisation supports financial viability.")

    # Demand by class
    num_anchors = len(_g(productive_use, "anchors") or [])
    pub_kwh = 0
    if _g(cluster, "has_health_facility"):
        pub_kwh += 8.0
    if _g(cluster, "has_education_facility"):
        pub_kwh += 3.0

    _caption(doc, "Table 3: Demand by customer class")
    demand_data = [
        ["Class", "Year-1 (kWh/yr)", "% of Total", "Peak (kW)", "Confidence"],
        ["Residential", f"{residential_kwh * 365:,.0f}", f"{residential_kwh / max(daily_energy, 0.1) * 100:.0f}%",
         f"{peak_kw * 0.45:.1f}", "C"],
        ["Productive Use", f"{pu_kwh_day * 365:,.0f}", f"{pu_demand_pct:.0f}%",
         f"{peak_kw * 0.35:.1f}", "C-D"],
        ["Public Institutions", f"{pub_kwh * 365:,.0f}",
         f"{pub_kwh / max(daily_energy, 0.1) * 100:.0f}%",
         f"{peak_kw * 0.15:.1f}", "C"],
        ["Commercial", f"{max(0, daily_energy - residential_kwh - pu_kwh_day - pub_kwh) * 365:,.0f}",
         f"{max(0, 100 - residential_kwh / max(daily_energy, 0.1) * 100 - pu_demand_pct - pub_kwh / max(daily_energy, 0.1) * 100):.0f}%",
         f"{peak_kw * 0.05:.1f}", "D"],
        ["TOTAL", f"{annual_energy:,.0f}", "100%", f"{peak_kw:.1f}", ""],
    ]
    _add_table(doc, demand_data)

    # Demand scenarios
    _caption(doc, "Table 4: Demand scenarios")
    scenario_data = [
        ["Scenario", "Year-1 (kWh/yr)", "Year-5 (kWh/yr)", "Year-10 (kWh/yr)"],
        ["Conservative (-25%)", f"{annual_energy * 0.75:,.0f}",
         f"{annual_energy * 0.75 * (1 + demand_growth) ** 5:,.0f}",
         f"{annual_energy * 0.75 * (1 + demand_growth) ** 10:,.0f}"],
        ["Base Case", f"{annual_energy:,.0f}", f"{year5_energy:,.0f}",
         f"{annual_energy * (1 + demand_growth) ** 10:,.0f}"],
        ["PUE-Activated (+30%)", f"{annual_energy * 1.3:,.0f}",
         f"{annual_energy * 1.3 * (1 + 0.05) ** 5:,.0f}",
         f"{annual_energy * 1.3 * (1 + 0.05) ** 10:,.0f}"],
    ]
    _add_table(doc, scenario_data)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # PAGE 3: PUE + TECHNICAL DESIGN
    # ══════════════════════════════════════════════════════════════
    _h1(doc, "3. Productive Use of Energy")

    _para(doc,
          f"PUE is the analytical anchor of this PFS. {num_anchors} anchor customer(s) identified, "
          f"contributing {pu_kwh_day:.1f} kWh/day ({pu_demand_pct:.0f}% of load). "
          f"The PUE-led design ensures system sizing and tariff structure are driven by "
          f"productive demand, not residential consumption alone.")

    # Sector assessment (top 5 relevant)
    sectors = _g(productive_use, "sectors") or []
    relevant_sectors = [
        s for s in sectors
        if (s.get("relevance") if isinstance(s, dict) else getattr(s, "relevance", ""))
        in ("high", "medium")
    ][:6]

    if relevant_sectors:
        _caption(doc, "Table 5: Key PUE sectors")
        sec_table = [["Sector", "Relevance", "Est. Demand (kWh/day)", "Key Activities"]]
        for sec in relevant_sectors:
            if isinstance(sec, dict):
                activities = sec.get("indicative_activities", [])
                sec_table.append([
                    sec.get("sector", ""),
                    sec.get("relevance", "").title(),
                    f"{sec.get('estimated_demand_kwh_day', 0):.1f}",
                    "; ".join(activities[:3]) if activities else sec.get("rationale", "")[:60],
                ])
            else:
                activities = getattr(sec, "indicative_activities", [])
                sec_table.append([
                    getattr(sec, "sector", ""),
                    getattr(sec, "relevance", "").title(),
                    f"{getattr(sec, 'estimated_demand_kwh_day', 0):.1f}",
                    "; ".join(activities[:3]) if activities else getattr(sec, "rationale", "")[:60],
                ])
        _add_table(doc, sec_table)

    # Anchor customers
    anchors = _g(productive_use, "anchors") or []
    if anchors:
        _caption(doc, "Table 6: Anchor load pipeline")
        anchor_table = [["Type", "Name", "Demand (kWh/d)", "Peak (kW)", "Confidence"]]
        for ac in anchors[:6]:
            if isinstance(ac, dict):
                anchor_table.append([
                    ac.get("type", ""), ac.get("name", ""),
                    f"{ac.get('estimated_demand_kwh_day', 0):.1f}",
                    f"{ac.get('estimated_peak_kw', 0):.1f}",
                    ac.get("confidence", "D").upper(),
                ])
            else:
                anchor_table.append([
                    getattr(ac, "type", ""), getattr(ac, "name", ""),
                    f"{getattr(ac, 'estimated_demand_kwh_day', 0):.1f}",
                    f"{getattr(ac, 'estimated_peak_kw', 0):.1f}",
                    getattr(ac, "confidence", "D").upper(),
                ])
        _add_table(doc, anchor_table)

    # Jobs & income
    jobs = _g(productive_use, "jobs") or {}
    income = _g(productive_use, "incremental_income_usd_year") or 0
    if jobs or income:
        direct = _g(jobs, "direct") or _g(jobs, "direct_jobs") or 0
        indirect = _g(jobs, "indirect") or _g(jobs, "indirect_jobs") or 0
        _para(doc,
              f"Estimated impact: {direct + indirect:.0f} jobs (direct + indirect), "
              f"USD {income:,.0f}/year incremental income from productive activities.",
              italic=True, size=9, color=_SLATE)

    # ── Technical Design ─────────────────────────────────────────
    _h1(doc, "4. Technical Design")

    ann_gen_mwh = ann_gen_kwh / 1000
    battery_nom = _g(sizing, "battery_kwh_nominal") or 0
    lv_km = _g(sizing, "lv_line_km") or 0
    capacity_factor = _g(sizing, "capacity_factor_pct") or 0
    curtailment = _g(sizing, "curtailment_pct") or 0
    customers = _g(distribution, "customers_connected") or households
    pole_count = _g(distribution, "pole_count") or 0
    vdrop = _g(distribution, "voltage_drop_max_pct") or 0
    losses = _g(distribution, "technical_losses_pct") or 0

    _para(doc,
          f"The system is designed as a {pv_kwp:.0f} kWp isolated solar PV mini-grid with "
          f"{battery_kwh:.0f} kWh usable lithium-ion battery storage and a {inverter_kva:.0f} kVA "
          f"hybrid inverter. Annual generation: {ann_gen_mwh:.0f} MWh with {unmet_pct:.1f}% "
          f"unmet demand. Distribution: {lv_km:.1f} km LV network, {pole_count} poles, "
          f"{customers} connections.")

    _caption(doc, "Table 7: System design summary")
    tech_data = [
        ["Component", "Specification", "Component", "Specification"],
        ["PV Array", f"{pv_kwp:.0f} kWp fixed-tilt",
         "LV Network", f"{lv_km:.1f} km ({pole_count} poles)"],
        ["Battery", f"{battery_kwh:.0f} kWh usable / {battery_nom:.0f} kWh nominal",
         "Voltage Drop", f"{vdrop:.1f}%"],
        ["Inverter", f"{inverter_kva:.0f} kVA hybrid",
         "Tech. Losses", f"{losses:.1f}%"],
        ["Annual Gen.", f"{ann_gen_mwh:.0f} MWh/yr",
         "Connections", f"{customers:,}"],
        ["Capacity Factor", f"{capacity_factor:.1f}%",
         "Dist. Cost/Conn.", _usd(dist_per_conn)],
        ["Unmet Demand", f"{unmet_pct:.1f}%",
         "Network Cost", _usd(dist_cost)],
    ]
    _add_table(doc, tech_data)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # PAGE 4: FINANCIAL SUMMARY
    # ══════════════════════════════════════════════════════════════
    _h1(doc, "5. Financial Summary")

    # CAPEX breakdown
    capex_bk = _g(financial, "capex_breakdown") or {}
    pv_capex = _g(capex_bk, "pv") or 0
    batt_capex = _g(capex_bk, "battery") or 0
    inv_capex = _g(capex_bk, "inverter") or 0
    dist_capex = _g(capex_bk, "distribution") or 0
    meters_capex = _g(capex_bk, "meters") or 0
    install_capex = _g(capex_bk, "installation") or 0
    soft_capex = _g(capex_bk, "soft_costs") or 0
    other_capex = total_capex - (pv_capex + batt_capex + inv_capex + dist_capex + meters_capex + install_capex + soft_capex)

    _caption(doc, "Table 8: CAPEX breakdown")
    capex_data = [
        ["Component", "Amount (USD)", "% of Total"],
        ["Solar PV", _usd(pv_capex), f"{pv_capex / max(total_capex, 1) * 100:.0f}%"],
        ["Battery Storage", _usd(batt_capex), f"{batt_capex / max(total_capex, 1) * 100:.0f}%"],
        ["Inverter/BOS", _usd(inv_capex), f"{inv_capex / max(total_capex, 1) * 100:.0f}%"],
        ["Distribution", _usd(dist_capex), f"{dist_capex / max(total_capex, 1) * 100:.0f}%"],
        ["Meters", _usd(meters_capex), f"{meters_capex / max(total_capex, 1) * 100:.0f}%"],
        ["Installation", _usd(install_capex), f"{install_capex / max(total_capex, 1) * 100:.0f}%"],
        ["Soft Costs / Other", _usd(soft_capex + max(other_capex, 0)),
         f"{(soft_capex + max(other_capex, 0)) / max(total_capex, 1) * 100:.0f}%"],
        ["TOTAL CAPEX", _usd(total_capex), "100%"],
    ]
    _add_table(doc, capex_data)

    # Key financial metrics
    _caption(doc, "Table 9: Financial returns")
    grant = _g(financial, "grant_amount_usd") or 0
    debt = _g(financial, "debt_amount_usd") or 0
    equity = _g(financial, "equity_amount_usd") or 0
    annual_rev = _g(financial, "annual_revenue_usd") or 0

    fin_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Project IRR", f"{irr:.1f}%", "LCOE", _usd_kwh(lcoe)],
        ["NPV (8% disc.)", _usd(npv), "DSCR", f"{dscr:.2f}x"],
        ["Payback", f"{payback:.1f} years",
         "Cost-Reflective Tariff", _usd_kwh(cost_reflective)],
        ["Annual Revenue", _usd(annual_rev), "Affordable Tariff", _usd_kwh(affordable_tariff)],
        ["Annual OPEX", _usd(annual_opex), "Subsidy Gap", f"{subsidy_gap_pct:.0f}% ({_usd(subsidy_gap_total)})"],
    ]
    _add_table(doc, fin_data)

    # Financing structure
    if grant or debt or equity:
        _caption(doc, "Table 10: Indicative financing structure")
        fin_struct = [
            ["Source", "Amount (USD)", "% of CAPEX"],
            ["Grant / RBF", _usd(grant), f"{grant / max(total_capex, 1) * 100:.0f}%"],
            ["Debt", _usd(debt), f"{debt / max(total_capex, 1) * 100:.0f}%"],
            ["Equity", _usd(equity), f"{equity / max(total_capex, 1) * 100:.0f}%"],
            ["Total", _usd(grant + debt + equity), "100%"],
        ]
        _add_table(doc, fin_struct)

    # Sensitivity
    sensitivity = _g(financial, "sensitivity") or []
    if sensitivity:
        _caption(doc, "Table 11: Sensitivity analysis (IRR impact)")
        sens_data = [["Parameter", "Low", "Base", "High", "IRR Low", "IRR Base", "IRR High"]]
        for s in sensitivity[:5]:
            if isinstance(s, dict):
                sens_data.append([
                    s.get("parameter", ""),
                    f"{s.get('low_value', 0):.2f}", f"{s.get('base_value', 0):.2f}",
                    f"{s.get('high_value', 0):.2f}",
                    f"{s.get('irr_at_low', 0):.1f}%", f"{s.get('irr_at_base', 0):.1f}%",
                    f"{s.get('irr_at_high', 0):.1f}%",
                ])
            else:
                sens_data.append([
                    getattr(s, "parameter", ""),
                    f"{getattr(s, 'low_value', 0):.2f}", f"{getattr(s, 'base_value', 0):.2f}",
                    f"{getattr(s, 'high_value', 0):.2f}",
                    f"{getattr(s, 'irr_at_low', 0):.1f}%", f"{getattr(s, 'irr_at_base', 0):.1f}%",
                    f"{getattr(s, 'irr_at_high', 0):.1f}%",
                ])
        _add_table(doc, sens_data, small=True)

    # Carbon revenue
    ann_cer = _g(carbon, "annual_emission_reductions_tco2e") or 0
    total_cer = _g(carbon, "total_eligible_tco2e") or 0
    carbon_rev = _g(carbon, "revenue_by_scenario") or {}
    if ann_cer > 0:
        mid_rev = carbon_rev.get("mid") or carbon_rev.get("base") or 0
        _para(doc,
              f"Carbon revenue: {ann_cer:.0f} tCO2e/yr ({total_cer:,.0f} total over crediting "
              f"period). Estimated revenue: {_usd(mid_rev)} over crediting period (mid-scenario).",
              italic=True, size=9, color=_SLATE)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # PAGE 5: RISKS + RECOMMENDATION + NEXT STEPS
    # ══════════════════════════════════════════════════════════════
    _h1(doc, "6. Key Risks")

    risks = _g(risk_analysis, "risks") or []
    top_risks = [r for r in risks
                 if (r.get("risk_level") if isinstance(r, dict) else getattr(r, "risk_level", ""))
                 in ("critical", "high")][:6]

    if top_risks:
        _caption(doc, "Table 12: Critical and high risks")
        risk_table = [["Risk", "Category", "L x I", "Level", "Mitigation"]]
        for r in top_risks:
            if isinstance(r, dict):
                mits = r.get("mitigation", [])
                risk_table.append([
                    r.get("sub_risk", ""),
                    r.get("category", "").title(),
                    f"{r.get('likelihood', 0)} x {r.get('impact', 0)}",
                    r.get("risk_level", "").upper(),
                    mits[0] if mits else "--",
                ])
            else:
                mits = getattr(r, "mitigation", [])
                risk_table.append([
                    getattr(r, "sub_risk", ""),
                    getattr(r, "category", "").title(),
                    f"{getattr(r, 'likelihood', 0)} x {getattr(r, 'impact', 0)}",
                    getattr(r, "risk_level", "").upper(),
                    mits[0] if mits else "--",
                ])
        _add_table(doc, risk_table, small=True)
    else:
        _para(doc, "No critical or high risks identified at desktop screening stage. "
                   "Full risk assessment required during feasibility phase.",
              italic=True, color=_GREY)

    # Grid arrival risk
    _h2(doc, "Grid Arrival Risk")
    _para(doc,
          f"Distance to MV grid: {dist_mv:.1f} km. Grid risk level: "
          f"{(_g(grid_risk, 'risk_level') or 'unknown').upper()}. "
          f"{_g(grid_risk, 'risk_label') or 'Assessment required.'}",
          size=9)

    # ESS summary
    esia_cat = _g(ess, "esia_category") or "--"
    ess_risk = _g(ess, "overall_ess_risk") or "unknown"
    _h2(doc, "Environmental & Social")
    _para(doc,
          f"ESIA category: {esia_cat}. Overall E&S risk: {ess_risk.upper()}. "
          f"{_g(ess, 'esia_rationale') or ''}",
          size=9)

    # Climate
    hazard_level = _g(climate, "overall_hazard_level") or "unknown"
    lifetime_co2 = _g(climate, "lifetime_avoided_tco2e") or 0
    _h2(doc, "Climate")
    _para(doc,
          f"Overall hazard level: {hazard_level.upper()}. "
          f"Lifetime avoided emissions: {lifetime_co2:,.0f} tCO2e. "
          f"NDC alignment: {(_g(climate, 'ndc_alignment') or 'Mozambique renewable energy targets')[:100]}.",
          size=9)

    # Confidence
    overall_conf = _g(confidence, "overall_confidence_score") or 0
    conf_level = _g(confidence, "overall_confidence_level") or "unknown"
    data_completeness = _g(confidence, "data_completeness_pct") or 0
    _h2(doc, "Data Confidence")
    _para(doc,
          f"Overall confidence: {overall_conf}/100 ({conf_level.upper()}). "
          f"Data completeness: {data_completeness:.0f}%. "
          f"Key gaps: demand survey, anchor contracts, land tenure.",
          size=9)

    # ── Recommendation ───────────────────────────────────────────
    _h1(doc, "7. Recommendation")

    p = doc.add_paragraph()
    run = p.add_run(recommendation)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = rec_color

    if irr > 0 and payback < 25:
        _para(doc,
              f"{site_name} is a credible candidate for a PUE-led isolated mini-grid concession. "
              f"The project should advance to full feasibility, with priority focus on: "
              f"(i) household demand survey and willingness-to-pay assessment; "
              f"(ii) anchor customer verification and pre-contractual engagement; "
              f"(iii) site micro-siting, land tenure, and environmental screening; "
              f"(iv) confirmation of off-grid designation with ARENE/FUNAE.")
    else:
        _para(doc,
              f"{site_name} requires significant blended finance to achieve viability. "
              f"The project should be structured with grant/RBF support from the outset. "
              f"Clustering with nearby settlements may improve unit economics. "
              f"Field validation is essential before committing capital.")

    _h2(doc, "Next Steps")
    _bullet(doc, "Commission field demand survey and willingness-to-pay study")
    _bullet(doc, "Engage potential anchor customers for pre-contractual discussions")
    _bullet(doc, "Conduct site micro-siting and land acquisition assessment")
    _bullet(doc, "Verify off-grid designation with ARENE / FUNAE")
    _bullet(doc, "Prepare full feasibility study with bankable financial model")
    _bullet(doc, "Initiate environmental and social due diligence (ESIA)")

    # Footer
    _blank(doc)
    _para(doc,
          "This executive summary is extracted from the full Pre-Feasibility Study. "
          "All figures are desktop estimates requiring field validation. "
          "This document does not constitute an investment recommendation.",
          italic=True, size=8, color=_GREY)
    _para(doc,
          f"Generated: {today.strftime('%Y-%m-%d')} | Moz Mini-Grid Platform | PUE-Led Methodology",
          italic=True, size=8, color=_GREY)

    # ── Save ─────────────────────────────────────────────────────
    doc.save(output_path)
    return output_path
