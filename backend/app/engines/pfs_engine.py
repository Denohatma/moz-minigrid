from __future__ import annotations

import math
from datetime import date
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import io

from app.schemas.analysis import AnalysisResult


def generate_pfs_docx(result: AnalysisResult) -> bytes:
    doc = Document()
    _set_default_style(doc)

    r = result
    f = r.financial
    s = r.sizing
    d = r.demand
    gr = r.grid_risk
    cl = r.cluster
    sol = r.solar_resource
    dist = r.distribution
    carb = r.carbon

    site_name = cl.village_name or r.site.name or "Unnamed"
    province = cl.admin_region or "Unknown"
    district = cl.admin_district or "Unknown"
    urban_label = ["Rural", "Peri-urban", "Urban"][min(cl.is_urban, 2)]
    pv_kwp = s.pv_kwp
    today = date.today()
    month_year = today.strftime("%B %Y")

    # ── Title Page ──────────────────────────────────────────────
    _add_blank_lines(doc, 4)
    _add_centered(doc, "PRE-FEASIBILITY STUDY", bold=True, size=24, color=RGBColor(0x2F, 0x85, 0x5A))
    _add_centered(doc, f"{site_name.upper()} {pv_kwp:.0f} kWp SOLAR PV MINI-GRID",
                  bold=True, size=18, color=RGBColor(0x1A, 0x20, 0x2C))
    _add_centered(doc, f"{district}, {province}, Mozambique", size=14, color=RGBColor(0x4A, 0x55, 0x68))
    _add_blank_lines(doc, 3)
    _add_centered(doc, "CONFIDENTIAL — DRAFT FOR REVIEW", bold=True, size=11, color=RGBColor(0xC5, 0x3D, 0x3D))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "This document is a desktop pre-feasibility study prepared for early project screening purposes only. "
        "It does not constitute a bankable feasibility study, investment recommendation, or engineering design."
    )
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

    doc.add_page_break()

    # ── 1. Executive Summary ────────────────────────────────────
    _h1(doc, "1. Executive Summary")

    _h2(doc, "Project Overview")
    ann_gen_mwh = (s.annual_generation_kwh or 0) / 1000
    doc.add_paragraph(
        f"The {site_name} {pv_kwp:.0f} kWp Solar PV Mini-Grid is a proposed rural electrification project "
        f"located in {site_name}, {district}, {province}, Mozambique, "
        f"centred at approximately {r.site.latitude:.4f}°S, {r.site.longitude:.4f}°E. "
        f"This pre-feasibility study assesses whether the project warrants advancement to full feasibility "
        f"as an isolated solar PV mini-grid designed to supply first-time utility-level electricity access "
        f"to {'an unelectrified' if not cl.has_nightlight else 'a partially electrified'} settlement "
        f"with {d.households} estimated connections."
    )

    _h2(doc, "Technical Concept")
    inv_kwac = s.inverter_kva * 0.85
    dc_ac = s.dc_ac_ratio or round(pv_kwp / inv_kwac, 1)
    batt_usable = s.battery_kwh_usable
    pr = sol.performance_ratio if sol else 0.77
    spec_yield = sol.specific_yield_kwh_per_kwp if sol else 0
    doc.add_paragraph(
        f"The preferred technical concept is a {pv_kwp:.0f} kWp DC ground-mounted solar PV plant with "
        f"approximately {inv_kwac:.0f} kWac conversion capacity (DC/AC ratio of ~{dc_ac:.1f}), "
        f"battery storage of {batt_usable:.0f} kWh usable capacity, and a low-voltage local distribution "
        f"network. Module technology is expected to be monocrystalline mono-PERC or TOPCon on fixed-tilt "
        f"mounting. Indicative annual gross generation is approximately {ann_gen_mwh:.1f} MWh/year at a "
        f"central specific yield of {spec_yield:,.0f} kWh/kWp/year, with a performance ratio of "
        f"{pr:.2f}. Solar yield estimates are derived from PVGIS 5.3 satellite-based data."
    )

    _h2(doc, "Financial Summary")
    _h3(doc, f"Table ES-1: Key financial screening metrics — {site_name} {pv_kwp:.0f} kWp Mini-Grid")
    es_data = [
        ["Metric", "Screening Value"],
        ["Total CAPEX", f"~USD {f.total_capex_usd:,.0f} (USD {f.capex_per_wp:.2f}/Wp)"],
        ["Annual OPEX", f"USD {f.annual_opex_usd:,.0f}/year"],
        ["Annual Energy Sold (est.)", f"~{(s.annual_energy_served_kwh or d.annual_energy_kwh) / 1000:.0f} MWh/year"],
        ["Average Realised Tariff", f"USD {f.affordable_tariff_usd:.2f}/kWh"],
        ["Year 1 Gross Revenue (est.)", f"~USD {f.annual_revenue_usd:,.0f}/year"],
        ["Project IRR", f"{f.irr_pct:.1f}%"],
        ["Equity IRR", f"{f.equity_irr_pct:.1f}%" if f.equity_irr_pct else "—"],
        ["LCOE", f"USD {f.lcoe_usd_kwh:.4f}/kWh"],
        ["Simple Payback", f"{f.payback_years:.1f} years"],
        ["Min DSCR", f"{f.dscr:.2f}"],
    ]
    _add_table(doc, es_data)

    _h2(doc, "Key Risks and Opportunities")
    doc.add_paragraph(
        f"The primary project risks are demand and affordability uncertainty, climate resilience exposure, "
        f"and capital cost uncertainty. Grid-interface risk is classified as {gr.risk_level} "
        f"based on MV grid distance of {gr.dist_mv_km:.1f} km. "
        f"Key opportunities include strong social-impact value for "
        f"{'an unelectrified' if not cl.has_nightlight else 'a partially electrified'} community "
        f"{'with education and health facilities' if cl.has_education_facility or cl.has_health_facility else ''}"
        f"{', and productive-use demand potential through ' + cl.crop_types if cl.crop_types else ''}."
    )

    _h2(doc, "Recommendation")
    viable = f.irr_pct > 0 and f.payback_years < 25
    if viable:
        rec = "CONDITIONAL GO"
        rec_text = (
            f"{site_name} is a credible rural electrification opportunity. "
            f"The project should advance to full feasibility, prioritising: "
            f"(i) a demand and willingness-to-pay survey; (ii) site micro-siting confirmation; "
            f"(iii) land verification and DUAT pathway engagement; and "
            f"(iv) confirmation of the off-grid designation with ARENE/FUNAE."
        )
    else:
        rec = "CONDITIONAL GO — BLENDED FINANCE REQUIRED"
        rec_text = (
            f"{site_name} presents a credible rural electrification opportunity, but the project "
            f"is not financially viable without concessional capital or grant support. "
            f"The project should be structured as a blended-finance investment from the outset, "
            f"targeting DFI funding, results-based finance, or climate access facilities."
        )
    p = doc.add_paragraph()
    run = p.add_run(f"RECOMMENDED DECISION: {rec}")
    run.bold = True
    doc.add_paragraph(rec_text)

    doc.add_page_break()

    # ── 2. Introduction ─────────────────────────────────────────
    _h1(doc, "2. Introduction")

    _h2(doc, "2.1 Project Overview")
    doc.add_paragraph(
        f"The {site_name} {pv_kwp:.0f} kWp Solar PV Mini-Grid is a proposed rural electrification "
        f"project for {site_name} in {district}, {province}, Mozambique. "
        f"The project concept is a {pv_kwp:.0f} kWp solar photovoltaic mini-grid intended to serve "
        f"{'an unelectrified' if not cl.has_nightlight else 'a partially electrified'} settlement "
        f"with {d.households} potential connections and an estimated daily demand of "
        f"{d.daily_energy_kwh:.0f} kWh. The project is classified as a mini-grid rather than a "
        f"grid-connected independent power producer."
    )

    _h2(doc, "2.2 Study Objectives")
    doc.add_paragraph(
        "This pre-feasibility study is prepared as an early-stage desktop assessment of whether "
        f"the {site_name} project warrants advancement to full feasibility. Key questions addressed include:"
    )
    for obj in [
        f"Whether {site_name} presents a credible mini-grid opportunity based on available demand anchors and solar resource",
        "Whether land appears available for development without obvious exclusionary constraints",
        "Whether demand anchors exist to support utilisation over time",
        "Which regulatory and delivery risks are most likely to shape the project pathway",
        "What conditions must be satisfied to advance the project to full feasibility",
    ]:
        doc.add_paragraph(obj, style="List Bullet")

    _h2(doc, "2.3 Study Limitations")
    doc.add_paragraph(
        "This document is explicitly a desktop pre-feasibility study and not a bankable feasibility study. "
        "It relies on secondary research, curated project datasets (World Bank DRE Atlas), and "
        "screening-level assumptions rather than field-verified survey results. "
        "This study does not include detailed engineering design, geotechnical investigations, "
        "measured solar resource assessment, environmental and social impact assessment, "
        "a bankable financial model, or legally verified permitting opinions."
    )

    doc.add_page_break()

    # ── 3. Site Description and Location ────────────────────────
    _h1(doc, "3. Site Description and Location")

    _h2(doc, "3.1 Geographic Location")
    doc.add_paragraph(
        f"The proposed solar mini-grid site is located at {site_name} in {district}, {province}, "
        f"Mozambique. The reference site centroid is taken as {r.site.latitude:.4f}°S, "
        f"{r.site.longitude:.4f}°E (WGS84), consistent with the World Bank DRE Atlas dataset."
    )
    _h3(doc, "Table 3-1: Site location summary")
    loc_data = [
        ["Parameter", "Value", "Note"],
        ["Settlement", site_name, "Project service area"],
        ["District", district, "Administrative area"],
        ["Province", province, "Administrative area"],
        ["Reference Latitude", f"{r.site.latitude:.4f}°", "WGS84"],
        ["Reference Longitude", f"{r.site.longitude:.4f}°", "WGS84"],
        ["Population", f"{cl.population:,}", "DRE Atlas"],
        ["Buildings", f"{cl.num_buildings:,}" if cl.num_buildings else "—", "DRE Atlas"],
        ["Area", f"{cl.area_km2:.3f} km²", "DRE Atlas"],
        ["Classification", urban_label, "DRE Atlas"],
        ["Electricity Access", "Yes (partial)" if cl.has_nightlight else "None (unelectrified)", "Nightlight proxy"],
    ]
    _add_table(doc, loc_data)

    _h2(doc, "3.2 Access and Infrastructure")
    _h3(doc, "Table 3-2: Infrastructure status summary")
    infra_data = [
        ["Infrastructure Item", "Status", "Implication"],
        ["Road access", f"{cl.dist_road_km:.1f} km to main road" + (" (access)" if getattr(cl, 'main_road_access', False) else ""), "Logistics planning required"],
        ["MV Grid", f"{cl.dist_grid_mv_km:.1f} km", "No grid connection currently"],
        ["Planned Grid", f"{cl.dist_grid_planned_km:.1f} km" if cl.dist_grid_planned_km else "Not confirmed", "Requires EDM verification"],
    ]
    if cl.nearest_hub_name:
        infra_data.append(["Nearest hub", f"{cl.nearest_hub_name} ({cl.dist_nearest_hub_km:.0f} km)" if cl.dist_nearest_hub_km else cl.nearest_hub_name, "Transport hub"])
    _add_table(doc, infra_data)

    doc.add_page_break()

    # ── 4. Solar Resource Assessment ────────────────────────────
    _h1(doc, "4. Solar Resource Assessment")

    _h2(doc, "4.1 Global Horizontal Irradiance (GHI)")
    ghi = sol.annual_ghi_kwh_m2 if sol else cl.ghi_kwh_m2_year
    ghi_source = sol.data_source if sol else "DRE Atlas"
    doc.add_paragraph(
        f"{site_name} benefits from a strong solar resource. Using data from {ghi_source}, "
        f"the annual GHI is assessed at approximately {ghi:,.0f} kWh/m²/year. "
        f"This indicates a viable solar resource for a fixed-tilt PV mini-grid."
    )

    if sol and sol.monthly_ghi_kwh_m2:
        _h3(doc, "Table 4-1: Monthly GHI profile")
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        ghi_table = [["Month", "GHI (kWh/m²/month)"]]
        for i, m in enumerate(months):
            ghi_table.append([m, f"{sol.monthly_ghi_kwh_m2[i]:.1f}"])
        ghi_table.append(["Annual Total", f"~{ghi:,.0f} kWh/m²/yr"])
        _add_table(doc, ghi_table)

    _h2(doc, "4.2 Performance Ratio and Loss Assumptions")
    doc.add_paragraph(
        f"A screening-level performance ratio of {pr:.2f} is adopted. "
        f"The main expected losses include:"
    )
    if sol and sol.loss_breakdown:
        _h3(doc, "Table 4-2: Pre-feasibility loss assumptions")
        loss_table = [["Loss Category", "Screening Value", "Note"]]
        loss_names = {
            "temperature": ("Temperature losses", "Warm tropical climate"),
            "soiling": ("Soiling losses", "Panel cleaning programme needed"),
            "wiring": ("Wiring and mismatch", "Standard allowance"),
            "inverter": ("Inverter conversion", "Hybrid inverter basis"),
            "battery_dispatch": ("Battery / control losses", "Depends on cycling depth"),
            "availability": ("Availability losses", "Access disruption risk"),
            "degradation_y1": ("Year 1 degradation / LID", "0.5%/year ongoing"),
        }
        for key, (label, note) in loss_names.items():
            val = sol.loss_breakdown.get(key, 0)
            loss_table.append([label, f"{val*100:.1f}%", note])
        _add_table(doc, loss_table)

    doc.add_page_break()

    # ── 5. Energy Demand and Market Analysis ────────────────────
    _h1(doc, "5. Energy Demand and Market Analysis")

    _h2(doc, "5.1 Settlement Profile and Demand")
    doc.add_paragraph(
        f"The settlement profile and demand estimates are derived from the World Bank DRE Atlas "
        f"for Mozambique. The available data indicates {d.households} potential customer connections "
        f"with an MTF demand Tier {d.demand_tier} classification."
    )
    _h3(doc, "Table 5-1: Settlement and demand profile")
    demand_table = [
        ["Category", "Value", "Source"],
        ["Population", f"{cl.population:,}", "DRE Atlas"],
        ["Mapped structures", f"{cl.num_buildings:,}" if cl.num_buildings else "—", "DRE Atlas"],
        ["Estimated connections", f"{d.households:,}", "Model estimate"],
        ["Daily energy demand", f"{d.daily_energy_kwh:.1f} kWh/day", "Model estimate"],
        ["Annual energy demand", f"{d.annual_energy_kwh:,.0f} kWh/yr", "Model estimate"],
        ["Peak demand", f"{d.peak_demand_kw:.1f} kW", "Model estimate"],
        ["Demand tier (MTF)", f"Tier {d.demand_tier}", "Model classification"],
        ["Persons per household", f"{d.persons_per_hh}", "Country default"],
    ]
    if cl.has_education_facility:
        demand_table.append(["Education facilities", f"{cl.num_education_facilities or 1}", "DRE Atlas"])
    if cl.has_health_facility:
        demand_table.append(["Health facilities", f"{cl.num_health_facilities or 1}", "DRE Atlas"])
    _add_table(doc, demand_table)

    _h2(doc, "5.2 Tariff and Regulatory Context")
    doc.add_paragraph(
        "For an isolated mini-grid in Mozambique, the most relevant commercial framework is ARENE's "
        "cost-reflective tariff regime for rural electricity service under Decree 93/2021. "
        f"The cost-reflective tariff is estimated at USD {f.cost_reflective_tariff_usd:.4f}/kWh, "
        f"while the affordable tariff assumption is USD {f.affordable_tariff_usd:.2f}/kWh."
    )

    doc.add_page_break()

    # ── 6. Technical Design Concept ─────────────────────────────
    _h1(doc, "6. Technical Design Concept")

    _h2(doc, "6.1 Technology Selection")
    doc.add_paragraph(
        f"The preferred technical concept is a fixed-tilt solar PV mini-grid with battery storage "
        f"and low-voltage local distribution, auto-sized to meet the estimated settlement demand of "
        f"{d.daily_energy_kwh:.0f} kWh/day. Battery storage is required to serve evening and "
        f"overnight demand."
    )

    _h2(doc, "6.2 System Configuration and Sizing")
    _h3(doc, "Table 6-1: System configuration and sizing parameters")
    sizing_table = [
        ["Parameter", "Value", "Note"],
        ["Installed DC Capacity", f"{pv_kwp:.1f} kWp", "Auto-sized to meet demand"],
        ["AC Conversion Capacity", f"~{inv_kwac:.0f} kWac", "Inverter rating"],
        ["DC/AC Ratio", f"~{dc_ac:.1f}", ""],
        ["Battery Storage (nominal)", f"{s.battery_kwh_nominal:.0f} kWh", "LFP lithium-ion"],
        ["Battery Storage (usable)", f"{batt_usable:.0f} kWh", "80% DoD"],
        ["Inverter", f"{s.inverter_kva:.1f} kVA", ""],
        ["Degradation Rate", "0.5%/year", "Standard assumption"],
    ]
    _add_table(doc, sizing_table)

    _h2(doc, "6.3 Energy Yield Estimate")
    doc.add_paragraph(
        f"Using an 8,760-hour dispatch simulation with hourly solar irradiance from PVGIS 5.3 "
        f"and the estimated load profile, the system is expected to generate approximately "
        f"{ann_gen_mwh:.1f} MWh/year gross, serving {(s.annual_energy_served_kwh or 0)/1000:.1f} MWh/year "
        f"of demand with {s.unmet_energy_pct:.1f}% unmet energy and "
        f"{s.curtailment_pct:.1f}% curtailment."
    )

    _h3(doc, "Table 6-2: Dispatch simulation results")
    dispatch_table = [
        ["Parameter", "Value"],
        ["Annual gross generation", f"{ann_gen_mwh:.1f} MWh/year"],
        ["Annual energy served", f"{(s.annual_energy_served_kwh or 0)/1000:.1f} MWh/year"],
        ["Unmet energy", f"{s.unmet_energy_pct:.1f}%"],
        ["Curtailment", f"{s.curtailment_pct:.1f}%"],
        ["Capacity factor", f"{s.capacity_factor_pct:.1f}%"],
        ["Battery cycles per year", f"{s.battery_cycles_per_year:.0f}"],
    ]
    _add_table(doc, dispatch_table)

    if dist:
        _h2(doc, "6.4 Distribution Network")
        doc.add_paragraph(
            f"The low-voltage distribution network is estimated using a radial model. "
            f"Total line length is {dist.total_line_length_m:,.0f} m with {dist.pole_count} poles "
            f"serving {dist.customers_connected} connections. Estimated maximum voltage drop is "
            f"{dist.voltage_drop_max_pct:.1f}% and technical losses are {dist.technical_losses_pct:.1f}%."
        )
        _h3(doc, "Table 6-3: Distribution network summary")
        dist_table = [
            ["Parameter", "Value"],
            ["Total line length", f"{dist.total_line_length_m:,.0f} m"],
            ["Pole count", f"{dist.pole_count}"],
            ["Customers connected", f"{dist.customers_connected}"],
            ["Network cost", f"USD {dist.total_network_cost_usd:,.0f}"],
            ["Cost per connection", f"USD {dist.cost_per_connection_usd:,.0f}"],
            ["Max voltage drop", f"{dist.voltage_drop_max_pct:.1f}%"],
            ["Technical losses", f"{dist.technical_losses_pct:.1f}%"],
        ]
        _add_table(doc, dist_table)

    doc.add_page_break()

    # ── 7. Regulatory and Permitting Framework ──────────────────
    _h1(doc, "7. Regulatory and Permitting Framework")

    _h2(doc, "7.1 Energy Sector Regulatory Overview")
    doc.add_paragraph(
        "Mozambique's regulatory framework for rural isolated solar mini-grids is governed by "
        "Law No. 11/2017 (establishing ARENE), Law No. 12/2022 (electricity sector), "
        "Decree No. 93/2021 (off-grid and mini-grid access up to 10 MW), and the 2023 mini-grid "
        "concession award regulation."
    )
    _h3(doc, "Table 7-1: Key regulatory institutions")
    reg_table = [
        ["Institution", "Role", "Relevance"],
        ["MIREME", "Sector ministry and concession-granting authority", "Provides formal policy backbone"],
        ["ARENE", "Energy regulator — tariff review, compliance", "Approves tariff methodology"],
        ["FUNAE", "Public off-grid and rural electrification agency", "Rural programme alignment"],
        ["EDM", "National utility — grid planning", "Confirms grid rollout plans"],
    ]
    _add_table(doc, reg_table)

    _h2(doc, "7.2 Indicative Permitting Timeline")
    doc.add_paragraph(
        f"The indicative permitting duration for {site_name} is 6–15 months, with variation driven "
        f"by DUAT complexity, environmental categorisation, and review speed."
    )

    doc.add_page_break()

    # ── 8. Environmental and Social Screening ───────────────────
    _h1(doc, "8. Environmental and Social Screening")

    _h2(doc, "8.1 Environmental Screening")
    suitable = r.screening.is_suitable
    doc.add_paragraph(
        f"Desktop land screening for the proposed {site_name} mini-grid indicates "
        f"{'low overall land risk and suitability for development' if suitable else 'potential concerns requiring further investigation'}. "
    )
    if r.screening.warnings:
        for w in r.screening.warnings:
            doc.add_paragraph(f"• {w.message}")

    _h2(doc, "8.2 Preliminary E&S Risk Classification")
    doc.add_paragraph(
        f"On a pre-feasibility basis, the {site_name} mini-grid is best classified as a "
        f"Category B / moderate risk project under an IFC-style framework."
    )

    doc.add_page_break()

    # ── 9. Financial Analysis ───────────────────────────────────
    _h1(doc, "9. Financial Analysis")

    _h2(doc, "9.1 Capital Expenditure (CAPEX)")
    bk = f.capex_breakdown
    total_capex = f.total_capex_usd
    doc.add_paragraph(
        f"The total project CAPEX is estimated at USD {total_capex:,.0f}, corresponding to "
        f"USD {f.capex_per_wp:.2f}/Wp on a PV-nameplate basis."
    )
    _h3(doc, "Table 9-1: Indicative CAPEX breakdown")
    capex_table = [
        ["Component", "USD", "USD/Wp", "% of Total"],
        ["PV modules + mounting + BOS", f"{bk.pv:,.0f}", f"{bk.pv / (pv_kwp * 1000):.2f}", f"{bk.pv/total_capex*100:.1f}%"],
        ["Battery storage and EMS", f"{bk.battery:,.0f}", f"{bk.battery / (pv_kwp * 1000):.2f}", f"{bk.battery/total_capex*100:.1f}%"],
        ["Inverters and power electronics", f"{bk.inverter:,.0f}", f"{bk.inverter / (pv_kwp * 1000):.2f}", f"{bk.inverter/total_capex*100:.1f}%"],
        ["Distribution network", f"{bk.distribution:,.0f}", f"{bk.distribution / (pv_kwp * 1000):.2f}", f"{bk.distribution/total_capex*100:.1f}%"],
        ["Installation + civil", f"{bk.installation:,.0f}", f"{bk.installation / (pv_kwp * 1000):.2f}", f"{bk.installation/total_capex*100:.1f}%"],
        ["Contingency + soft costs", f"{bk.soft_costs:,.0f}", f"{bk.soft_costs / (pv_kwp * 1000):.2f}", f"{bk.soft_costs/total_capex*100:.1f}%"],
        ["Total CAPEX", f"{total_capex:,.0f}", f"{f.capex_per_wp:.2f}", "100%"],
    ]
    _add_table(doc, capex_table)

    _h2(doc, "9.2 Operating Expenditure (OPEX)")
    opex = f.opex_breakdown
    if opex:
        _h3(doc, "Table 9-2: Indicative annual OPEX breakdown")
        opex_table = [
            ["OPEX Category", "USD/year", "Note"],
            ["Generation O&M", f"{opex.generation_om:,.0f}", f"{opex.generation_om/total_capex*100:.1f}% of gen CAPEX"],
            ["Distribution O&M", f"{opex.distribution_om:,.0f}", "Network maintenance"],
            ["Site security", f"{opex.site_security:,.0f}", "Local hire preferred"],
            ["Remote monitoring", f"{opex.remote_monitoring:,.0f}", "Communications"],
            ["Insurance", f"{opex.insurance:,.0f}", "Asset coverage"],
            ["Total Annual OPEX", f"{f.annual_opex_usd:,.0f}", ""],
        ]
        _add_table(doc, opex_table)

    _h2(doc, "9.3 Revenue Model")
    energy_sold = (s.annual_energy_served_kwh or d.annual_energy_kwh) * 0.92
    doc.add_paragraph(
        f"Using an indicative annual energy sold figure of {energy_sold/1000:.0f} MWh/year "
        f"after losses and demand constraints, and a realised tariff of "
        f"USD {f.affordable_tariff_usd:.2f}/kWh, Year 1 gross revenue would be approximately "
        f"USD {f.annual_revenue_usd:,.0f}/year."
    )

    _h2(doc, "9.4 Key Financial Indicators")
    _h3(doc, "Table 9-3: Indicative financial screening summary")
    fin_table = [
        ["Financial Metric", "Value", "Note"],
        ["Project IRR", f"{f.irr_pct:.1f}%", "Pre-tax, nominal"],
        ["Equity IRR", f"{f.equity_irr_pct:.1f}%" if f.equity_irr_pct else "—", "Under blended finance"],
        ["NPV @ 10% discount", f"USD {f.npv_usd:,.0f}", ""],
        ["LCOE", f"USD {f.lcoe_usd_kwh:.4f}/kWh", "Real"],
        ["Simple payback", f"{f.payback_years:.1f} years", ""],
        ["Min DSCR", f"{f.dscr:.2f}", ""],
        ["Cost-reflective tariff", f"USD {f.cost_reflective_tariff_usd:.4f}/kWh", ""],
        ["Subsidy gap / connection", f"USD {f.subsidy_gap_per_connection_usd:,.0f}", f"{f.subsidy_gap_pct_capex:.0f}% of CAPEX"],
    ]
    _add_table(doc, fin_table)

    _h2(doc, "9.5 Sensitivity Analysis")
    _h3(doc, "Table 9-4: Sensitivity analysis")
    sens_table = [["Variable", "IRR @ Low", "IRR @ Base", "IRR @ High"]]
    for sv in f.sensitivity:
        sens_table.append([sv.parameter, f"{sv.irr_at_low:.1f}%", f"{sv.irr_at_base:.1f}%", f"{sv.irr_at_high:.1f}%"])
    _add_table(doc, sens_table)

    _h2(doc, "9.6 Indicative Financing Structure")
    _h3(doc, "Table 9-5: Indicative blended financing structure")
    fin_struct = [
        ["Financing Component", "Amount (USD)", "Share", "Likely Sources"],
        ["Grant / results-based subsidy", f"{f.grant_amount_usd:,.0f}", f"{f.subsidy_gap_pct_capex:.0f}%",
         "FUNAE, BRILHO, climate funds, bilateral donors"],
        ["Concessional debt", f"{f.debt_amount_usd:,.0f}", "35%",
         "DFIs, green climate fund, rural electrification facilities"],
        ["Developer equity", f"{f.equity_amount_usd:,.0f}", "25%",
         "Project sponsor; may attract impact investors"],
    ]
    _add_table(doc, fin_struct)

    doc.add_page_break()

    # ── 10. Carbon Assessment ───────────────────────────────────
    if carb:
        _h1(doc, "10. Carbon Credit Assessment")
        doc.add_paragraph(
            f"The {site_name} mini-grid displaces diesel generation, enabling carbon credit revenue. "
            f"Annual emission reductions are estimated at {carb.annual_emission_reductions_tco2e:.1f} tCO2e/year, "
            f"displacing {carb.diesel_displaced_litres_yr:,.0f} litres of diesel per year."
        )
        _h3(doc, "Table 10-1: Carbon credit assessment summary")
        carbon_table = [
            ["Parameter", "Value"],
            ["Annual emission reductions", f"{carb.annual_emission_reductions_tco2e:.1f} tCO2e/yr"],
            ["Diesel displaced", f"{carb.diesel_displaced_litres_yr:,.0f} litres/yr"],
            ["Crediting period", f"{carb.crediting_period_years} years"],
            ["Total eligible reductions", f"{carb.total_eligible_tco2e:,.0f} tCO2e"],
            ["Recommended methodology", carb.recommended_methodology],
            ["Alternative methodology", carb.alternative_methodology],
        ]
        _add_table(doc, carbon_table)

        _h3(doc, "Table 10-2: Revenue by price scenario")
        rev_table = [["Scenario", "Annual Revenue (USD)", "NPV (USD)"]]
        for sc, rev in sorted(carb.revenue_by_scenario.items()):
            npv = carb.npv_carbon_revenue.get(sc, 0)
            rev_table.append([sc.replace("_", " ").title(), f"{rev:,.0f}", f"{npv:,.0f}"])
        _add_table(doc, rev_table)

        doc.add_page_break()

    # ── 11. Grid Risk Assessment ────────────────────────────────
    _h1(doc, "11. Grid Risk Assessment")
    doc.add_paragraph(
        f"Grid-interface risk for {site_name} is classified as {gr.risk_level.upper()} "
        f"based on MV grid distance of {gr.dist_mv_km:.1f} km and HV grid distance of "
        f"{gr.dist_hv_km:.1f} km. {gr.risk_label}"
    )
    if gr.esmap_recommended:
        doc.add_paragraph(f"ESMAP recommended strategy: {gr.esmap_recommended}")
    if gr.design_implications:
        doc.add_paragraph(f"Design implications: {gr.design_implications}")

    if gr.esmap_scores:
        _h3(doc, "Table 11-1: ESMAP scenario scoring")
        esmap_table = [["Scenario", "Weighted Score", "Timeline", "Financial", "Regulatory"]]
        for es in gr.esmap_scores:
            esmap_table.append([
                es.label,
                f"{es.weighted_score:.2f}",
                f"{es.timeline_certainty:.2f}",
                f"{es.financial_viability:.2f}",
                f"{es.regulatory_alignment:.2f}",
            ])
        _add_table(doc, esmap_table)

    if gr.scenarios:
        _h3(doc, "Table 11-2: Grid arrival scenarios")
        arrival_table = [["Scenario", "Adjusted IRR", "NPV", "Investment Recovered"]]
        for sc in gr.scenarios:
            arrival_table.append([
                f"Grid at Year {sc.arrival_year}",
                f"{sc.adjusted_irr:.1f}%",
                f"USD {sc.adjusted_npv:,.0f}",
                f"{sc.investment_recovered_pct:.0f}%",
            ])
        _add_table(doc, arrival_table)

    doc.add_page_break()

    # ── 12. Conclusions and Recommendations ─────────────────────
    _h1(doc, "12. Conclusions and Recommendations")

    _h2(doc, "12.1 Viability Assessment")
    doc.add_paragraph(
        f"The {site_name} {pv_kwp:.0f} kWp solar PV mini-grid presents a "
        f"{'credible and worthwhile' if viable else 'challenging but potentially worthwhile'} "
        f"rural electrification opportunity. "
        f"{'The desktop evidence supports advancement to full feasibility.' if viable else 'The project requires blended finance to be viable.'}"
    )

    _h2(doc, "12.2 Key Findings")
    findings = [
        f"{site_name} {'is unelectrified and has' if not cl.has_nightlight else 'has'} "
        f"{d.households} potential connections with estimated daily demand of {d.daily_energy_kwh:.0f} kWh.",
        f"Solar resource is well-supported by PVGIS at {ghi:,.0f} kWh/m²/year GHI.",
        f"System sizing indicates {pv_kwp:.0f} kWp PV with {batt_usable:.0f} kWh usable battery, "
        f"generating {ann_gen_mwh:.0f} MWh/year with {s.unmet_energy_pct:.1f}% unmet demand.",
        f"Total CAPEX is estimated at USD {total_capex:,.0f} (USD {f.capex_per_wp:.2f}/Wp).",
        f"Grid-interface risk is {gr.risk_level} ({gr.dist_mv_km:.1f} km to MV grid).",
        "The project must be structured as a blended-finance asset." if not viable else
        "The project appears viable under blended-finance assumptions.",
    ]
    for finding in findings:
        doc.add_paragraph(finding, style="List Bullet")

    _h2(doc, "12.3 Recommended Next Steps")
    _h3(doc, "Table 12-1: Recommended next steps")
    steps_table = [
        ["Phase", "Action", "Timeline"],
        ["1", "Household and enterprise demand survey including willingness-to-pay", "Months 1–2"],
        ["2", "Site visit: topographic, flood, and access survey; land-use confirmation", "Months 1–2"],
        ["3", "Confirm off-grid designation with FUNAE/ARENE; initiate DUAT engagement", "Months 1–3"],
        ["4", "Coordinates-specific solar extraction and detailed technical sizing", "Months 2–3"],
        ["5", "Community consultation and land-use verification for DUAT pathway", "Months 2–4"],
        ["6", "Environmental screening and ESIA scoping under Decree 54/2015", "Months 2–4"],
        ["7", "Blended-finance structure and bankable financial model", "Months 3–5"],
        ["8", "Supplier budget quotations and EPC market sounding", "Months 4–6"],
    ]
    _add_table(doc, steps_table)

    _h2(doc, "12.4 Go / No-Go Recommendation")
    p = doc.add_paragraph()
    run = p.add_run(f"RECOMMENDED DECISION: {rec}")
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x2F, 0x85, 0x5A)
    doc.add_paragraph(rec_text)

    # ── 25-Year Cash Flow (Appendix) ────────────────────────────
    doc.add_page_break()
    _h1(doc, "Appendix A: 25-Year Cash Flow Projection")
    cf_table = [["Year", "Revenue", "OPEX", "Replacements", "Net CF", "Cumulative"]]
    for cf in f.cash_flow:
        cf_table.append([
            str(cf.year),
            f"${cf.revenue:,.0f}",
            f"${cf.opex:,.0f}",
            f"${cf.replacements:,.0f}",
            f"${cf.net_cash_flow:,.0f}",
            f"${cf.cumulative:,.0f}",
        ])
    _add_table(doc, cf_table, small=True)

    # ── Footer ──────────────────────────────────────────────────
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        f"Generated by Moz Mini-Grid Prefeasibility Platform — {month_year}\n"
        "This report is for indicative planning purposes only."
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0xA0, 0xAE, 0xC0)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Document helpers ─────────────────────────────────────────────

def _set_default_style(doc: Document):
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(4)


def _h1(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x2F, 0x85, 0x5A)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)


def _h2(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)


def _h3(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
    run.italic = True
    p.paragraph_format.space_before = Pt(4)


def _add_centered(doc, text, bold=False, size=12, color=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color


def _add_blank_lines(doc, n):
    for _ in range(n):
        doc.add_paragraph()


def _add_table(doc, data: list[list[str]], small: bool = False):
    if not data:
        return
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, row_data in enumerate(data):
        for j, cell_text in enumerate(row_data):
            cell = table.cell(i, j)
            cell.text = str(cell_text)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.size = Pt(8 if small else 9)
                    if i == 0:
                        run.bold = True
