from __future__ import annotations

from app.schemas.analysis import AnalysisResult


def generate_html_report(result: AnalysisResult) -> str:
    """Generate an HTML prefeasibility report that can be printed to PDF."""
    r = result
    f = r.financial
    s = r.sizing
    d = r.demand
    gr = r.grid_risk
    cl = r.cluster

    urban_label = ["Rural", "Peri-urban", "Urban"][min(cl.is_urban, 2)]

    sol = r.solar_resource
    dist = r.distribution
    carb = r.carbon

    capex_items = [
        ("PV Modules", f.capex_breakdown.pv),
        ("Battery", f.capex_breakdown.battery),
        ("Inverter + BOS", f.capex_breakdown.inverter),
        ("Distribution", f.capex_breakdown.distribution),
        ("Installation", f.capex_breakdown.installation),
        ("Soft Costs / Contingency", f.capex_breakdown.soft_costs),
    ]

    warnings_html = ""
    for w in r.screening.warnings:
        color = "#e53e3e" if w.severity == "error" else "#d69e2e" if w.severity == "warning" else "#3182ce"
        warnings_html += f'<div style="padding:8px 12px;margin-bottom:6px;border-left:3px solid {color};background:#f7fafc;font-size:13px;">{w.message}</div>'

    scenarios_html = ""
    if gr.scenarios:
        rows = ""
        for sc in gr.scenarios:
            rows += f"<tr><td>Year {sc.arrival_year}</td><td>{sc.adjusted_irr:.1f}%</td><td>${sc.adjusted_npv:,.0f}</td><td>{sc.investment_recovered_pct:.0f}%</td></tr>"
        scenarios_html = f"""
        <h3>Grid Arrival Scenarios</h3>
        <table><thead><tr><th>Scenario</th><th>Adjusted IRR</th><th>Adjusted NPV</th><th>Investment Recovered</th></tr></thead>
        <tbody>{rows}</tbody></table>"""

    sensitivity_rows = ""
    for sv in f.sensitivity:
        sensitivity_rows += f"<tr><td>{sv.parameter}</td><td>{sv.irr_at_low:.1f}%</td><td>{sv.irr_at_base:.1f}%</td><td>{sv.irr_at_high:.1f}%</td></tr>"

    cashflow_rows = ""
    for cf in f.cash_flow:
        cashflow_rows += f"<tr><td>{cf.year}</td><td>${cf.revenue:,.0f}</td><td>${cf.opex:,.0f}</td><td>${cf.replacements:,.0f}</td><td>${cf.net_cash_flow:,.0f}</td><td>${cf.cumulative:,.0f}</td></tr>"

    load_profile_bars = ""
    max_kw = max(d.load_profile_kw) if d.load_profile_kw else 1
    for hour, kw in enumerate(d.load_profile_kw):
        pct = (kw / max_kw) * 100 if max_kw > 0 else 0
        load_profile_bars += f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;"><span style="width:40px;font-size:11px;text-align:right;">{hour:02d}:00</span><div style="height:14px;background:#38a169;border-radius:2px;width:{pct}%;"></div><span style="font-size:11px;">{kw:.1f}</span></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Prefeasibility Report — {r.site.name or "Site"}</title>
<style>
  @page {{ margin: 20mm; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1a202c; line-height: 1.5; max-width: 900px; margin: 0 auto; padding: 20px; font-size: 13px; }}
  h1 {{ color: #2f855a; margin-bottom: 4px; font-size: 24px; }}
  h2 {{ color: #2d3748; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; margin-top: 28px; font-size: 16px; }}
  h3 {{ color: #4a5568; font-size: 14px; margin-top: 16px; }}
  .subtitle {{ color: #718096; font-size: 14px; margin-bottom: 20px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }}
  .metric {{ background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center; }}
  .metric .value {{ font-size: 22px; font-weight: 700; color: #2f855a; }}
  .metric .label {{ font-size: 11px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px; }}
  th {{ background: #2f855a; color: white; padding: 6px 10px; text-align: left; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #e2e8f0; }}
  tr:nth-child(even) {{ background: #f7fafc; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
  .info-row {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #edf2f7; }}
  .info-label {{ color: #718096; }}
  .info-value {{ font-weight: 600; }}
  .risk-badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 12px; }}
  .risk-low {{ background: #c6f6d5; color: #22543d; }}
  .risk-medium {{ background: #fefcbf; color: #744210; }}
  .risk-high {{ background: #fed7d7; color: #822727; }}
  .risk-critical {{ background: #e53e3e; color: white; }}
  .page-break {{ page-break-before: always; }}
  .footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #e2e8f0; color: #a0aec0; font-size: 11px; text-align: center; }}
</style>
</head>
<body>

<h1>Mini-Grid Prefeasibility Report</h1>
<p class="subtitle">{r.site.name or "Unnamed Site"} &mdash; ({r.site.latitude:.4f}, {r.site.longitude:.4f})</p>

{warnings_html}

<h2>Executive Summary</h2>
<div class="metrics">
  <div class="metric"><div class="value">${f.lcoe_usd_kwh:.3f}</div><div class="label">LCOE ($/kWh)</div></div>
  <div class="metric"><div class="value">{f.irr_pct:.1f}%</div><div class="label">Project IRR</div></div>
  <div class="metric"><div class="value">${f.total_capex_usd:,.0f}</div><div class="label">Total CAPEX</div></div>
  <div class="metric"><div class="value">${f.npv_usd:,.0f}</div><div class="label">NPV</div></div>
  <div class="metric"><div class="value">{f.payback_years:.1f} yr</div><div class="label">Payback</div></div>
  <div class="metric"><div class="value">{f.dscr:.2f}</div><div class="label">DSCR</div></div>
</div>

<h2>Site Description</h2>
<div class="info-grid">
  <div>
    {"<div class='info-row'><span class='info-label'>Settlement</span><span class='info-value'>" + cl.village_name + "</span></div>" if cl.village_name else ""}
    {"<div class='info-row'><span class='info-label'>Province</span><span class='info-value'>" + cl.admin_region + "</span></div>" if cl.admin_region else ""}
    {"<div class='info-row'><span class='info-label'>District</span><span class='info-value'>" + cl.admin_district + "</span></div>" if cl.admin_district else ""}
    <div class="info-row"><span class="info-label">Classification</span><span class="info-value">{urban_label}</span></div>
    <div class="info-row"><span class="info-label">Population</span><span class="info-value">{cl.population:,}</span></div>
    <div class="info-row"><span class="info-label">Area</span><span class="info-value">{cl.area_km2:.3f} km&sup2;</span></div>
  </div>
  <div>
    {"<div class='info-row'><span class='info-label'>Buildings</span><span class='info-value'>" + f"{cl.num_buildings:,}" + "</span></div>" if cl.num_buildings else ""}
    {"<div class='info-row'><span class='info-label'>Est. Connections</span><span class='info-value'>" + f"{cl.dre_num_connections:,}" + "</span></div>" if cl.dre_num_connections else ""}
    <div class="info-row"><span class="info-label">Solar PV Potential</span><span class="info-value">{cl.ghi_kwh_m2_year:.0f} kWh/kWp/yr</span></div>
    <div class="info-row"><span class="info-label">Existing Grid</span><span class="info-value">{cl.dist_grid_mv_km:.1f} km</span></div>
    {"<div class='info-row'><span class='info-label'>Planned Grid</span><span class='info-value'>" + f"{cl.dist_grid_planned_km:.1f} km" + "</span></div>" if cl.dist_grid_planned_km else ""}
    <div class="info-row"><span class="info-label">Road Distance</span><span class="info-value">{cl.dist_road_km:.1f} km</span></div>
    <div class="info-row"><span class="info-label">Nightlight</span><span class="info-value">{"Yes (" + f"{cl.nightlight_overlap_pct:.0f}% coverage)" if cl.has_nightlight else "No"}</span></div>
  </div>
</div>

{"<h3>Socioeconomic Context</h3><div class='info-grid'><div>" +
  (f"<div class='info-row'><span class='info-label'>Wealth Index (RWI)</span><span class='info-value'>{cl.mean_rwi:.2f}</span></div>" if cl.mean_rwi is not None else "") +
  ("<div class='info-row'><span class='info-label'>Education</span><span class='info-value'>Yes (" + str(cl.num_education_facilities) + ")</span></div>" if cl.has_education_facility else "<div class='info-row'><span class='info-label'>Education</span><span class='info-value'>None nearby</span></div>") +
  ("<div class='info-row'><span class='info-label'>Healthcare</span><span class='info-value'>Yes (" + str(cl.num_health_facilities) + ")</span></div>" if cl.has_health_facility else "<div class='info-row'><span class='info-label'>Healthcare</span><span class='info-value'>None nearby</span></div>") +
  "</div><div>" +
  (f"<div class='info-row'><span class='info-label'>Main Crops</span><span class='info-value'>{cl.crop_types}</span></div>" if cl.crop_types else "") +
  (f"<div class='info-row'><span class='info-label'>Security Risk</span><span class='info-value'><span class='risk-badge risk-{cl.security_risk}'>{cl.security_risk.upper()}</span></span></div>" if cl.security_risk else "") +
  (f"<div class='info-row'><span class='info-label'>Nearest Hub</span><span class='info-value'>{cl.nearest_hub_name} ({cl.dist_nearest_hub_km:.0f} km)</span></div>" if cl.nearest_hub_name else "") +
  "</div></div>" if any([cl.mean_rwi, cl.crop_types, cl.security_risk, cl.nearest_hub_name]) else ""}

<h2>Demand Analysis</h2>
<div class="info-grid">
  <div>
    <div class="info-row"><span class="info-label">Households</span><span class="info-value">{d.households}</span></div>
    <div class="info-row"><span class="info-label">Demand Tier (MTF)</span><span class="info-value">Tier {d.demand_tier}</span></div>
    <div class="info-row"><span class="info-label">Persons / Household</span><span class="info-value">{d.persons_per_hh}</span></div>
  </div>
  <div>
    <div class="info-row"><span class="info-label">Daily Energy</span><span class="info-value">{d.daily_energy_kwh:.1f} kWh</span></div>
    <div class="info-row"><span class="info-label">Annual Energy</span><span class="info-value">{d.annual_energy_kwh:,.0f} kWh</span></div>
    <div class="info-row"><span class="info-label">Peak Demand</span><span class="info-value">{d.peak_demand_kw:.1f} kW</span></div>
  </div>
</div>

<h3>24-Hour Load Profile (kW)</h3>
{load_profile_bars}

<div class="page-break"></div>

<h2>System Sizing</h2>
<table>
  <thead><tr><th>Component</th><th>Size</th><th>Unit</th></tr></thead>
  <tbody>
    <tr><td>PV Array</td><td>{s.pv_kwp:.1f}</td><td>kWp</td></tr>
    <tr><td>Battery (Nominal)</td><td>{s.battery_kwh_nominal:.0f}</td><td>kWh</td></tr>
    <tr><td>Battery (Usable)</td><td>{s.battery_kwh_usable:.0f}</td><td>kWh</td></tr>
    <tr><td>Inverter</td><td>{s.inverter_kva:.1f}</td><td>kVA</td></tr>
    <tr><td>LV Distribution</td><td>{s.lv_line_km:.1f}</td><td>km</td></tr>
    <tr><td>Transformers (50 kVA)</td><td>{s.service_transformers}</td><td>units</td></tr>
    <tr><td>Meters</td><td>{s.meters}</td><td>units</td></tr>
  </tbody>
</table>

{f'''<h3>Dispatch Simulation Results</h3>
<div class="info-grid">
  <div>
    <div class="info-row"><span class="info-label">Annual Generation</span><span class="info-value">{s.annual_generation_kwh:,.0f} kWh</span></div>
    <div class="info-row"><span class="info-label">Energy Served</span><span class="info-value">{s.annual_energy_served_kwh:,.0f} kWh</span></div>
    <div class="info-row"><span class="info-label">Unmet Demand</span><span class="info-value">{s.unmet_energy_pct:.1f}%</span></div>
  </div>
  <div>
    <div class="info-row"><span class="info-label">Curtailment</span><span class="info-value">{s.curtailment_pct:.1f}%</span></div>
    <div class="info-row"><span class="info-label">Capacity Factor</span><span class="info-value">{s.capacity_factor_pct:.1f}%</span></div>
    <div class="info-row"><span class="info-label">Battery Cycles/yr</span><span class="info-value">{s.battery_cycles_per_year:.0f}</span></div>
  </div>
</div>''' if s.annual_generation_kwh else ''}

{f'''<h3>Solar Resource</h3>
<div class="info-grid">
  <div>
    <div class="info-row"><span class="info-label">Annual GHI</span><span class="info-value">{sol.annual_ghi_kwh_m2:.0f} kWh/m&sup2;/yr</span></div>
    <div class="info-row"><span class="info-label">Specific Yield</span><span class="info-value">{sol.specific_yield_kwh_per_kwp:.0f} kWh/kWp</span></div>
  </div>
  <div>
    <div class="info-row"><span class="info-label">Performance Ratio</span><span class="info-value">{sol.performance_ratio:.1%}</span></div>
    <div class="info-row"><span class="info-label">Data Source</span><span class="info-value">{sol.data_source}</span></div>
  </div>
</div>''' if sol else ''}

<h2>CAPEX Breakdown</h2>
<table>
  <thead><tr><th>Component</th><th>Cost (USD)</th><th>% of Total</th></tr></thead>
  <tbody>
    {"".join(f'<tr><td>{label}</td><td>${cost:,.0f}</td><td>{cost/f.total_capex_usd*100:.1f}%</td></tr>' for label, cost in capex_items)}
    <tr style="font-weight:bold;border-top:2px solid #2f855a;"><td>Total</td><td>${f.total_capex_usd:,.0f}</td><td>100%</td></tr>
  </tbody>
</table>

<h2>Tariff & Affordability</h2>
<div class="info-grid">
  <div>
    <div class="info-row"><span class="info-label">Cost-Reflective Tariff</span><span class="info-value">${f.cost_reflective_tariff_usd:.4f}/kWh</span></div>
    <div class="info-row"><span class="info-label">Affordable Tariff</span><span class="info-value">${f.affordable_tariff_usd:.3f}/kWh</span></div>
  </div>
  <div>
    <div class="info-row"><span class="info-label">Subsidy Gap / Connection</span><span class="info-value">${f.subsidy_gap_per_connection_usd:,.0f}</span></div>
    <div class="info-row"><span class="info-label">Total Subsidy Gap</span><span class="info-value">${f.subsidy_gap_total_usd:,.0f} ({f.subsidy_gap_pct_capex:.1f}% CAPEX)</span></div>
  </div>
</div>

<h2>Sensitivity Analysis (&plusmn;20%)</h2>
<table>
  <thead><tr><th>Parameter</th><th>IRR @ -20%</th><th>IRR @ Base</th><th>IRR @ +20%</th></tr></thead>
  <tbody>{sensitivity_rows}</tbody>
</table>

{f'''<h2>Financing Structure</h2>
<div class="info-grid">
  <div>
    <div class="info-row"><span class="info-label">Grant / Subsidy</span><span class="info-value">${f.grant_amount_usd:,.0f} ({f.subsidy_gap_pct_capex:.0f}%)</span></div>
    <div class="info-row"><span class="info-label">Concessional Debt</span><span class="info-value">${f.debt_amount_usd:,.0f}</span></div>
    <div class="info-row"><span class="info-label">Equity</span><span class="info-value">${f.equity_amount_usd:,.0f}</span></div>
  </div>
  <div>
    <div class="info-row"><span class="info-label">CAPEX / Wp</span><span class="info-value">${f.capex_per_wp:.2f}</span></div>
    <div class="info-row"><span class="info-label">Annual OPEX</span><span class="info-value">${f.annual_opex_usd:,.0f}</span></div>
    <div class="info-row"><span class="info-label">Equity IRR</span><span class="info-value">{f.equity_irr_pct:.1f}%</span></div>
  </div>
</div>''' if f.grant_amount_usd is not None else ''}

{f'''<h2>Carbon Assessment</h2>
<div class="info-grid">
  <div>
    <div class="info-row"><span class="info-label">Annual Reductions</span><span class="info-value">{carb.annual_emission_reductions_tco2e:.1f} tCO2e/yr</span></div>
    <div class="info-row"><span class="info-label">Diesel Displaced</span><span class="info-value">{carb.diesel_displaced_litres_yr:,.0f} litres/yr</span></div>
    <div class="info-row"><span class="info-label">Methodology</span><span class="info-value">{carb.recommended_methodology}</span></div>
  </div>
  <div>
    <div class="info-row"><span class="info-label">Revenue (Market $12/t)</span><span class="info-value">${carb.revenue_by_scenario.get("market", 0):,.0f}/yr</span></div>
    <div class="info-row"><span class="info-label">Revenue NPV (Market)</span><span class="info-value">${carb.npv_carbon_revenue.get("market", 0):,.0f}</span></div>
    <div class="info-row"><span class="info-label">Crediting Period</span><span class="info-value">{carb.crediting_period_years} years</span></div>
  </div>
</div>
{"".join(f"<div style=&quot;color:#d69e2e;font-size:12px;margin:4px 0;&quot;>⚠ {w}</div>" for w in carb.warnings)}''' if carb else ''}

<h2>Grid Risk Assessment</h2>
<div class="info-row"><span class="info-label">Distance to MV Grid</span><span class="info-value">{gr.dist_mv_km:.1f} km</span></div>
<div class="info-row"><span class="info-label">Distance to HV Grid</span><span class="info-value">{gr.dist_hv_km:.1f} km</span></div>
<div class="info-row"><span class="info-label">Risk Level</span><span class="info-value"><span class="risk-badge risk-{gr.risk_level}">{gr.risk_level.upper()}</span></span></div>
<div class="info-row"><span class="info-label">Assessment</span><span class="info-value">{gr.risk_label}</span></div>
{f'<div class="info-row"><span class="info-label">ESMAP Strategy</span><span class="info-value">{gr.esmap_recommended}</span></div>' if gr.esmap_recommended else ''}
{f'<div class="info-row"><span class="info-label">Design Implications</span><span class="info-value">{gr.design_implications}</span></div>' if gr.design_implications else ''}
{scenarios_html}

<div class="page-break"></div>

<h2>Cash Flow Projection (25 Years)</h2>
<table>
  <thead><tr><th>Year</th><th>Revenue</th><th>OPEX</th><th>Replacements</th><th>Net Cash Flow</th><th>Cumulative</th></tr></thead>
  <tbody>{cashflow_rows}</tbody>
</table>

<div class="footer">
  Generated by Moz Mini-Grid Prefeasibility Platform &mdash; Mozambique<br>
  This report is for indicative planning purposes only. All figures should be validated through detailed on-site assessment.
</div>

</body>
</html>"""
