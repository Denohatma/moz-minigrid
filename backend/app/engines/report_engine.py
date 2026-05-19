from __future__ import annotations

from app.schemas.analysis import AnalysisResult


def _risk_badge(level: str) -> str:
    """Return an inline risk-badge span for the given level string."""
    norm = level.lower().replace(" ", "_")
    css_class = "risk-low"
    if norm in ("high", "very_high", "substantial"):
        css_class = "risk-high"
    elif norm in ("medium", "moderate", "peri-urban"):
        css_class = "risk-medium"
    elif norm in ("critical",):
        css_class = "risk-critical"
    return f'<span class="risk-badge {css_class}">{level.upper()}</span>'


def _relevance_badge(relevance: str) -> str:
    """Return a coloured badge for productive-use relevance."""
    colors = {
        "high": ("background:#c6f6d5;color:#22543d;", "HIGH"),
        "medium": ("background:#fefcbf;color:#744210;", "MEDIUM"),
        "low": ("background:#fed7d7;color:#822727;", "LOW"),
        "none": ("background:#e2e8f0;color:#4a5568;", "NONE"),
    }
    style, label = colors.get(relevance.lower(), ("background:#e2e8f0;color:#4a5568;", relevance.upper()))
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;font-weight:600;font-size:12px;{style}">{label}</span>'


def _data_quality_badge(quality: str) -> str:
    """Return a coloured badge for data quality."""
    colors = {
        "high": "background:#c6f6d5;color:#22543d;",
        "medium": "background:#fefcbf;color:#744210;",
        "low": "background:#fed7d7;color:#822727;",
    }
    style = colors.get(quality.lower(), "background:#e2e8f0;color:#4a5568;")
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;font-weight:600;font-size:12px;{style}">{quality.upper()}</span>'


def _hazard_level_color(level: str) -> str:
    """Return an inline background-color style for a hazard level."""
    mapping = {
        "very_high": "background:#e53e3e;color:white;",
        "high": "background:#ed8936;color:white;",
        "moderate": "background:#ecc94b;color:#744210;",
        "low": "background:#48bb78;color:white;",
        "negligible": "background:#a0aec0;color:white;",
    }
    return mapping.get(level.lower(), "background:#e2e8f0;color:#4a5568;")


def _score_bar(score: int, max_score: int = 100) -> str:
    """Return an inline progress-bar showing a confidence score."""
    pct = min(score / max_score * 100, 100) if max_score > 0 else 0
    color = "#38a169" if pct >= 70 else "#ecc94b" if pct >= 40 else "#e53e3e"
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="flex:1;background:#e2e8f0;border-radius:4px;height:12px;overflow:hidden;">'
        f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:4px;"></div>'
        f'</div>'
        f'<span style="font-weight:600;font-size:12px;min-width:36px;">{score}</span></div>'
    )


def _build_productive_use_section(pu) -> str:
    """Build the Productive Use Value Chain section HTML."""
    html = '<div class="page-break"></div>\n<h2>Productive Use Value Chain</h2>\n'

    # Sectors table
    if pu.sectors:
        rows = ""
        for sec in pu.sectors:
            activities = ", ".join(sec.indicative_activities) if sec.indicative_activities else "—"
            rows += (
                f"<tr><td>{sec.sector}</td>"
                f"<td>{_relevance_badge(sec.relevance)}</td>"
                f"<td style='font-size:11px;'>{sec.rationale}</td>"
                f"<td style='font-size:11px;'>{activities}</td>"
                f"<td style='text-align:right;'>{sec.estimated_demand_kwh_day:.1f}</td></tr>"
            )
        html += (
            "<h3>Relevant Sectors</h3>\n"
            "<table><thead><tr><th>Sector</th><th>Relevance</th><th>Rationale</th>"
            "<th>Indicative Activities</th><th>Est. Demand (kWh/day)</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Summary metrics
    html += (
        '<div class="metrics">\n'
        f'  <div class="metric"><div class="value">{pu.total_productive_demand_kwh_day:.1f}</div><div class="label">Productive Demand (kWh/day)</div></div>\n'
        f'  <div class="metric"><div class="value">{pu.productive_demand_pct:.1f}%</div><div class="label">Productive Share of Total Demand</div></div>\n'
        f'  <div class="metric"><div class="value">${pu.incremental_income_usd_year:,.0f}</div><div class="label">Incremental Income ($/yr)</div></div>\n'
        '</div>\n'
    )

    # Anchor customers
    if pu.anchors:
        rows = ""
        for a in pu.anchors:
            rows += (
                f"<tr><td>{a.type}</td><td>{a.name}</td>"
                f"<td style='text-align:right;'>{a.estimated_demand_kwh_day:.1f}</td>"
                f"<td style='text-align:right;'>{a.estimated_peak_kw:.1f}</td>"
                f"<td>{_data_quality_badge(a.confidence)}</td>"
                f"<td>{a.contract_type}</td></tr>"
            )
        html += (
            "<h3>Anchor Customers</h3>\n"
            "<table><thead><tr><th>Type</th><th>Name</th><th>Demand (kWh/day)</th>"
            "<th>Peak (kW)</th><th>Confidence</th><th>Contract</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Equipment recommendations
    if pu.equipment_recommendations:
        rows = ""
        for eq in pu.equipment_recommendations:
            rows += (
                f"<tr><td>{eq.sector}</td><td>{eq.equipment}</td>"
                f"<td style='text-align:right;'>{eq.power_kw:.1f}</td>"
                f"<td style='text-align:right;'>${eq.capex_usd_low:,.0f} – ${eq.capex_usd_high:,.0f}</td>"
                f"<td>{eq.ownership_model}</td></tr>"
            )
        html += (
            "<h3>Equipment Recommendations</h3>\n"
            "<table><thead><tr><th>Sector</th><th>Equipment</th><th>Power (kW)</th>"
            "<th>CAPEX Range (USD)</th><th>Ownership Model</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Complementary investment summary
    ci = pu.complementary_investment_usd
    if ci:
        html += '<h3>Complementary Investment Required</h3>\n<div class="info-grid"><div>\n'
        for key in ("equipment", "working_capital", "market_access", "training"):
            if key in ci:
                label = key.replace("_", " ").title()
                html += f'<div class="info-row"><span class="info-label">{label}</span><span class="info-value">${ci[key]:,.0f}</span></div>\n'
        html += '</div><div>\n'
        if "total" in ci:
            html += f'<div class="info-row"><span class="info-label">Total Complementary Investment</span><span class="info-value" style="color:#2f855a;font-size:16px;">${ci["total"]:,.0f}</span></div>\n'
        html += '</div></div>\n'

    # Jobs and income
    jobs = pu.jobs
    if jobs:
        html += '<h3>Employment Impact</h3>\n<div class="metrics">\n'
        if "direct" in jobs:
            html += f'  <div class="metric"><div class="value">{jobs["direct"]}</div><div class="label">Direct Jobs</div></div>\n'
        if "indirect" in jobs:
            html += f'  <div class="metric"><div class="value">{jobs["indirect"]}</div><div class="label">Indirect Jobs</div></div>\n'
        if "total" in jobs:
            html += f'  <div class="metric"><div class="value">{jobs["total"]}</div><div class="label">Total Jobs</div></div>\n'
        html += '</div>\n'

    return html


def _build_ess_section(ess) -> str:
    """Build the Environmental & Social Safeguards section HTML."""
    html = '<div class="page-break"></div>\n<h2>Environmental &amp; Social Safeguards</h2>\n'

    # ESIA category as prominent badge
    cat_colors = {
        "A": "background:#e53e3e;color:white;",
        "B+": "background:#ed8936;color:white;",
        "B": "background:#ecc94b;color:#744210;",
        "C": "background:#48bb78;color:white;",
    }
    cat_style = cat_colors.get(ess.esia_category, "background:#e2e8f0;color:#4a5568;")
    html += (
        f'<div style="margin:12px 0;padding:12px;background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;">'
        f'<span style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.5px;">ESIA Category</span> '
        f'<span style="display:inline-block;padding:4px 16px;border-radius:12px;font-weight:700;font-size:18px;{cat_style}">{ess.esia_category}</span>'
        f'<p style="margin:8px 0 0;font-size:12px;color:#4a5568;">{ess.esia_rationale}</p></div>\n'
    )

    # Key risk indicators
    html += '<div class="info-grid"><div>\n'
    html += f'<div class="info-row"><span class="info-label">Biodiversity Sensitivity</span><span class="info-value">{_risk_badge(ess.biodiversity_sensitivity)}</span></div>\n'
    html += f'<div class="info-row"><span class="info-label">Resettlement Risk</span><span class="info-value">{_risk_badge(ess.resettlement_risk)}</span></div>\n'
    html += f'<div class="info-row"><span class="info-label">Overall ESS Risk</span><span class="info-value">{_risk_badge(ess.overall_ess_risk)}</span></div>\n'
    html += '</div><div>\n'

    if ess.labour_safety_risks:
        html += '<div class="info-row"><span class="info-label">Labour Safety Risks</span><span class="info-value" style="font-size:11px;">' + "; ".join(ess.labour_safety_risks) + '</span></div>\n'
    if ess.community_safety_risks:
        html += '<div class="info-row"><span class="info-label">Community Safety Risks</span><span class="info-value" style="font-size:11px;">' + "; ".join(ess.community_safety_risks) + '</span></div>\n'

    html += '</div></div>\n'

    # Protected area checks
    if ess.protected_area_checks:
        rows = ""
        for pa in ess.protected_area_checks:
            rows += (
                f"<tr><td>{pa.area_name}</td>"
                f"<td style='text-align:right;'>{pa.distance_km:.1f} km</td>"
                f"<td>{'Yes' if pa.buffer_zone else 'No'}</td>"
                f"<td>{_risk_badge(pa.sensitivity)}</td></tr>"
            )
        html += (
            "<h3>Protected Area Proximity</h3>\n"
            "<table><thead><tr><th>Protected Area</th><th>Distance</th><th>Buffer Zone</th>"
            "<th>Sensitivity</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Stakeholder groups
    if ess.stakeholder_groups:
        html += '<h3>Stakeholder Groups</h3>\n<div style="margin:6px 0;">\n'
        for sg in ess.stakeholder_groups:
            html += f'<span style="display:inline-block;padding:3px 10px;margin:3px;background:#edf2f7;border-radius:12px;font-size:12px;">{sg}</span>\n'
        html += '</div>\n'

    # GESI considerations
    if ess.gesi_considerations:
        html += '<h3>Gender Equality &amp; Social Inclusion</h3>\n<ul style="font-size:12px;">\n'
        for g in ess.gesi_considerations:
            html += f'  <li>{g}</li>\n'
        html += '</ul>\n'

    # Women's empowerment
    if ess.womens_empowerment_opportunities:
        html += "<h3>Women's Empowerment Opportunities</h3>\n<ul style=\"font-size:12px;\">\n"
        for w in ess.womens_empowerment_opportunities:
            html += f'  <li>{w}</li>\n'
        html += '</ul>\n'

    # Recommended actions
    if ess.recommended_actions:
        html += '<h3>Recommended ESS Actions</h3>\n<ol style="font-size:12px;">\n'
        for a in ess.recommended_actions:
            html += f'  <li>{a}</li>\n'
        html += '</ol>\n'

    return html


def _build_climate_section(climate) -> str:
    """Build the Climate Rationale section HTML."""
    html = '<div class="page-break"></div>\n<h2>Climate Rationale</h2>\n'

    # Headline metrics
    html += (
        '<div class="metrics">\n'
        f'  <div class="metric"><div class="value">{climate.lifetime_avoided_tco2e:,.0f}</div><div class="label">Lifetime Avoided tCO2e</div></div>\n'
        f'  <div class="metric"><div class="value">{climate.per_capita_reduction_tco2e:.2f}</div><div class="label">Per Capita Reduction (tCO2e)</div></div>\n'
        f'  <div class="metric"><div class="value">${climate.total_climate_finance_potential_usd:,.0f}</div><div class="label">Climate Finance Potential</div></div>\n'
        '</div>\n'
    )

    # NDC alignment narrative
    html += (
        '<h3>NDC Alignment</h3>\n'
        f'<div style="padding:8px 12px;background:#f7fafc;border-left:3px solid #2f855a;font-size:12px;margin:8px 0;">{climate.ndc_alignment}</div>\n'
    )

    # Adaptation narrative
    html += (
        '<h3>Adaptation Narrative</h3>\n'
        f'<div style="padding:8px 12px;background:#f7fafc;border-left:3px solid #3182ce;font-size:12px;margin:8px 0;">{climate.adaptation_narrative}</div>\n'
    )

    # Hazard exposure table
    if climate.hazards:
        rows = ""
        for h in climate.hazards:
            lvl_style = _hazard_level_color(h.level)
            rows += (
                f"<tr><td>{h.hazard.replace('_', ' ').title()}</td>"
                f'<td><span style="display:inline-block;padding:2px 10px;border-radius:12px;font-weight:600;font-size:12px;{lvl_style}">{h.level.replace("_", " ").upper()}</span></td>'
                f"<td style='font-size:11px;'>{h.description}</td></tr>"
            )
        html += (
            f"<h3>Climate Hazard Exposure</h3>\n"
            f'<div class="info-row"><span class="info-label">Overall Hazard Level</span><span class="info-value">{_risk_badge(climate.overall_hazard_level)}</span></div>\n'
            "<table><thead><tr><th>Hazard</th><th>Level</th><th>Description</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Design resilience measures
    if climate.design_resilience_measures:
        html += '<h3>Design Resilience Measures</h3>\n<ul style="font-size:12px;">\n'
        for m in climate.design_resilience_measures:
            html += f'  <li>{m}</li>\n'
        html += '</ul>\n'

    # Climate finance eligibility table
    if climate.climate_finance:
        rows = ""
        for cf in climate.climate_finance:
            eligible_icon = '<span style="color:#38a169;font-weight:700;">&#10003;</span>' if cf.eligible else '<span style="color:#e53e3e;font-weight:700;">&#10007;</span>'
            rows += (
                f"<tr><td>{cf.instrument}</td>"
                f"<td style='text-align:center;'>{eligible_icon}</td>"
                f"<td style='font-size:11px;'>{cf.rationale}</td>"
                f"<td style='text-align:right;'>${cf.estimated_value_usd:,.0f}</td></tr>"
            )
        html += (
            f'<h3>Climate Finance Eligibility</h3>\n'
            f'<div class="info-row"><span class="info-label">Climate Finance Score</span><span class="info-value">{_risk_badge(climate.climate_finance_score)}</span></div>\n'
            "<table><thead><tr><th>Instrument</th><th>Eligible</th><th>Rationale</th>"
            "<th>Est. Value (USD)</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    return html


def _build_risk_section(ra) -> str:
    """Build the Comprehensive Risk Analysis section HTML."""
    html = '<div class="page-break"></div>\n<h2>Comprehensive Risk Analysis</h2>\n'

    # Overall risk level
    html += (
        f'<div style="margin:12px 0;padding:12px;background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;">'
        f'<span style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.5px;">Overall Risk Level</span> '
        f'{_risk_badge(ra.overall_risk_level)}'
        f'<span style="margin-left:16px;font-size:12px;color:#4a5568;">Score: {ra.overall_risk_score:.1f}</span></div>\n'
    )

    # Top risks callout
    if ra.top_risks:
        html += '<h3>Top Risks</h3>\n<ol style="font-size:12px;margin:4px 0;">\n'
        for tr in ra.top_risks[:3]:
            html += f'  <li style="margin-bottom:4px;">{tr}</li>\n'
        html += '</ol>\n'

    # Full risk matrix table
    if ra.risks:
        rows = ""
        for ri in ra.risks:
            mitigation_text = "; ".join(ri.mitigation) if ri.mitigation else "—"
            rows += (
                f"<tr><td>{ri.category.title()}</td>"
                f"<td style='font-size:11px;'>{ri.sub_risk}</td>"
                f"<td style='text-align:center;'>{ri.likelihood}</td>"
                f"<td style='text-align:center;'>{ri.impact}</td>"
                f"<td style='text-align:center;font-weight:600;'>{ri.risk_score}</td>"
                f"<td>{_risk_badge(ri.risk_level)}</td>"
                f"<td style='font-size:11px;'>{mitigation_text}</td>"
                f"<td style='font-size:11px;'>{ri.allocation}</td></tr>"
            )
        html += (
            "<h3>Risk Matrix</h3>\n"
            "<table><thead><tr><th>Category</th><th>Sub-Risk</th><th>L</th><th>I</th>"
            "<th>Score</th><th>Level</th><th>Mitigation</th><th>Allocation</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Risk allocation summary
    ras = ra.risk_allocation_summary
    if ras:
        html += '<h3>Risk Allocation Summary</h3>\n<div class="info-grid"><div>\n'
        for party, count in ras.items():
            html += f'<div class="info-row"><span class="info-label">{party.title()}</span><span class="info-value">{count}</span></div>\n'
        html += '</div><div></div></div>\n'

    return html


def _build_confidence_section(conf) -> str:
    """Build the Confidence Scoring section HTML."""
    html = '<div class="page-break"></div>\n<h2>Confidence Scoring</h2>\n'

    # Overall confidence headline
    html += (
        '<div style="margin:12px 0;padding:12px;background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;">'
        f'<span style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.5px;">Overall Confidence</span> '
        f'{_score_bar(conf.overall_confidence_score)}'
        f'<div style="margin-top:6px;">'
        f'{_risk_badge(conf.overall_confidence_level)}'
        f'<span style="margin-left:16px;font-size:12px;color:#4a5568;">Data Completeness: {conf.data_completeness_pct:.0f}%</span></div></div>\n'
    )

    # Dimensions table
    if conf.dimensions:
        rows = ""
        for dim in conf.dimensions:
            rows += (
                f"<tr><td>{dim.dimension}</td>"
                f"<td style='min-width:160px;'>{_score_bar(dim.confidence_score)}</td>"
                f"<td style='text-align:right;'>&plusmn;{dim.margin_of_error_pct:.1f}%</td>"
                f"<td>{_data_quality_badge(dim.data_quality)}</td></tr>"
            )
        html += (
            "<h3>Confidence Dimensions</h3>\n"
            "<table><thead><tr><th>Dimension</th><th>Score</th><th>Margin of Error</th>"
            "<th>Data Quality</th></tr></thead>\n"
            f"<tbody>{rows}</tbody></table>\n"
        )

    # Recommendations
    if conf.recommendations:
        html += '<h3>Recommendations to Improve Confidence</h3>\n<ol style="font-size:12px;">\n'
        for rec in conf.recommendations:
            html += f'  <li>{rec}</li>\n'
        html += '</ol>\n'

    return html


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

    # Build optional TOR-required sections
    productive_use_html = _build_productive_use_section(r.productive_use) if r.productive_use else ""
    ess_html = _build_ess_section(r.ess) if r.ess else ""
    climate_html = _build_climate_section(r.climate) if r.climate else ""
    risk_analysis_html = _build_risk_section(r.risk_analysis) if r.risk_analysis else ""
    confidence_html = _build_confidence_section(r.confidence) if r.confidence else ""

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

{productive_use_html}

{ess_html}

{climate_html}

{risk_analysis_html}

{confidence_html}

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
