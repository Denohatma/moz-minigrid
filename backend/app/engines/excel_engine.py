from __future__ import annotations

import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

from app.schemas.analysis import AnalysisResult


HEADER_FONT = Font(bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2F855A", end_color="2F855A", fill_type="solid")
INPUT_FILL = PatternFill(start_color="FFFDE7", end_color="FFFDE7", fill_type="solid")
SECTION_FONT = Font(bold=True, size=12, color="1A202C")
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)
USD_FMT = '#,##0'
USD_DEC_FMT = '#,##0.00'
PCT_FMT = '0.0%'


def generate_excel(result: AnalysisResult) -> bytes:
    wb = Workbook()

    _build_inputs_sheet(wb, result)
    _build_demand_sheet(wb, result)
    _build_sizing_sheet(wb, result)
    _build_distribution_sheet(wb, result)
    _build_cashflow_sheet(wb, result)
    _build_sensitivity_sheet(wb, result)
    _build_carbon_sheet(wb, result)

    # TOR-required analysis sheets (only created when data is present)
    if result.productive_use is not None:
        _build_productive_use_sheet(wb, result)
    if result.ess is not None:
        _build_ess_sheet(wb, result)
    if result.climate is not None:
        _build_climate_sheet(wb, result)
    if result.risk_analysis is not None:
        _build_risk_register_sheet(wb, result)
    if result.confidence is not None:
        _build_confidence_sheet(wb, result)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _style_header_row(ws, row: int, cols: int):
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER


def _build_inputs_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.active
    ws.title = "Inputs"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 14

    row = 1
    ws.cell(row=row, column=1, value="Moz Mini-Grid Prefeasibility Model").font = Font(bold=True, size=14, color="2F855A")
    row += 2

    ws.cell(row=row, column=1, value="SITE INFORMATION").font = SECTION_FONT
    row += 1
    cl = r.cluster
    site_data = [
        ("Latitude", r.site.latitude, ""),
        ("Longitude", r.site.longitude, ""),
        ("Site Name", r.site.name or "Unnamed", ""),
        ("Settlement", cl.village_name or "—", ""),
        ("Province", cl.admin_region or "—", ""),
        ("District", cl.admin_district or "—", ""),
        ("Classification", ["Rural", "Peri-urban", "Urban"][min(cl.is_urban, 2)], ""),
        ("Population", cl.population, ""),
        ("Buildings", cl.num_buildings or "—", ""),
        ("Est. Connections", cl.dre_num_connections or "—", ""),
        ("Area", cl.area_km2, "km²"),
        ("Solar PV Potential", cl.ghi_kwh_m2_year, "kWh/kWp/yr"),
        ("Existing Grid", cl.dist_grid_mv_km, "km"),
        ("Planned Grid", cl.dist_grid_planned_km or "—", "km"),
        ("Road Distance", cl.dist_road_km, "km"),
        ("Nightlight", "Yes" if cl.has_nightlight else "No", ""),
        ("Wealth Index (RWI)", cl.mean_rwi if cl.mean_rwi is not None else "—", ""),
        ("Security Risk", cl.security_risk or "—", ""),
        ("Main Crops", cl.crop_types or "—", ""),
    ]
    for label, val, unit in site_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=val)
        cell.border = THIN_BORDER
        ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
        row += 1

    if r.solar_resource:
        row += 1
        ws.cell(row=row, column=1, value="SOLAR RESOURCE").font = SECTION_FONT
        row += 1
        sol = r.solar_resource
        solar_data = [
            ("Annual GHI", sol.annual_ghi_kwh_m2, "kWh/m²/yr"),
            ("Specific Yield", sol.specific_yield_kwh_per_kwp, "kWh/kWp"),
            ("Performance Ratio", sol.performance_ratio, ""),
            ("Data Source", sol.data_source, ""),
        ]
        for label, val, unit in solar_data:
            ws.cell(row=row, column=1, value=label).border = THIN_BORDER
            ws.cell(row=row, column=2, value=val).border = THIN_BORDER
            ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
            row += 1

    row += 1
    ws.cell(row=row, column=1, value="FINANCIAL ASSUMPTIONS").font = SECTION_FONT
    row += 1

    fin_data = [
        ("Affordable Tariff", r.financial.affordable_tariff_usd, "$/kWh"),
        ("Annual OPEX", r.financial.annual_opex_usd, "USD"),
        ("Grant / Subsidy", r.financial.grant_amount_usd, "USD"),
        ("Concessional Debt", r.financial.debt_amount_usd, "USD"),
        ("Developer Equity", r.financial.equity_amount_usd, "USD"),
        ("Project Life", 25, "years"),
    ]
    for label, val, unit in fin_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=val)
        cell.fill = INPUT_FILL
        cell.border = THIN_BORDER
        ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
        row += 1


def _build_demand_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Demand")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 16

    row = 1
    ws.cell(row=row, column=1, value="DEMAND ESTIMATION").font = SECTION_FONT
    row += 2

    demand_data = [
        ("Households", r.demand.households),
        ("Demand Tier (MTF)", r.demand.demand_tier),
        ("Persons per Household", r.demand.persons_per_hh),
        ("Daily Energy (kWh)", r.demand.daily_energy_kwh),
        ("Annual Energy (kWh)", r.demand.annual_energy_kwh),
        ("Peak Demand (kW)", r.demand.peak_demand_kw),
    ]
    for label, val in demand_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        ws.cell(row=row, column=2, value=val).border = THIN_BORDER
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="24-HOUR LOAD PROFILE").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Hour")
    ws.cell(row=row, column=2, value="Load (kW)")
    _style_header_row(ws, row, 2)
    row += 1
    for hour, kw in enumerate(r.demand.load_profile_kw):
        ws.cell(row=row, column=1, value=f"{hour:02d}:00").border = THIN_BORDER
        ws.cell(row=row, column=2, value=round(kw, 3)).border = THIN_BORDER
        row += 1


def _build_sizing_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Sizing")
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 10

    row = 1
    ws.cell(row=row, column=1, value="SYSTEM SIZING").font = SECTION_FONT
    row += 2

    s = r.sizing
    sizing_data = [
        ("PV Array", s.pv_kwp, "kWp"),
        ("Battery (Nominal)", s.battery_kwh_nominal, "kWh"),
        ("Battery (Usable)", s.battery_kwh_usable, "kWh"),
        ("Inverter", s.inverter_kva, "kVA"),
        ("DC/AC Ratio", s.dc_ac_ratio, ""),
        ("LV Network", s.lv_line_km, "km"),
        ("Transformers (50 kVA)", s.service_transformers, "units"),
        ("Meters", s.meters, "units"),
    ]
    for label, val, unit in sizing_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        ws.cell(row=row, column=2, value=val).border = THIN_BORDER
        ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
        row += 1

    if s.annual_generation_kwh is not None:
        row += 1
        ws.cell(row=row, column=1, value="DISPATCH SIMULATION").font = SECTION_FONT
        row += 1
        dispatch_data = [
            ("Annual Generation", f"{s.annual_generation_kwh:,.0f}", "kWh"),
            ("Annual Energy Served", f"{s.annual_energy_served_kwh:,.0f}" if s.annual_energy_served_kwh else "—", "kWh"),
            ("Unmet Energy", f"{s.unmet_energy_pct:.1f}" if s.unmet_energy_pct is not None else "—", "%"),
            ("Curtailment", f"{s.curtailment_pct:.1f}" if s.curtailment_pct is not None else "—", "%"),
            ("Capacity Factor", f"{s.capacity_factor_pct:.1f}" if s.capacity_factor_pct is not None else "—", "%"),
            ("Battery Cycles / Year", f"{s.battery_cycles_per_year:,.0f}" if s.battery_cycles_per_year is not None else "—", ""),
        ]
        for label, val, unit in dispatch_data:
            ws.cell(row=row, column=1, value=label).border = THIN_BORDER
            ws.cell(row=row, column=2, value=val).border = THIN_BORDER
            ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
            row += 1

    row += 2
    ws.cell(row=row, column=1, value="CAPEX BREAKDOWN").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Component")
    ws.cell(row=row, column=2, value="Cost (USD)")
    ws.cell(row=row, column=3, value="% Total")
    _style_header_row(ws, row, 3)
    row += 1

    bk = r.financial.capex_breakdown
    total = r.financial.total_capex_usd
    capex_items = [
        ("PV Modules", bk.pv),
        ("Battery", bk.battery),
        ("Inverter + BOS", bk.inverter),
        ("Distribution", bk.distribution),
        ("Meters", bk.meters),
        ("Installation", bk.installation),
        ("Soft Costs", bk.soft_costs),
    ]
    for label, cost in capex_items:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=round(cost, 2))
        cell.number_format = USD_FMT
        cell.border = THIN_BORDER
        pct_cell = ws.cell(row=row, column=3, value=round(cost / total, 3) if total else 0)
        pct_cell.number_format = PCT_FMT
        pct_cell.border = THIN_BORDER
        row += 1

    ws.cell(row=row, column=1, value="TOTAL").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    total_cell = ws.cell(row=row, column=2, value=round(total, 2))
    total_cell.font = Font(bold=True)
    total_cell.number_format = USD_FMT
    total_cell.border = THIN_BORDER


def _build_distribution_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Distribution")
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 12

    row = 1
    ws.cell(row=row, column=1, value="DISTRIBUTION NETWORK").font = SECTION_FONT
    row += 2

    if not r.distribution:
        ws.cell(row=row, column=1, value="Distribution data not available.")
        return

    d = r.distribution
    summary_data = [
        ("Total Line Length", f"{d.total_line_length_m:,.0f}", "m"),
        ("Pole Count", d.pole_count, "units"),
        ("Customers Connected", d.customers_connected, ""),
        ("Cost per Connection", round(d.cost_per_connection_usd, 0), "USD"),
        ("Total Network Cost", round(d.total_network_cost_usd, 0), "USD"),
        ("Max Voltage Drop", f"{d.voltage_drop_max_pct:.1f}", "%"),
        ("Technical Losses", f"{d.technical_losses_pct:.1f}", "%"),
        ("Construction Multiplier", f"{d.construction_multiplier:.2f}", ""),
        ("Estimation Method", d.method_used, ""),
    ]
    for label, val, unit in summary_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=val)
        cell.border = THIN_BORDER
        if isinstance(val, (int, float)) and unit == "USD":
            cell.number_format = USD_FMT
        ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
        row += 1

    if d.bill_of_quantities:
        row += 1
        ws.cell(row=row, column=1, value="BILL OF QUANTITIES").font = SECTION_FONT
        row += 1
        boq_headers = ["Category", "Description", "Unit", "Qty", "Unit Cost (USD)", "Total (USD)"]
        for i in range(1, 7):
            ws.column_dimensions[get_column_letter(i)].width = max(
                ws.column_dimensions[get_column_letter(i)].width or 0, 16
            )
        ws.column_dimensions["D"].width = 10
        for c, h in enumerate(boq_headers, 1):
            ws.cell(row=row, column=c, value=h)
        _style_header_row(ws, row, len(boq_headers))
        row += 1

        grand_total = 0.0
        for item in d.bill_of_quantities:
            ws.cell(row=row, column=1, value=item.category).border = THIN_BORDER
            ws.cell(row=row, column=2, value=item.description).border = THIN_BORDER
            ws.cell(row=row, column=3, value=item.unit).border = THIN_BORDER
            qty_cell = ws.cell(row=row, column=4, value=round(item.quantity, 1))
            qty_cell.border = THIN_BORDER
            uc_cell = ws.cell(row=row, column=5, value=round(item.unit_cost_usd, 2))
            uc_cell.number_format = USD_DEC_FMT
            uc_cell.border = THIN_BORDER
            tc_cell = ws.cell(row=row, column=6, value=round(item.total_cost_usd, 2))
            tc_cell.number_format = USD_FMT
            tc_cell.border = THIN_BORDER
            grand_total += item.total_cost_usd
            row += 1

        ws.cell(row=row, column=1, value="TOTAL").font = Font(bold=True)
        ws.cell(row=row, column=1).border = THIN_BORDER
        total_cell = ws.cell(row=row, column=6, value=round(grand_total, 2))
        total_cell.font = Font(bold=True)
        total_cell.number_format = USD_FMT
        total_cell.border = THIN_BORDER

    if d.warnings:
        row += 2
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in d.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1


def _build_cashflow_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Cash Flow")
    headers = [
        "Year", "Revenue", "Carbon Rev.", "OPEX", "Debt Service",
        "CAPEX", "Replacements", "Net Cash Flow", "Cumulative",
    ]
    ws.column_dimensions["A"].width = 8
    for i in range(2, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 16

    row = 1
    ws.cell(row=row, column=1, value="25-YEAR CASH FLOW").font = SECTION_FONT
    row += 2

    metrics = [
        ("Total CAPEX", f"${r.financial.total_capex_usd:,.0f}"),
        ("CAPEX / Wp", f"${r.financial.capex_per_wp:.2f}" if r.financial.capex_per_wp else "—"),
        ("LCOE", f"${r.financial.lcoe_usd_kwh:.4f}/kWh"),
        ("Project IRR", f"{r.financial.irr_pct:.1f}%"),
        ("Equity IRR", f"{r.financial.equity_irr_pct:.1f}%" if r.financial.equity_irr_pct is not None else "—"),
        ("NPV", f"${r.financial.npv_usd:,.0f}"),
        ("Payback", f"{r.financial.payback_years:.1f} years"),
        ("Min DSCR", f"{r.financial.dscr:.2f}"),
        ("Cost-Reflective Tariff", f"${r.financial.cost_reflective_tariff_usd:.4f}/kWh"),
        ("Subsidy Gap / Connection", f"${r.financial.subsidy_gap_per_connection_usd:,.0f}"),
        ("Subsidy Gap (% CAPEX)", f"{r.financial.subsidy_gap_pct_capex:.1f}%"),
    ]
    for label, val in metrics:
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws.cell(row=row, column=1).border = THIN_BORDER
        ws.cell(row=row, column=2, value=val).border = THIN_BORDER
        row += 1

    row += 1
    for c, h in enumerate(headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(headers))
    row += 1

    for cf in r.financial.cash_flow:
        ws.cell(row=row, column=1, value=cf.year).border = THIN_BORDER
        values = [
            cf.revenue,
            cf.carbon_revenue or 0,
            cf.opex,
            cf.debt_service or 0,
            cf.capex,
            cf.replacements,
            cf.net_cash_flow,
            cf.cumulative,
        ]
        for c, val in enumerate(values, 2):
            cell = ws.cell(row=row, column=c, value=val)
            cell.number_format = USD_DEC_FMT
            cell.border = THIN_BORDER
        row += 1


def _build_sensitivity_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Sensitivity")
    headers = ["Parameter", "Low Value", "Base Value", "High Value", "IRR @ Low", "IRR @ Base", "IRR @ High"]
    for i in range(1, 8):
        ws.column_dimensions[get_column_letter(i)].width = 16

    row = 1
    ws.cell(row=row, column=1, value="SENSITIVITY ANALYSIS (±20%)").font = SECTION_FONT
    row += 2

    for c, h in enumerate(headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(headers))
    row += 1

    for s in r.financial.sensitivity:
        ws.cell(row=row, column=1, value=s.parameter).border = THIN_BORDER
        ws.cell(row=row, column=2, value=s.low_value).border = THIN_BORDER
        ws.cell(row=row, column=3, value=s.base_value).border = THIN_BORDER
        ws.cell(row=row, column=4, value=s.high_value).border = THIN_BORDER
        for c, val in enumerate([s.irr_at_low, s.irr_at_base, s.irr_at_high], 5):
            cell = ws.cell(row=row, column=c, value=val)
            cell.number_format = '0.0'
            cell.border = THIN_BORDER
        row += 1

    row += 2
    ws.cell(row=row, column=1, value="GRID RISK ASSESSMENT").font = SECTION_FONT
    row += 1
    gr = r.grid_risk
    ws.cell(row=row, column=1, value="MV Grid Distance").border = THIN_BORDER
    ws.cell(row=row, column=2, value=f"{gr.dist_mv_km:.1f} km").border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="HV Grid Distance").border = THIN_BORDER
    ws.cell(row=row, column=2, value=f"{gr.dist_hv_km:.1f} km").border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Risk Level").border = THIN_BORDER
    ws.cell(row=row, column=2, value=gr.risk_level.upper()).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Assessment").border = THIN_BORDER
    ws.cell(row=row, column=2, value=gr.risk_label).border = THIN_BORDER

    if gr.scenarios:
        row += 2
        for sc in gr.scenarios:
            ws.cell(row=row, column=1, value=f"Grid arrives year {sc.arrival_year}").font = Font(bold=True)
            row += 1
            ws.cell(row=row, column=1, value="Adjusted IRR").border = THIN_BORDER
            ws.cell(row=row, column=2, value=f"{sc.adjusted_irr:.1f}%").border = THIN_BORDER
            row += 1
            ws.cell(row=row, column=1, value="Investment Recovered").border = THIN_BORDER
            ws.cell(row=row, column=2, value=f"{sc.investment_recovered_pct:.0f}%").border = THIN_BORDER
            row += 1

    if gr.esmap_scores:
        row += 2
        ws.cell(row=row, column=1, value="ESMAP SCENARIO SCORING").font = SECTION_FONT
        row += 1
        esmap_headers = ["Scenario", "Score", "Timeline", "Financial", "Regulatory", "Complexity", "Stakeholder"]
        for c, h in enumerate(esmap_headers, 1):
            ws.cell(row=row, column=c, value=h)
        _style_header_row(ws, row, len(esmap_headers))
        row += 1
        for es in gr.esmap_scores:
            ws.cell(row=row, column=1, value=es.label).border = THIN_BORDER
            for c, val in enumerate([
                es.weighted_score, es.timeline_certainty, es.financial_viability,
                es.regulatory_alignment, es.implementation_complexity, es.stakeholder_acceptability,
            ], 2):
                cell = ws.cell(row=row, column=c, value=round(val, 2))
                cell.number_format = '0.00'
                cell.border = THIN_BORDER
            row += 1

        if gr.esmap_recommended:
            row += 1
            ws.cell(row=row, column=1, value="Recommended Strategy").font = Font(bold=True)
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2, value=gr.esmap_recommended).border = THIN_BORDER

    if gr.design_implications:
        row += 2
        ws.cell(row=row, column=1, value="Design Implications").font = Font(bold=True)
        row += 1
        ws.cell(row=row, column=1, value=gr.design_implications).border = THIN_BORDER


def _build_carbon_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Carbon")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 12

    row = 1
    ws.cell(row=row, column=1, value="CARBON CREDIT ASSESSMENT").font = SECTION_FONT
    row += 2

    if not r.carbon:
        ws.cell(row=row, column=1, value="Carbon assessment not available.")
        return

    ca = r.carbon
    summary_data = [
        ("Annual Emission Reductions", round(ca.annual_emission_reductions_tco2e, 1), "tCO2e/yr"),
        ("Diesel Displaced", round(ca.diesel_displaced_litres_yr, 0), "litres/yr"),
        ("Crediting Period", ca.crediting_period_years, "years"),
        ("Total Eligible Reductions", round(ca.total_eligible_tco2e, 0), "tCO2e"),
        ("Recommended Methodology", ca.recommended_methodology, ""),
        ("Alternative Methodology", ca.alternative_methodology, ""),
        ("Validation Cost", round(ca.validation_cost_estimate_usd, 0), "USD"),
        ("Annual Verification Cost", round(ca.annual_verification_cost_usd, 0), "USD"),
    ]
    for label, val, unit in summary_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=val)
        cell.border = THIN_BORDER
        if isinstance(val, (int, float)) and unit == "USD":
            cell.number_format = USD_FMT
        ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="Methodology Rationale").font = Font(bold=True)
    row += 1
    ws.cell(row=row, column=1, value=ca.methodology_rationale).border = THIN_BORDER

    row += 2
    ws.cell(row=row, column=1, value="REVENUE BY PRICE SCENARIO").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Scenario")
    ws.cell(row=row, column=2, value="Annual Revenue (USD)")
    ws.cell(row=row, column=3, value="NPV (USD)")
    _style_header_row(ws, row, 3)
    row += 1

    for scenario, annual_rev in sorted(ca.revenue_by_scenario.items()):
        ws.cell(row=row, column=1, value=scenario.replace("_", " ").title()).border = THIN_BORDER
        rev_cell = ws.cell(row=row, column=2, value=round(annual_rev, 0))
        rev_cell.number_format = USD_FMT
        rev_cell.border = THIN_BORDER
        npv_val = ca.npv_carbon_revenue.get(scenario, 0)
        npv_cell = ws.cell(row=row, column=3, value=round(npv_val, 0))
        npv_cell.number_format = USD_FMT
        npv_cell.border = THIN_BORDER
        row += 1

    if ca.warnings:
        row += 2
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in ca.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1


# ── Productive Use Sheet ───────────────────────────────────────────

def _build_productive_use_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Productive Use")
    pu = r.productive_use

    # Column widths
    for col, width in [("A", 22), ("B", 22), ("C", 30), ("D", 18), ("E", 18), ("F", 20)]:
        ws.column_dimensions[col].width = width

    row = 1

    # ── Relevant Sectors ──
    ws.cell(row=row, column=1, value="RELEVANT SECTORS").font = SECTION_FONT
    row += 1
    sector_headers = ["Sector", "Relevance", "Activities", "Est. Demand kWh/day", "Seasonal Pattern"]
    for c, h in enumerate(sector_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(sector_headers))
    row += 1

    for s in pu.sectors:
        ws.cell(row=row, column=1, value=s.sector).border = THIN_BORDER
        ws.cell(row=row, column=2, value=s.relevance.title()).border = THIN_BORDER
        ws.cell(row=row, column=3, value=", ".join(s.indicative_activities) if s.indicative_activities else "—").border = THIN_BORDER
        cell = ws.cell(row=row, column=4, value=round(s.estimated_demand_kwh_day, 1))
        cell.number_format = USD_DEC_FMT
        cell.border = THIN_BORDER
        ws.cell(row=row, column=5, value=s.seasonal_pattern).border = THIN_BORDER
        row += 1

    # ── Anchor Customers ──
    row += 1
    ws.cell(row=row, column=1, value="ANCHOR CUSTOMERS").font = SECTION_FONT
    row += 1
    anchor_headers = ["Type", "Name", "Demand kWh/day", "Peak kW", "Confidence", "Contract Type"]
    for c, h in enumerate(anchor_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(anchor_headers))
    row += 1

    for a in pu.anchors:
        ws.cell(row=row, column=1, value=a.type).border = THIN_BORDER
        ws.cell(row=row, column=2, value=a.name).border = THIN_BORDER
        cell = ws.cell(row=row, column=3, value=round(a.estimated_demand_kwh_day, 1))
        cell.number_format = USD_DEC_FMT
        cell.border = THIN_BORDER
        cell = ws.cell(row=row, column=4, value=round(a.estimated_peak_kw, 2))
        cell.number_format = USD_DEC_FMT
        cell.border = THIN_BORDER
        ws.cell(row=row, column=5, value=a.confidence.title()).border = THIN_BORDER
        ws.cell(row=row, column=6, value=a.contract_type).border = THIN_BORDER
        row += 1

    # ── Equipment Recommendations ──
    row += 1
    ws.cell(row=row, column=1, value="EQUIPMENT RECOMMENDATIONS").font = SECTION_FONT
    row += 1
    equip_headers = ["Sector", "Equipment", "Power kW", "CAPEX Low USD", "CAPEX High USD", "Ownership Model"]
    for c, h in enumerate(equip_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(equip_headers))
    row += 1

    for eq in pu.equipment_recommendations:
        ws.cell(row=row, column=1, value=eq.sector).border = THIN_BORDER
        ws.cell(row=row, column=2, value=eq.equipment).border = THIN_BORDER
        cell = ws.cell(row=row, column=3, value=round(eq.power_kw, 2))
        cell.number_format = USD_DEC_FMT
        cell.border = THIN_BORDER
        cell = ws.cell(row=row, column=4, value=round(eq.capex_usd_low, 0))
        cell.number_format = USD_FMT
        cell.border = THIN_BORDER
        cell = ws.cell(row=row, column=5, value=round(eq.capex_usd_high, 0))
        cell.number_format = USD_FMT
        cell.border = THIN_BORDER
        ws.cell(row=row, column=6, value=eq.ownership_model).border = THIN_BORDER
        row += 1

    # ── Complementary Investment ──
    row += 1
    ws.cell(row=row, column=1, value="COMPLEMENTARY INVESTMENT").font = SECTION_FONT
    row += 1
    comp = pu.complementary_investment_usd
    comp_items = [
        ("Equipment", comp.get("equipment", 0)),
        ("Working Capital", comp.get("working_capital", 0)),
        ("Market Access", comp.get("market_access", 0)),
        ("Training", comp.get("training", 0)),
    ]
    total_comp = sum(v for _, v in comp_items)
    comp_items.append(("Total", total_comp))
    for label, val in comp_items:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=round(val, 0))
        cell.number_format = USD_FMT
        cell.border = THIN_BORDER
        if label == "Total":
            ws.cell(row=row, column=1).font = Font(bold=True)
            cell.font = Font(bold=True)
        row += 1

    # ── Jobs & Income ──
    row += 1
    ws.cell(row=row, column=1, value="JOBS & INCOME").font = SECTION_FONT
    row += 1
    jobs = pu.jobs
    direct = jobs.get("direct", 0)
    indirect = jobs.get("indirect", 0)
    total_jobs = jobs.get("total", direct + indirect)
    jobs_data = [
        ("Direct Jobs", direct),
        ("Indirect Jobs", indirect),
        ("Total Jobs", total_jobs),
        ("Incremental Income (USD/year)", round(pu.incremental_income_usd_year, 0)),
    ]
    for label, val in jobs_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        cell = ws.cell(row=row, column=2, value=val)
        cell.border = THIN_BORDER
        if "USD" in label:
            cell.number_format = USD_FMT
        if label == "Total Jobs":
            ws.cell(row=row, column=1).font = Font(bold=True)
            cell.font = Font(bold=True)
        row += 1

    if pu.warnings:
        row += 1
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in pu.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1


# ── ESS Sheet ──────────────────────────────────────────────────────

def _build_ess_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("ESS")
    ess = r.ess

    for col, width in [("A", 30), ("B", 40), ("C", 16)]:
        ws.column_dimensions[col].width = width

    row = 1
    ws.cell(row=row, column=1, value="ENVIRONMENTAL & SOCIAL SCREENING").font = SECTION_FONT
    row += 2

    # ── ESIA Category ──
    ws.cell(row=row, column=1, value="ESIA CATEGORY").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Category").border = THIN_BORDER
    ws.cell(row=row, column=2, value=ess.esia_category).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Rationale").border = THIN_BORDER
    ws.cell(row=row, column=2, value=ess.esia_rationale).border = THIN_BORDER
    row += 1

    if ess.esia_requirements:
        ws.cell(row=row, column=1, value="Requirements").font = Font(bold=True)
        row += 1
        for req in ess.esia_requirements:
            ws.cell(row=row, column=1, value=req).border = THIN_BORDER
            row += 1

    # ── Biodiversity ──
    row += 1
    ws.cell(row=row, column=1, value="BIODIVERSITY SCREENING").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Sensitivity").border = THIN_BORDER
    ws.cell(row=row, column=2, value=ess.biodiversity_sensitivity).border = THIN_BORDER
    row += 1
    if ess.biodiversity_notes:
        ws.cell(row=row, column=1, value="Notes").border = THIN_BORDER
        ws.cell(row=row, column=2, value=ess.biodiversity_notes).border = THIN_BORDER
        row += 1

    if ess.protected_area_checks:
        row += 1
        pa_headers = ["Protected Area", "Distance km", "Buffer Zone", "Sensitivity"]
        for c, h in enumerate(pa_headers, 1):
            ws.cell(row=row, column=c, value=h)
        _style_header_row(ws, row, len(pa_headers))
        ws.column_dimensions["D"].width = 16
        row += 1
        for pa in ess.protected_area_checks:
            ws.cell(row=row, column=1, value=pa.area_name).border = THIN_BORDER
            cell = ws.cell(row=row, column=2, value=round(pa.distance_km, 1))
            cell.number_format = USD_DEC_FMT
            cell.border = THIN_BORDER
            ws.cell(row=row, column=3, value="Yes" if pa.buffer_zone else "No").border = THIN_BORDER
            ws.cell(row=row, column=4, value=pa.sensitivity.title()).border = THIN_BORDER
            row += 1

    # ── Resettlement Risk ──
    row += 1
    ws.cell(row=row, column=1, value="RESETTLEMENT RISK").font = SECTION_FONT
    row += 1
    resettle_data = [
        ("Resettlement Risk", ess.resettlement_risk),
        ("Physical Displacement Risk", ess.physical_displacement_risk or "—"),
        ("Economic Displacement Risk", ess.economic_displacement_risk or "—"),
        ("Est. Land Requirement (ha)", round(ess.estimated_land_requirement_ha, 2)),
    ]
    for label, val in resettle_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        ws.cell(row=row, column=2, value=val).border = THIN_BORDER
        row += 1
    if ess.resettlement_notes:
        ws.cell(row=row, column=1, value="Notes").border = THIN_BORDER
        ws.cell(row=row, column=2, value=ess.resettlement_notes).border = THIN_BORDER
        row += 1

    # ── Overall ESS Risk ──
    row += 1
    ws.cell(row=row, column=1, value="OVERALL ESS RISK").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Overall Risk Level").border = THIN_BORDER
    ws.cell(row=row, column=2, value=ess.overall_ess_risk.upper()).border = THIN_BORDER
    row += 1

    # ── Stakeholder Groups ──
    if ess.stakeholder_groups:
        row += 1
        ws.cell(row=row, column=1, value="STAKEHOLDER GROUPS").font = SECTION_FONT
        row += 1
        for sg in ess.stakeholder_groups:
            ws.cell(row=row, column=1, value=sg).border = THIN_BORDER
            row += 1

    # ── GESI Considerations ──
    if ess.gesi_considerations:
        row += 1
        ws.cell(row=row, column=1, value="GESI CONSIDERATIONS").font = SECTION_FONT
        row += 1
        for g in ess.gesi_considerations:
            ws.cell(row=row, column=1, value=g).border = THIN_BORDER
            row += 1

    if ess.womens_empowerment_opportunities:
        row += 1
        ws.cell(row=row, column=1, value="Women's Empowerment Opportunities").font = Font(bold=True)
        row += 1
        for opp in ess.womens_empowerment_opportunities:
            ws.cell(row=row, column=1, value=opp).border = THIN_BORDER
            row += 1

    if ess.inclusion_measures:
        row += 1
        ws.cell(row=row, column=1, value="Inclusion Measures").font = Font(bold=True)
        row += 1
        for m in ess.inclusion_measures:
            ws.cell(row=row, column=1, value=m).border = THIN_BORDER
            row += 1

    # ── Recommended Actions ──
    if ess.recommended_actions:
        row += 1
        ws.cell(row=row, column=1, value="RECOMMENDED ACTIONS").font = SECTION_FONT
        row += 1
        for action in ess.recommended_actions:
            ws.cell(row=row, column=1, value=action).border = THIN_BORDER
            row += 1

    if ess.warnings:
        row += 1
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in ess.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1


# ── Climate Sheet ──────────────────────────────────────────────────

def _build_climate_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Climate")
    cl = r.climate

    for col, width in [("A", 28), ("B", 18), ("C", 36), ("D", 36)]:
        ws.column_dimensions[col].width = width

    row = 1
    ws.cell(row=row, column=1, value="CLIMATE RATIONALE").font = SECTION_FONT
    row += 2

    # ── Climate Hazards ──
    ws.cell(row=row, column=1, value="CLIMATE HAZARDS").font = SECTION_FONT
    row += 1
    hazard_headers = ["Hazard", "Level", "Description", "Design Measures"]
    for c, h in enumerate(hazard_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(hazard_headers))
    row += 1

    for hz in cl.hazards:
        ws.cell(row=row, column=1, value=hz.hazard.replace("_", " ").title()).border = THIN_BORDER
        ws.cell(row=row, column=2, value=hz.level.replace("_", " ").title()).border = THIN_BORDER
        ws.cell(row=row, column=3, value=hz.description).border = THIN_BORDER
        ws.cell(row=row, column=4, value=", ".join(hz.design_measures) if hz.design_measures else "—").border = THIN_BORDER
        row += 1

    ws.cell(row=row, column=1, value="Overall Hazard Level").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    ws.cell(row=row, column=2, value=cl.overall_hazard_level.replace("_", " ").title()).border = THIN_BORDER
    row += 1

    if cl.design_resilience_measures:
        row += 1
        ws.cell(row=row, column=1, value="Design Resilience Measures").font = Font(bold=True)
        row += 1
        for m in cl.design_resilience_measures:
            ws.cell(row=row, column=1, value=m).border = THIN_BORDER
            row += 1

    # ── Mitigation Summary ──
    row += 1
    ws.cell(row=row, column=1, value="MITIGATION SUMMARY").font = SECTION_FONT
    row += 1
    mitigation_data = [
        ("Lifetime Avoided Emissions", round(cl.lifetime_avoided_tco2e, 1), "tCO2e"),
        ("Per Capita Reduction", round(cl.per_capita_reduction_tco2e, 3), "tCO2e"),
        ("NDC Alignment", cl.ndc_alignment, ""),
    ]
    for label, val, unit in mitigation_data:
        ws.cell(row=row, column=1, value=label).border = THIN_BORDER
        ws.cell(row=row, column=2, value=val).border = THIN_BORDER
        ws.cell(row=row, column=3, value=unit).border = THIN_BORDER
        row += 1

    # ── Adaptation ──
    row += 1
    ws.cell(row=row, column=1, value="ADAPTATION").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value="Adaptation Narrative").border = THIN_BORDER
    ws.cell(row=row, column=2, value=cl.adaptation_narrative).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Water Security").border = THIN_BORDER
    ws.cell(row=row, column=2, value=cl.water_security_contribution).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Food Security").border = THIN_BORDER
    ws.cell(row=row, column=2, value=cl.food_security_contribution).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Energy Access Adaptation").border = THIN_BORDER
    ws.cell(row=row, column=2, value=cl.energy_access_adaptation).border = THIN_BORDER
    row += 1

    # ── Climate Finance ──
    row += 1
    ws.cell(row=row, column=1, value="CLIMATE FINANCE ELIGIBILITY").font = SECTION_FONT
    row += 1
    fin_headers = ["Instrument", "Eligible", "Est. Value USD", "Rationale"]
    for c, h in enumerate(fin_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(fin_headers))
    row += 1

    for cf in cl.climate_finance:
        ws.cell(row=row, column=1, value=cf.instrument).border = THIN_BORDER
        ws.cell(row=row, column=2, value="Yes" if cf.eligible else "No").border = THIN_BORDER
        cell = ws.cell(row=row, column=3, value=round(cf.estimated_value_usd, 0))
        cell.number_format = USD_FMT
        cell.border = THIN_BORDER
        ws.cell(row=row, column=4, value=cf.rationale).border = THIN_BORDER
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="Climate Finance Score").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    ws.cell(row=row, column=2, value=cl.climate_finance_score.upper()).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Total Climate Finance Potential").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    cell = ws.cell(row=row, column=2, value=round(cl.total_climate_finance_potential_usd, 0))
    cell.number_format = USD_FMT
    cell.border = THIN_BORDER
    ws.cell(row=row, column=3, value="USD").border = THIN_BORDER

    if cl.warnings:
        row += 2
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in cl.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1


# ── Risk Register Sheet ───────────────────────────────────────────

def _build_risk_register_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Risk Register")
    ra = r.risk_analysis

    for col, width in [
        ("A", 16), ("B", 24), ("C", 12), ("D", 10), ("E", 10),
        ("F", 10), ("G", 36), ("H", 14),
    ]:
        ws.column_dimensions[col].width = width

    row = 1
    ws.cell(row=row, column=1, value="RISK REGISTER").font = SECTION_FONT
    row += 2

    # ── Overall Risk ──
    ws.cell(row=row, column=1, value="Overall Risk Level").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    ws.cell(row=row, column=2, value=ra.overall_risk_level.upper()).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Overall Risk Score").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    ws.cell(row=row, column=2, value=round(ra.overall_risk_score, 1)).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Mitigation Investment").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    cell = ws.cell(row=row, column=2, value=round(ra.mitigation_investment_usd, 0))
    cell.number_format = USD_FMT
    cell.border = THIN_BORDER
    ws.cell(row=row, column=3, value="USD").border = THIN_BORDER
    row += 1

    # ── Top Risks ──
    if ra.top_risks:
        row += 1
        ws.cell(row=row, column=1, value="TOP RISKS").font = SECTION_FONT
        row += 1
        for i, tr in enumerate(ra.top_risks, 1):
            ws.cell(row=row, column=1, value=f"{i}.").border = THIN_BORDER
            ws.cell(row=row, column=2, value=tr).border = THIN_BORDER
            row += 1

    # ── Full Risk Matrix ──
    row += 1
    ws.cell(row=row, column=1, value="RISK MATRIX").font = SECTION_FONT
    row += 1
    risk_headers = ["Category", "Sub-Risk", "Likelihood", "Impact", "Score", "Level", "Mitigation", "Allocation"]
    for c, h in enumerate(risk_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(risk_headers))
    row += 1

    for ri in ra.risks:
        ws.cell(row=row, column=1, value=ri.category.title()).border = THIN_BORDER
        ws.cell(row=row, column=2, value=ri.sub_risk).border = THIN_BORDER
        ws.cell(row=row, column=3, value=ri.likelihood).border = THIN_BORDER
        ws.cell(row=row, column=4, value=ri.impact).border = THIN_BORDER
        ws.cell(row=row, column=5, value=ri.risk_score).border = THIN_BORDER
        ws.cell(row=row, column=6, value=ri.risk_level.upper()).border = THIN_BORDER
        ws.cell(row=row, column=7, value="; ".join(ri.mitigation) if ri.mitigation else "—").border = THIN_BORDER
        ws.cell(row=row, column=8, value=ri.allocation.title()).border = THIN_BORDER
        row += 1

    if ra.warnings:
        row += 1
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in ra.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1


# ── Confidence Sheet ───────────────────────────────────────────────

def _build_confidence_sheet(wb: Workbook, r: AnalysisResult):
    ws = wb.create_sheet("Confidence")
    ca = r.confidence

    for col, width in [("A", 24), ("B", 12), ("C", 18), ("D", 14), ("E", 18)]:
        ws.column_dimensions[col].width = width

    row = 1
    ws.cell(row=row, column=1, value="CONFIDENCE ASSESSMENT").font = SECTION_FONT
    row += 2

    # ── Overall Score ──
    ws.cell(row=row, column=1, value="Overall Confidence Score").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    ws.cell(row=row, column=2, value=ca.overall_confidence_score).border = THIN_BORDER
    ws.cell(row=row, column=3, value=f"/ 100").border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Overall Confidence Level").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    ws.cell(row=row, column=2, value=ca.overall_confidence_level.upper()).border = THIN_BORDER
    row += 1
    ws.cell(row=row, column=1, value="Data Completeness").font = Font(bold=True)
    ws.cell(row=row, column=1).border = THIN_BORDER
    cell = ws.cell(row=row, column=2, value=round(ca.data_completeness_pct / 100, 3))
    cell.number_format = PCT_FMT
    cell.border = THIN_BORDER
    row += 2

    # ── Dimension Table ──
    ws.cell(row=row, column=1, value="CONFIDENCE DIMENSIONS").font = SECTION_FONT
    row += 1
    dim_headers = ["Dimension", "Score", "Margin of Error %", "Data Quality", "Calibration Status"]
    for c, h in enumerate(dim_headers, 1):
        ws.cell(row=row, column=c, value=h)
    _style_header_row(ws, row, len(dim_headers))
    row += 1

    for d in ca.dimensions:
        ws.cell(row=row, column=1, value=d.dimension).border = THIN_BORDER
        ws.cell(row=row, column=2, value=d.confidence_score).border = THIN_BORDER
        cell = ws.cell(row=row, column=3, value=round(d.margin_of_error_pct, 1))
        cell.number_format = '0.0'
        cell.border = THIN_BORDER
        ws.cell(row=row, column=4, value=d.data_quality.title()).border = THIN_BORDER
        ws.cell(row=row, column=5, value=d.calibration_status).border = THIN_BORDER
        row += 1

    # ── Recommendations ──
    if ca.recommendations:
        row += 1
        ws.cell(row=row, column=1, value="RECOMMENDATIONS").font = SECTION_FONT
        row += 1
        for i, rec in enumerate(ca.recommendations, 1):
            ws.cell(row=row, column=1, value=f"{i}.").border = THIN_BORDER
            ws.cell(row=row, column=2, value=rec).border = THIN_BORDER
            row += 1

    if ca.warnings:
        row += 1
        ws.cell(row=row, column=1, value="WARNINGS").font = SECTION_FONT
        row += 1
        for w in ca.warnings:
            ws.cell(row=row, column=1, value=w).border = THIN_BORDER
            row += 1
