"""AFUR Technical Guide knowledge base.

Extracted from: "Principles for the Toolbox of African Model Mini-Grid
Regulations — A Technical Guide" (AFUR / GET.transform, December 2023).

This module provides structured policy and technical knowledge that the
chat assistant uses to answer regulatory, design, and affordability questions.
"""
from __future__ import annotations

from typing import Optional

AFUR_KNOWLEDGE = """
# AFUR Model Mini-Grid Regulations — Technical Guide (Key Knowledge)

Source: African Forum for Utility Regulators (AFUR) & GET.transform, December 2023.
Funded by UKAid TEA Platform and EU GET.transform programme.

## 1. The Safety-Reliability-Affordability Triangle

Mini-grid regulations set technical, financial, and legal requirements that are
interdependent. The regulator must find a "sweet spot" balancing three pillars:

- **Safety**: Health and safety of the system, components, installation, and operation.
- **Reliability**: Service availability and power quality measured in hours/day and outages.
- **Affordability**: The tariff level that results from capital and operating expenditure.

These form a zero-sum game at a given technology level: pushing any one boundary
adversely affects the others. A very safe system is expensive (less affordable).
A highly reliable system needs skilled staff and spare parts (higher OPEX, higher tariff).
A highly affordable system cuts corners on safety or reliability.

The regulator's goal is to find the sweet spot within the triangle using a
data-driven, bottom-up approach rather than imposing urban-grade standards on
rural mini-grids.

## 2. Technical Aspects in Mini-Grid Regulations

### 2.1 Generation
Guidelines and requirements for PV, batteries, inverters, and other generation assets.
Regulations may reference IEC 62257 (overall system), IEC 61215 (PV modules),
IEC 61427-1 (batteries). Health and safety covered across development stages.

### 2.2 Distribution
Interconnection guidelines, power quality standards, availability requirements,
and reliability targets.

### 2.3 Consumer / Service Quality
Standards for metering, billing, service levels, and complaint handling.

### 2.4 Availability and Reliability
Quantified by:
- Technical availability: hours/day operational (not under repair/maintenance).
- Reliability: interruption frequency and duration (planned + unplanned).

Two perspectives:
- Power generation vs demand: relates to inverter capacity and backup generator.
  Power shortages cause shutdowns.
- Energy vs demand: relates to PV capacity and battery storage. Energy shortages
  cause rationing.

### 2.5 Interconnection Requirements
If mini-grid is within 5-20 km of advancing main grid, it may need to be
grid-interconnection ready. This can increase distribution CAPEX up to 25-38%.
Components: greater cable cross-section, MV transformer, LV switchgear,
higher-rated breakers at customer end.

### 2.6 Technical Reporting
Regulators require performance reporting. Digital tools can automate this.
Too-frequent reporting requirements increase overhead costs and tariff.

## 3. Reliability and Affordability

### 3.1 Availability and Tariff Impact
- **99.9% availability**: tariff ~$1.4/kWh. Requires full local warehouse,
  advanced call centre, on-site high-level electrician, spare inverters.
  Equivalent to Tier 5 ESMAP (8.76 hours outage/year).
- **99% availability**: ~87.6 hours outage/year. Still expensive.
- **95% availability**: limited local warehouse, advanced call centre.
  438 hours outage/year.
- **90% availability**: central warehouse only, simple call centre,
  no on-site staff. 876 hours outage/year = Tier 4. **Tariff ~$0.30/kWh**
  (the affordable target).
- **<90% availability**: central warehouse only, no on-site staff.
  Lower CAPEX but longer response times, more customer dissatisfaction.

Key finding: **For an affordable tariff of $0.30/kWh, regulators should target
~90% availability** (876 hours of planned + unplanned outage per year per
connection). This corresponds to ESMAP Tier 4.

Decision-making approach for availability:
1. Define an acceptable tariff level
2. Find industry CAPEX and OPEX benchmarks
3. Design mini-grids for different availability levels
4. Use tariff determination tool to find tariffs for each level
5. Select the availability level matching the acceptable tariff

### 3.2 Allowable Voltage Drop and Affordability
- Voltage drops along distribution lines cause appliances to underperform
  or become non-functional below a certain voltage.
- IEC 60038: supply voltage should not differ from nominal by more than ±10%.
- Bigger cable cross-section = lower losses but higher cost.
- If voltage drop requirement shifts from 5% to 15%, tariff reduces from
  $0.33/kWh to $0.29/kWh.
- The mini-grid can be divided into two zones:
  - Core zone (~1 km radius): full IEC 60038 compliance (±10%)
  - Outer zone: allow higher voltage drop for basic access only,
    with appliance restrictions and lower-voltage-compatible devices.
- Regulatory template: "Operators of mini-grids are allowed to connect
  clients in the most remote line extensions for basic access only,
  even if the supply voltage may constantly be lower than 10% of nominal."

### 3.3 Power Quality (Inverter Selection)
- The inverter is the "brain" of the mini-grid: sets voltage, frequency,
  balances demand and supply, provides reactive power.
- Low-quality inverters may fail handling high productive use loads,
  causing unwanted tripping, dust accumulation, poor ventilation,
  component failures (capacitors, DC breakers).
- Higher-end inverters handle harmonics better, are more costly but
  reduce OPEX through fewer failures.
- **Key finding**: proper inverters keep availability high and tariff sustainable.
  Cheap inverters result in frequent service interruptions and damage.

Power quality categorisation (3 levels):
1. **Basic** (rural households): standard voltage range, basic appliances
2. **Intermediate** (commercial): tighter voltage variation
3. **Advanced** (productive loads, critical loads): strictest standards,
   surge protection required, voltage variation ±5%, transient protection

Frequency regulation: ±1 Hz of nominal frequency. Most inverters use
active power control. Short-duration (<half cycle) and long-duration
(>1 minute) voltage variations: <1/day and <5/day for advanced categories.

### 3.4 Component Standards (Meters and Installation Boards)
Three meter types with different impacts:
- **Smart meters**: granular data, automatic recharge, reduced OPEX,
  increased CAPEX, data protection considerations. Examples: SparkMeter, SteamaCo.
- **Prepaid meters**: STS token or SMS based, reduced OPEX, lower CAPEX than smart.
  Examples: Inhemeter, Calin meter. Recommended as cost-effective.
- **Post-paid meters**: manual reading, lowest CAPEX but highest OPEX,
  collection risk, human resources needed.

Key takeaway: **Prepaid meters + rural ready-boards provide the best
cost-tariff balance** — as good as smart meters + rural boards on tariff impact.

Installation boards:
- Rural ready-board: fixed bulbs and load points, suitable for rural setup
- Urban ready-board: higher capacity breakers
- **Operators may install 5A or lower breakers instead of 16A/25A** for
  sufficient safety at lower cost.

### 3.5 Grid Interconnection Readiness
- Distribution CAPEX can increase up to **25-38%** if grid-interconnection
  ready design is required. Tariff impact: from $0.27/kWh to $0.37/kWh.
- Components needed: greater cable cross-section, MV transformer + switchgear,
  LV switchgear, higher-rated customer breakers (e.g. 16A).
- Decision approach:
  1. How far is the grid? Use electrification master plan.
  2. Find unelectrified areas within 5-20 km of main grid.
  3. Assess how fast grid is approaching.
  4. If grid arrival is likely, design for interconnection from start.
  5. If not, design standalone — can be upgraded later.
- Regulators should define different interconnection levels based on
  distance and grid advancement timeline.

## 4. Key Benchmarks and Numbers

| Parameter | Value | Source |
|-----------|-------|--------|
| Affordable tariff target | $0.30/kWh | AFUR/GET.transform simulations |
| 90% availability outage hours | 876 hrs/yr (Tier 4) | ESMAP Multi-tier Framework |
| 99.9% availability tariff | ~$1.40/kWh | AFUR simulations |
| Voltage drop impact on tariff | 5%→15% drop: $0.33→$0.29/kWh | AFUR simulations |
| Grid-interconnection CAPEX increase | 25-38% | AFUR simulations |
| Grid-interconnection tariff impact | $0.27→$0.37/kWh | AFUR simulations |
| IEC voltage tolerance | ±10% of nominal | IEC 60038 |
| Recommended breaker rating | 5A (rural) vs 16A/25A (urban) | AFUR recommendation |
| CAPEX subsidy baseline | 75% of total CAPEX | Simulation assumptions |
| Simulation customer count | 205 (single-phase 200, three-phase 5) | Annex I |
| Project lifetime (simulations) | 20 years | Annex I |

## 5. Decision-Making Frameworks

### Availability Level Selection
1. Define acceptable tariff level for local context
2. Find CAPEX/OPEX benchmarks from industry
3. Design mini-grids at different availability levels (80%, 85%, 90%, 95%, 99%)
4. Calculate tariffs for each design
5. Select availability matching acceptable tariff

### Voltage Level Selection
1. Define different connection groups by appliance type
2. Find allowable voltage range per group
3. Design for different voltage drop limits (5%, 10%, 15%, 20%)
4. Calculate tariffs per voltage drop level
5. Select voltage drop level balancing function and tariff

### Component Standard Selection
1. Allow prepaid meters (smart and STS) only — most cost-effective
2. Define appropriate breaker rating per consumer type
3. Select installation board type per consumer category (rural/urban)

### Interconnection Readiness
1. Find unelectrified areas within 5-20 km of main grid
2. Assess grid advancement speed
3. Design with/without interconnection readiness
4. Compare CAPEX and tariff difference
5. If difference is small, build interconnection-ready from start

## 6. Mozambique-Specific Context

Mozambique's mini-grid regulatory framework is administered by ARENE
(Autoridade Reguladora de Energia, formerly CNELEC). Key considerations:
- Most rural settlements are far from MV grid (>10 km median)
- Grid advancement is slow in many provinces (Cabo Delgado, Niassa, Zambezia)
- Security situation in northern provinces affects O&M costs and availability
- Productive use of energy is critical for financial sustainability
- FUNAE (Fundo de Energia) manages many existing mini-grids
- Concession regime requires ARENE licensing
- Tariff must be approved by ARENE (currently capped at regulated levels)
- Prepaid metering is increasingly standard
- 90% target availability is realistic for rural Mozambique mini-grids
"""

SYSTEM_PROMPT_TEMPLATE = """You are the Moz Platform AI Assistant — an expert on mini-grid
pre-feasibility analysis in Mozambique. You help developers, regulators, investors,
and analysts understand site data, design decisions, policy context, and financial viability.

You have access to:
1. The AFUR Technical Guide on mini-grid regulations (safety-reliability-affordability triangle)
2. Real settlement cluster data from the World Bank DRE Atlas
3. Analysis results from the platform's engineering models (solar resource, demand estimation,
   system sizing with 8,760-hour dispatch, distribution network design, financial DCF,
   carbon credits, productive use assessment, ESS screening, climate rationale, risk analysis)

When answering:
- Cite specific data from the current analysis when available
- Reference AFUR guide principles when discussing policy, regulation, or design tradeoffs
- Use concrete numbers: tariff ranges, CAPEX benchmarks, voltage drop limits
- If the user asks about changing parameters, explain the engineering impact and suggest
  specific values they can enter in the Optimize panel
- Be direct and technical — your audience understands energy engineering
- When uncertain, say so and explain what data would be needed

{policy_knowledge}

{site_context}
"""


def build_system_prompt(analysis_result: Optional[dict] = None,
                        cluster: Optional[dict] = None) -> str:
    site_context = ""
    if analysis_result:
        site_context = _format_analysis_context(analysis_result)
    elif cluster:
        site_context = _format_cluster_context(cluster)

    return SYSTEM_PROMPT_TEMPLATE.format(
        policy_knowledge=AFUR_KNOWLEDGE,
        site_context=site_context,
    )


def _format_cluster_context(cluster: dict) -> str:
    lines = ["## Current Site Data (cluster only — no full analysis yet)"]
    lines.append(f"- Settlement: {cluster.get('village_name', 'Unknown')}")
    lines.append(f"- Province: {cluster.get('admin_region', '?')}, District: {cluster.get('admin_district', '?')}")
    lines.append(f"- Population: {cluster.get('population', '?')}")
    lines.append(f"- Buildings: {cluster.get('num_buildings', '?')}")
    lines.append(f"- Area: {cluster.get('area_km2', '?')} km²")
    lines.append(f"- GHI: {cluster.get('ghi_kwh_m2_year', '?')} kWh/m²/yr")
    lines.append(f"- Distance to MV grid: {cluster.get('dist_grid_mv_km', '?')} km")
    lines.append(f"- Distance to planned grid: {cluster.get('dist_grid_planned_km', '?')} km")
    lines.append(f"- Distance to road: {cluster.get('dist_road_km', '?')} km")
    lines.append(f"- Mean RWI: {cluster.get('mean_rwi', '?')}")
    lines.append(f"- Security risk: {cluster.get('security_risk', '?')}")
    lines.append(f"- Nightlight: {'Yes' if cluster.get('has_nightlight') else 'No'}")
    if cluster.get('crop_types'):
        lines.append(f"- Crops: {cluster['crop_types']}")
    return "\n".join(lines)


def _format_analysis_context(result: dict) -> str:
    lines = ["## Current Analysis Results"]

    site = result.get("site", {})
    cluster = result.get("cluster", {})
    demand = result.get("demand", {})
    sizing = result.get("sizing", {})
    financial = result.get("financial", {})
    solar = result.get("solar_resource", {})
    dist = result.get("distribution", {})
    carbon = result.get("carbon", {})
    grid_risk = result.get("grid_risk", {})
    pue = result.get("productive_use", {})
    climate = result.get("climate", {})
    risk = result.get("risk_analysis", {})
    confidence = result.get("confidence", {})

    lines.append(f"\n### Site: {cluster.get('village_name', site.get('name', 'Unknown'))}")
    lines.append(f"- Coordinates: {site.get('latitude')}, {site.get('longitude')}")
    lines.append(f"- Province: {cluster.get('admin_region', '?')}, District: {cluster.get('admin_district', '?')}")
    lines.append(f"- Population: {cluster.get('population', '?')}")
    lines.append(f"- Buildings: {cluster.get('num_buildings', '?')} (satellite-detected, includes non-residential)")
    lines.append(f"- Classification: {'Urban' if cluster.get('is_urban') == 2 else 'Peri-urban' if cluster.get('is_urban') == 1 else 'Rural'}")

    lines.append(f"\n### Demand")
    lines.append(f"- Households connected (Round 1): {demand.get('households', '?')} of {demand.get('total_settlement_households', '?')} total")
    lines.append(f"- Coverage: {demand.get('coverage_pct', 0) * 100:.0f}%")
    lines.append(f"- Demand tier: {demand.get('demand_tier', '?')}")
    lines.append(f"- Daily energy: {demand.get('daily_energy_kwh', '?')} kWh/day")
    lines.append(f"- Peak demand: {demand.get('peak_demand_kw', '?')} kW")
    lines.append(f"- Annual energy: {demand.get('annual_energy_kwh', '?')} kWh/yr")
    lines.append(f"- Productive use: {demand.get('productive_use_kwh_day', 0)} kWh/day")

    if solar:
        lines.append(f"\n### Solar Resource")
        lines.append(f"- Annual GHI: {solar.get('annual_ghi_kwh_m2', '?')} kWh/m²/yr")
        lines.append(f"- Specific yield: {solar.get('specific_yield_kwh_per_kwp', '?')} kWh/kWp/yr")
        lines.append(f"- Performance ratio: {solar.get('performance_ratio', '?')}")

    lines.append(f"\n### System Sizing")
    lines.append(f"- PV: {sizing.get('pv_kwp', '?')} kWp")
    lines.append(f"- Battery: {sizing.get('battery_kwh_nominal', '?')} kWh nominal ({sizing.get('battery_kwh_usable', '?')} usable)")
    lines.append(f"- Inverter: {sizing.get('inverter_kva', '?')} kVA")
    if sizing.get('annual_generation_kwh'):
        lines.append(f"- Annual generation: {sizing['annual_generation_kwh']:.0f} kWh")
    if sizing.get('unmet_energy_pct') is not None:
        lines.append(f"- Unmet energy: {sizing['unmet_energy_pct']:.1f}%")
    if sizing.get('capacity_factor_pct') is not None:
        lines.append(f"- Capacity factor: {sizing['capacity_factor_pct']:.1f}%")

    if dist:
        lines.append(f"\n### Distribution")
        lines.append(f"- Line length: {dist.get('total_line_length_m', '?')} m")
        lines.append(f"- Poles: {dist.get('pole_count', '?')}")
        lines.append(f"- Customers: {dist.get('customers_connected', '?')}")
        lines.append(f"- Network cost: ${dist.get('total_network_cost_usd', 0):,.0f}")
        lines.append(f"- Cost/connection: ${dist.get('cost_per_connection_usd', 0):,.0f}")
        lines.append(f"- Voltage drop: {dist.get('voltage_drop_max_pct', '?')}%")

    lines.append(f"\n### Financial")
    lines.append(f"- Total CAPEX: ${financial.get('total_capex_usd', 0):,.0f}")
    lines.append(f"- LCOE: ${financial.get('lcoe_usd_kwh', 0):.3f}/kWh")
    lines.append(f"- Project IRR: {financial.get('irr_pct', 0):.1f}%")
    if financial.get('equity_irr_pct') is not None:
        lines.append(f"- Equity IRR: {financial['equity_irr_pct']:.1f}%")
    lines.append(f"- NPV: ${financial.get('npv_usd', 0):,.0f}")
    lines.append(f"- Payback: {financial.get('payback_years', '?')} years")
    lines.append(f"- DSCR: {financial.get('dscr', '?')}")
    lines.append(f"- Cost-reflective tariff: ${financial.get('cost_reflective_tariff_usd', 0):.3f}/kWh")
    lines.append(f"- Affordable tariff: ${financial.get('affordable_tariff_usd', 0):.3f}/kWh")
    lines.append(f"- Subsidy gap: ${financial.get('subsidy_gap_per_connection_usd', 0):,.0f}/conn ({financial.get('subsidy_gap_pct_capex', 0):.0f}% CAPEX)")
    bk = financial.get('capex_breakdown', {})
    if bk:
        lines.append(f"- CAPEX breakdown: PV=${bk.get('pv', 0):,.0f}, Battery=${bk.get('battery', 0):,.0f}, Inverter=${bk.get('inverter', 0):,.0f}, Distribution=${bk.get('distribution', 0):,.0f}, Install=${bk.get('installation', 0):,.0f}, Soft=${bk.get('soft_costs', 0):,.0f}")

    if grid_risk:
        lines.append(f"\n### Grid Risk")
        lines.append(f"- Distance to MV: {grid_risk.get('dist_mv_km', '?')} km")
        lines.append(f"- Distance to HV: {grid_risk.get('dist_hv_km', '?')} km")
        lines.append(f"- Risk level: {grid_risk.get('risk_level', '?')}")
        lines.append(f"- ESMAP strategy: {grid_risk.get('esmap_recommended', '?')}")

    if carbon:
        lines.append(f"\n### Carbon")
        lines.append(f"- Annual reductions: {carbon.get('annual_emission_reductions_tco2e', '?')} tCO2e/yr")
        lines.append(f"- Diesel displaced: {carbon.get('diesel_displaced_litres_yr', '?')} litres/yr")
        lines.append(f"- Methodology: {carbon.get('recommended_methodology', '?')}")

    if pue and pue.get('sectors'):
        high = [s for s in pue['sectors'] if s.get('relevance') == 'high']
        lines.append(f"\n### Productive Use")
        lines.append(f"- Total PUE demand: {pue.get('total_productive_demand_kwh_day', 0)} kWh/day")
        lines.append(f"- PUE share: {pue.get('productive_demand_pct', 0)}%")
        if high:
            lines.append(f"- High-relevance sectors: {', '.join(s['sector'] for s in high)}")

    if risk:
        lines.append(f"\n### Risk Analysis")
        lines.append(f"- Overall risk: {risk.get('overall_risk_level', '?')} ({risk.get('overall_risk_score', '?')}/25)")
        if risk.get('top_risks'):
            for r in risk['top_risks'][:3]:
                lines.append(f"  - {r}")

    if confidence:
        lines.append(f"\n### Data Confidence")
        lines.append(f"- Overall: {confidence.get('overall_confidence_score', '?')}% ({confidence.get('overall_confidence_level', '?')})")

    return "\n".join(lines)
