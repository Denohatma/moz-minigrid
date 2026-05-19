from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"


class ConcessionSection(BaseModel):
    section_number: int
    title: str
    data: dict


class ConcessionDataSheet(BaseModel):
    site_name: str
    province: str
    district: str
    generation_date: str
    sections: list[ConcessionSection]
    warnings: list[str] = Field(default_factory=list)


def generate_concession_data(
    analysis_result,
    productive_use=None,
    ess=None,
    climate=None,
    risk_analysis=None,
    confidence=None,
) -> ConcessionDataSheet:
    r = analysis_result
    cl = r.cluster
    f = r.financial
    s = r.sizing
    d = r.demand
    gr = r.grid_risk
    sol = r.solar_resource
    dist = r.distribution
    carb = r.carbon

    site_name = cl.village_name or r.site.name or "Unnamed"
    province = cl.admin_region or "Unknown"
    district = cl.admin_district or "Unknown"
    config = _load_config()
    warnings: list[str] = []

    sections: list[ConcessionSection] = []

    # ── Section 1: Concession Identification ──────────────────────
    concession_term = _recommend_concession_term(f, gr)
    sections.append(ConcessionSection(
        section_number=1,
        title="Concession Identification",
        data={
            "site_name": site_name,
            "coordinates": {"latitude": r.site.latitude, "longitude": r.site.longitude},
            "province": province,
            "district": district,
            "administrative_post": cl.nearest_hub_name or "N/A",
            "settlements_covered": 1,
            "settlement_names": [site_name],
            "total_population": cl.population,
            "recommended_concession_term_years": concession_term,
            "concession_term_justification": (
                f"{concession_term}-year term recommended based on "
                f"{'strong' if f.irr_pct > 10 else 'moderate' if f.irr_pct > 5 else 'marginal'} "
                f"financial viability (IRR {f.irr_pct:.1f}%) and "
                f"{gr.risk_level} grid arrival risk."
            ),
        },
    ))

    # ── Section 2: Baseline ───────────────────────────────────────
    pop = cl.population
    growth_rate = config.get("population_growth_rate", 0.028)
    sections.append(ConcessionSection(
        section_number=2,
        title="Baseline",
        data={
            "current_population": pop,
            "current_households": d.households,
            "population_projections": {
                "year_5": int(pop * (1 + growth_rate) ** 5),
                "year_10": int(pop * (1 + growth_rate) ** 10),
                "year_15": int(pop * (1 + growth_rate) ** 15),
                "year_20": int(pop * (1 + growth_rate) ** 20),
            },
            "household_projections": {
                "year_5": int(d.households * (1 + growth_rate) ** 5),
                "year_10": int(d.households * (1 + growth_rate) ** 10),
                "year_15": int(d.households * (1 + growth_rate) ** 15),
                "year_20": int(d.households * (1 + growth_rate) ** 20),
            },
            "existing_electrification": {
                "status": _electrification_status(cl),
                "electrified_population_pct": round(cl.electrified_pop / max(pop, 1) * 100, 1),
            },
            "existing_infrastructure": {
                "road_access": cl.main_road_access or cl.dist_road_km < 5,
                "distance_road_km": round(cl.dist_road_km, 1),
                "distance_grid_mv_km": round(cl.dist_grid_mv_km, 1),
                "distance_grid_hv_km": round(cl.dist_grid_hv_km or 0, 1),
                "has_education_facility": cl.has_education_facility or False,
                "has_health_facility": cl.has_health_facility or False,
                "nearest_hub": cl.nearest_hub_name or "N/A",
                "distance_nearest_hub_km": round(cl.dist_nearest_hub_km or 0, 1),
                "distance_water_km": round(cl.closest_distance_water_km or 0, 1),
            },
        },
    ))

    # ── Section 3: Demand ─────────────────────────────────────────
    demand_growth = 0.03
    daily = d.daily_energy_kwh
    annual = d.annual_energy_kwh
    sections.append(ConcessionSection(
        section_number=3,
        title="Demand",
        data={
            "estimated_demand": {
                "year_1": {"energy_kwh_year": round(annual, 0), "peak_kw": round(d.peak_demand_kw, 1)},
                "year_5": {"energy_kwh_year": round(annual * (1 + demand_growth) ** 5, 0), "peak_kw": round(d.peak_demand_kw * (1 + demand_growth) ** 5, 1)},
                "year_10": {"energy_kwh_year": round(annual * (1 + demand_growth) ** 10, 0), "peak_kw": round(d.peak_demand_kw * (1 + demand_growth) ** 10, 1)},
                "year_15": {"energy_kwh_year": round(annual * (1 + demand_growth) ** 15, 0), "peak_kw": round(d.peak_demand_kw * (1 + demand_growth) ** 15, 1)},
                "year_20": {"energy_kwh_year": round(annual * (1 + demand_growth) ** 20, 0), "peak_kw": round(d.peak_demand_kw * (1 + demand_growth) ** 20, 1)},
            },
            "daily_load_profile_kw": d.load_profile_kw,
            "demand_tier": d.demand_tier,
            "demand_breakdown": {
                "residential_pct": _residential_pct(d, productive_use),
                "commercial_pct": _commercial_pct(d, productive_use),
                "productive_pct": _productive_pct(productive_use),
                "public_services_pct": _public_services_pct(cl),
            },
            "demand_growth_assumptions": {
                "residential_growth_pct_year": 3.0,
                "productive_growth_pct_year": 5.0,
                "connection_ramp_years": 5,
            },
            "confidence_interval": (
                confidence.dimensions[1].margin_of_error_pct
                if confidence and len(confidence.dimensions) > 1
                else 20.0
            ),
        },
    ))

    # ── Section 4: Anchor Customers ───────────────────────────────
    anchors_data = []
    if productive_use and hasattr(productive_use, "anchors"):
        for a in productive_use.anchors:
            anchors_data.append({
                "type": a.type,
                "name": a.name,
                "demand_kwh_day": a.estimated_demand_kwh_day,
                "peak_kw": a.estimated_peak_kw,
                "contract_type": a.contract_type,
                "confidence": a.confidence,
            })

    if not anchors_data:
        _add_default_anchors(cl, anchors_data)

    sections.append(ConcessionSection(
        section_number=4,
        title="Anchor Customers",
        data={"identified_anchors": anchors_data},
    ))

    # ── Section 5: Productive Use ─────────────────────────────────
    pue_data: dict = {"status": "assessment_included" if productive_use else "not_assessed"}
    if productive_use:
        pue_data.update({
            "relevant_sectors": [
                {"sector": sec.sector, "relevance": sec.relevance, "activities": sec.indicative_activities}
                for sec in productive_use.sectors if sec.relevance in ("high", "medium")
            ],
            "total_productive_demand_kwh_day": productive_use.total_productive_demand_kwh_day,
            "productive_demand_pct": productive_use.productive_demand_pct,
            "demand_projections": productive_use.demand_projections,
            "complementary_investment_usd": productive_use.complementary_investment_usd,
            "demand_stimulation": productive_use.demand_stimulation,
            "jobs": productive_use.jobs,
            "incremental_income_usd_year": productive_use.incremental_income_usd_year,
        })

    sections.append(ConcessionSection(
        section_number=5,
        title="Productive Use",
        data=pue_data,
    ))

    # ── Section 6: Resource & Technical Design ────────────────────
    annual_ghi = sol.annual_ghi_kwh_m2 if sol else cl.ghi_kwh_m2_year
    sections.append(ConcessionSection(
        section_number=6,
        title="Resource & Technical Design",
        data={
            "solar_resource": {
                "annual_ghi_kwh_m2": round(annual_ghi, 1),
                "monthly_ghi": sol.monthly_ghi_kwh_m2 if sol else [],
                "performance_ratio": sol.performance_ratio if sol else 0.77,
                "data_source": sol.data_source if sol else "estimate",
            },
            "generation": {
                "pv_kwp": s.pv_kwp,
                "inverter_kva": s.inverter_kva,
                "battery_kwh_nominal": s.battery_kwh_nominal,
                "battery_kwh_usable": s.battery_kwh_usable,
                "battery_technology": "LFP (Lithium Iron Phosphate)",
                "annual_generation_kwh": s.annual_generation_kwh or 0,
                "annual_energy_served_kwh": s.annual_energy_served_kwh or 0,
                "capacity_factor_pct": s.capacity_factor_pct or 0,
                "unmet_energy_pct": s.unmet_energy_pct or 0,
            },
            "distribution": {
                "total_line_length_m": dist.total_line_length_m if dist else 0,
                "pole_count": dist.pole_count if dist else 0,
                "customers_connected": dist.customers_connected if dist else d.households,
                "voltage_drop_max_pct": dist.voltage_drop_max_pct if dist else 0,
                "technical_losses_pct": dist.technical_losses_pct if dist else 0,
            },
            "reserve_margin_pct": round((s.pv_kwp / max(d.peak_demand_kw, 0.1) - 1) * 100, 1),
        },
    ))

    # ── Section 7: CAPEX & OPEX ───────────────────────────────────
    cb = f.capex_breakdown
    sections.append(ConcessionSection(
        section_number=7,
        title="CAPEX & OPEX",
        data={
            "total_capex_usd": f.total_capex_usd,
            "capex_breakdown": {
                "generation": round((cb.pv or 0) + (cb.mounting or 0) + (cb.bos or 0), 0),
                "storage": round(cb.battery, 0),
                "distribution": round(cb.distribution + cb.meters, 0),
                "civil_works": round(cb.civil_works or 0, 0),
                "project_development": round(cb.soft_costs + (cb.owners_cost or 0), 0),
                "contingencies": round(cb.contingency or 0, 0),
            },
            "total_opex_usd_year": f.annual_opex_usd or 0,
            "opex_breakdown": {
                "generation_om": f.opex_breakdown.generation_om if f.opex_breakdown else 0,
                "distribution_om": f.opex_breakdown.distribution_om if f.opex_breakdown else 0,
                "site_security": f.opex_breakdown.site_security if f.opex_breakdown else 0,
                "remote_monitoring": f.opex_breakdown.remote_monitoring if f.opex_breakdown else 0,
                "insurance": f.opex_breakdown.insurance if f.opex_breakdown else 0,
            },
            "cost_per_connection_usd": round(f.total_capex_usd / max(d.households, 1), 0),
            "cost_per_kw_installed_usd": round(f.total_capex_usd / max(s.pv_kwp, 0.1), 0),
            "capex_per_wp": f.capex_per_wp or 0,
        },
    ))

    # ── Section 8: Financial Model & Tariff ───────────────────────
    exchange_rate = config.get("exchange_rate_mzn_per_usd", 63.5)
    sections.append(ConcessionSection(
        section_number=8,
        title="Financial Model & Tariff",
        data={
            "tariff_structure": {
                "residential_usd_kwh": round(f.cost_reflective_tariff_usd * 0.85, 3),
                "commercial_usd_kwh": round(f.cost_reflective_tariff_usd * 1.10, 3),
                "productive_usd_kwh": round(f.cost_reflective_tariff_usd * 0.95, 3),
                "anchor_usd_kwh": round(f.cost_reflective_tariff_usd * 0.80, 3),
                "cost_reflective_tariff_usd_kwh": round(f.cost_reflective_tariff_usd, 3),
                "affordable_tariff_usd_kwh": round(f.affordable_tariff_usd, 3),
            },
            "tariff_mzn": {
                "residential_mzn_kwh": round(f.cost_reflective_tariff_usd * 0.85 * exchange_rate, 1),
                "commercial_mzn_kwh": round(f.cost_reflective_tariff_usd * 1.10 * exchange_rate, 1),
            },
            "subsidy": {
                "capital_grant_usd": f.grant_amount_usd or 0,
                "capital_grant_pct_capex": round((f.grant_amount_usd or 0) / max(f.total_capex_usd, 1) * 100, 1),
                "subsidy_gap_per_connection_usd": f.subsidy_gap_per_connection_usd,
                "results_based_component_usd_per_conn": round(f.subsidy_gap_per_connection_usd * 0.3, 0),
            },
            "financial_indicators": {
                "project_irr_pct": f.irr_pct,
                "equity_irr_pct": f.equity_irr_pct or 0,
                "npv_usd": f.npv_usd,
                "payback_years": f.payback_years,
                "dscr": f.dscr,
                "lcoe_usd_kwh": f.lcoe_usd_kwh,
            },
            "sensitivity_analysis": [
                {"parameter": sr.parameter, "low": sr.irr_at_low, "base": sr.irr_at_base, "high": sr.irr_at_high}
                for sr in f.sensitivity
            ],
        },
    ))

    # ── Section 9: ESIA & Social Safeguards ───────────────────────
    ess_data: dict = {"status": "screening_included" if ess else "not_assessed"}
    if ess:
        ess_data.update({
            "esia_category": ess.esia_category,
            "esia_rationale": ess.esia_rationale,
            "esia_requirements": ess.esia_requirements,
            "biodiversity_sensitivity": ess.biodiversity_sensitivity,
            "resettlement_risk": ess.resettlement_risk,
            "overall_ess_risk": ess.overall_ess_risk,
            "stakeholder_groups": ess.stakeholder_groups,
            "consultation_requirements": ess.consultation_requirements,
            "grievance_mechanism": ess.grievance_mechanism,
            "gesi_considerations": ess.gesi_considerations,
            "womens_empowerment_opportunities": ess.womens_empowerment_opportunities,
        })
    else:
        warnings.append("ESS screening not performed — include in full feasibility study")

    sections.append(ConcessionSection(
        section_number=9,
        title="ESIA & Social Safeguards",
        data=ess_data,
    ))

    # ── Section 10: Climate Rationale ─────────────────────────────
    climate_data: dict = {"status": "assessment_included" if climate else "not_assessed"}
    if climate:
        climate_data.update({
            "avoided_ghg_tco2e_year": carb.annual_emission_reductions_tco2e if carb else 0,
            "lifetime_avoided_tco2e": climate.lifetime_avoided_tco2e,
            "ndc_alignment": climate.ndc_alignment,
            "adaptation_narrative": climate.adaptation_narrative,
            "hazards": [
                {"hazard": h.hazard, "level": h.level, "description": h.description}
                for h in climate.hazards
            ],
            "overall_hazard_level": climate.overall_hazard_level,
            "design_resilience_measures": climate.design_resilience_measures,
            "climate_finance_eligibility": [
                {"instrument": cf.instrument, "eligible": cf.eligible, "estimated_value_usd": cf.estimated_value_usd}
                for cf in climate.climate_finance
            ],
            "climate_finance_score": climate.climate_finance_score,
        })
    elif carb:
        climate_data.update({
            "avoided_ghg_tco2e_year": carb.annual_emission_reductions_tco2e,
            "lifetime_avoided_tco2e": carb.annual_emission_reductions_tco2e * 25 * 0.995 ** 12,
            "carbon_methodology": carb.recommended_methodology,
        })

    sections.append(ConcessionSection(
        section_number=10,
        title="Climate Rationale",
        data=climate_data,
    ))

    # ── Section 11: Risk Analysis ─────────────────────────────────
    risk_data: dict = {"status": "assessment_included" if risk_analysis else "not_assessed"}
    if risk_analysis:
        risk_data.update({
            "risks": [
                {
                    "category": ri.category,
                    "sub_risk": ri.sub_risk,
                    "likelihood": ri.likelihood,
                    "impact": ri.impact,
                    "risk_score": ri.risk_score,
                    "risk_level": ri.risk_level,
                    "mitigation": ri.mitigation,
                    "allocation": ri.allocation,
                }
                for ri in risk_analysis.risks
            ],
            "overall_risk_level": risk_analysis.overall_risk_level,
            "top_risks": risk_analysis.top_risks,
            "risk_allocation_summary": risk_analysis.risk_allocation_summary,
        })
    else:
        warnings.append("Comprehensive risk analysis not performed — include in full feasibility study")

    sections.append(ConcessionSection(
        section_number=11,
        title="Risk Analysis",
        data=risk_data,
    ))

    # ── Section 12: Performance Standards ─────────────────────────
    sections.append(ConcessionSection(
        section_number=12,
        title="Performance Standards",
        data={
            "reliability": {
                "saidi_target_hours_year": 150,
                "saifi_target_interruptions_year": 50,
                "availability_target_pct": 98.0,
            },
            "power_quality": {
                "voltage_tolerance_pct": 10,
                "frequency_hz": 50,
                "frequency_tolerance_pct": 2,
            },
            "customer_service": {
                "connection_lead_time_days": 30,
                "complaint_resolution_days": 14,
                "metering_accuracy_class": 1,
            },
            "connection_ramp_up": {
                "year_1_pct": 40,
                "year_2_pct": 60,
                "year_3_pct": 80,
                "year_4_pct": 90,
                "year_5_pct": 100,
            },
            "productive_use_uptake": {
                "year_1_pct": 10,
                "year_3_pct": 25,
                "year_5_pct": 40,
            },
            "reporting_frequency": "quarterly",
        },
    ))

    # ── Section 13: Recommended Concession Terms ──────────────────
    sections.append(ConcessionSection(
        section_number=13,
        title="Recommended Concession Terms",
        data={
            "concession_term_years": concession_term,
            "exclusivity": "Exclusive generation and distribution rights within concession boundary",
            "tariff_review": {
                "frequency": "Every 3 years",
                "triggers": ["CPI exceeds 15%", "Exchange rate deviation > 20%", "Fuel price change > 30%"],
                "methodology": "Cost-plus with regulatory approval (ARENE)",
            },
            "subsidy_disbursement": {
                "capital_grant": "70% at COD, 30% after 1-year performance verification",
                "results_based": "Per verified connection over years 1-5",
            },
            "asset_transfer": "Assets transfer to government at nominal value at end of concession",
            "grid_arrival_regime": {
                "interconnection_rights": "Concessionaire has right to interconnect per ARENE Resolution 2/2022",
                "compensation_framework": "Residual asset value based on depreciated replacement cost",
                "integration_options": ["Convert to grid-connected IPP", "Asset buyout by EDM", "Hybrid operation"],
            },
            "reporting_obligations": "Quarterly operational reports to ARENE; annual audited financials",
            "step_in_provisions": "ARENE may step in after 6 months of material non-compliance",
            "termination": "For cause with 90-day cure period; force majeure provisions per Mozambique law",
        },
    ))

    # ── Section 14: Attachments ───────────────────────────────────
    attachments = [
        "Site geospatial files (coordinates and settlement boundary)",
        "Financial model (Excel workbook with live formulas)",
    ]
    if dist:
        attachments.append("Distribution network preliminary layout")
    if ess:
        attachments.append("ESIA screening report")
    if productive_use:
        attachments.append("Productive use anchor business cases")
    if confidence:
        attachments.append(
            f"AI Tool confidence and margin of error report "
            f"(overall confidence: {confidence.overall_confidence_score}%)"
        )

    sections.append(ConcessionSection(
        section_number=14,
        title="Attachments",
        data={"attachment_list": attachments},
    ))

    return ConcessionDataSheet(
        site_name=site_name,
        province=province,
        district=district,
        generation_date=date.today().isoformat(),
        sections=sections,
        warnings=warnings,
    )


def generate_concession_json(concession: ConcessionDataSheet) -> dict:
    return concession.model_dump()


def _recommend_concession_term(financial, grid_risk) -> int:
    if grid_risk.risk_level == "critical":
        return 15
    if grid_risk.risk_level == "high":
        return 18
    if financial.irr_pct > 10:
        return 20
    return 25


def _electrification_status(cl) -> str:
    elec_pct = cl.electrified_pop / max(cl.population, 1) * 100
    if elec_pct < 5:
        return "Unelectrified"
    if elec_pct < 30:
        return f"Partially electrified ({elec_pct:.0f}% — likely SHS)"
    return f"Partially electrified ({elec_pct:.0f}%)"


def _residential_pct(demand, productive_use) -> float:
    if productive_use and productive_use.productive_demand_pct > 0:
        return round(max(100 - productive_use.productive_demand_pct - 5, 40), 1)
    if demand.demand_tier <= 2:
        return 85.0
    if demand.demand_tier == 3:
        return 70.0
    return 55.0


def _commercial_pct(demand, productive_use) -> float:
    if demand.demand_tier >= 4:
        return 15.0
    if demand.demand_tier == 3:
        return 10.0
    return 5.0


def _productive_pct(productive_use) -> float:
    if productive_use and productive_use.productive_demand_pct > 0:
        return round(productive_use.productive_demand_pct, 1)
    return 5.0


def _public_services_pct(cl) -> float:
    base = 3.0
    if cl.has_education_facility:
        base += 1.0
    if cl.has_health_facility:
        base += 1.5
    return base


def _add_default_anchors(cl, anchors: list):
    if cl.has_health_facility:
        anchors.append({
            "type": "Health centre",
            "name": f"{cl.village_name or 'Local'} health centre",
            "demand_kwh_day": 8.0,
            "peak_kw": 2.0,
            "contract_type": "standard",
            "confidence": "medium",
        })
    if cl.has_education_facility:
        anchors.append({
            "type": "School",
            "name": f"{cl.village_name or 'Local'} school",
            "demand_kwh_day": 3.0,
            "peak_kw": 1.0,
            "contract_type": "standard",
            "confidence": "medium",
        })
    if cl.population > 500 and cl.dist_road_km < 10:
        anchors.append({
            "type": "Telecom tower",
            "name": "Telecom tower (estimated)",
            "demand_kwh_day": 15.0,
            "peak_kw": 3.0,
            "contract_type": "take-or-pay",
            "confidence": "low",
        })


def _load_config() -> dict:
    path = COUNTRY_DIR / "config.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
