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
