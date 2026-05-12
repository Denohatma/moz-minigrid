from __future__ import annotations

import json
from pathlib import Path

from app.schemas.analysis import CarbonAssessment

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

DIESEL_EF_KG_CO2_PER_LITRE = 2.68
DIESEL_CH4_N2O_KG_CO2E_PER_LITRE = 0.12
TOTAL_EF = DIESEL_EF_KG_CO2_PER_LITRE + DIESEL_CH4_N2O_KG_CO2E_PER_LITRE

PRICE_SCENARIOS = {
    "zero": 0.0,
    "conservative": 5.0,
    "market": 12.0,
    "premium": 20.0,
}


def assess_carbon(
    annual_energy_served_kwh: float,
    discount_rate: float = 0.10,
) -> CarbonAssessment:
    """Calculate emission reductions, recommend methodology, and estimate carbon revenue.

    Baseline assumes diesel genset displacement (standard for off-grid sites).
    """
    defaults = _load_defaults()
    tech = defaults.get("technical", {})
    genset_eff = tech.get("genset_efficiency", 0.33)
    diesel_density = tech.get("diesel_energy_density_kwh_per_litre", 10.0)

    diesel_kwh = annual_energy_served_kwh / genset_eff
    diesel_litres = diesel_kwh / diesel_density
    annual_tco2e = diesel_litres * TOTAL_EF / 1000

    crediting_period = 7
    total_eligible = annual_tco2e * crediting_period
    issuance_start = 3

    revenue_by_scenario: dict[str, float] = {}
    npv_by_scenario: dict[str, float] = {}
    for name, price in PRICE_SCENARIOS.items():
        annual_rev = annual_tco2e * price
        revenue_by_scenario[name] = round(annual_rev, 0)
        npv = sum(
            annual_rev / (1 + discount_rate) ** yr
            for yr in range(issuance_start, issuance_start + crediting_period)
        )
        npv_by_scenario[name] = round(npv, 0)

    if annual_tco2e < 100:
        methodology = "Gold Standard TPDDTEC"
        rationale = (
            "Small-scale off-grid rural electrification with strong SDG impact. "
            "Gold Standard TPDDTEC recommended for premium pricing and "
            "micro-scale provisions (<100 tCO2e/year)."
        )
        alternative = "Verra VM0103"
    else:
        methodology = "Verra VM0103"
        rationale = (
            "Off-grid renewable electrification with productive use potential. "
            "Verra VM0103 is the standard methodology for mini-grid projects "
            "with established African deployments."
        )
        alternative = "Gold Standard TPDDTEC"

    validation_cost = 15000
    annual_verification = 5000
    warnings: list[str] = []

    if annual_tco2e * PRICE_SCENARIOS["market"] < annual_verification:
        warnings.append(
            f"Annual carbon revenue at market price "
            f"(USD {annual_tco2e * PRICE_SCENARIOS['market']:.0f}) "
            f"is below annual verification cost (USD {annual_verification}). "
            "Consider bundling with other mini-grid projects."
        )

    return CarbonAssessment(
        annual_emission_reductions_tco2e=round(annual_tco2e, 1),
        diesel_displaced_litres_yr=round(diesel_litres, 0),
        crediting_period_years=crediting_period,
        total_eligible_tco2e=round(total_eligible, 0),
        revenue_by_scenario=revenue_by_scenario,
        npv_carbon_revenue=npv_by_scenario,
        recommended_methodology=methodology,
        methodology_rationale=rationale,
        alternative_methodology=alternative,
        validation_cost_estimate_usd=validation_cost,
        annual_verification_cost_usd=annual_verification,
        warnings=warnings,
    )


def _load_defaults() -> dict:
    path = COUNTRY_DIR / "financial_defaults.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
