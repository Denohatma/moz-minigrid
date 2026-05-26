from __future__ import annotations

from typing import Optional

from app.schemas.site import SiteCoordinates
from app.schemas.analysis import AnalysisResult
from app.engines.gis_engine import lookup_cluster, screen_suitability
from app.engines.solar_engine import assess_solar_resource
from app.engines.demand_engine import estimate_demand
from app.engines.sizing_engine import size_system
from app.engines.distribution_engine import design_distribution
from app.engines.carbon_engine import assess_carbon
from app.engines.financial_engine import run_financial_model
from app.engines.grid_risk_engine import assess_grid_risk
from app.engines.productive_use_engine import analyze_productive_use
from app.engines.ess_engine import screen_ess
from app.engines.climate_engine import assess_climate_rationale
from app.engines.risk_engine import analyze_risks
from app.engines.confidence_engine import score_confidence
from app.engines.concession_engine import generate_concession_data


DIST_TARGET_PCT = 0.27
DIST_TOLERANCE = 0.015


def _dist_share(financial, distribution):
    """Distribution's share of equipment subtotal (= share of total CAPEX
    since the overhead multiplier is uniform across all components)."""
    bk = financial.capex_breakdown
    gen = (bk.pv or 0) + (bk.battery or 0) + (bk.inverter or 0) + (bk.civil_works or 0)
    dist = distribution.total_network_cost_usd
    equip = gen + dist
    return (dist / equip if equip > 0 else 0), gen


def _apply_pue_scaling(demand, hourly_demand, pue_kwh_day):
    """Add PUE demand on top of residential demand."""
    demand.productive_use_kwh_day = pue_kwh_day
    combined = demand.daily_energy_kwh + pue_kwh_day
    scale = combined / demand.daily_energy_kwh if demand.daily_energy_kwh > 0 else 1.0
    demand.daily_energy_kwh = round(combined, 2)
    demand.annual_energy_kwh = round(combined * 365, 1)
    demand.peak_demand_kw = round(demand.peak_demand_kw * scale, 2)
    return demand, [h * scale for h in hourly_demand]


def run_full_analysis(
    latitude: float,
    longitude: float,
    name: Optional[str] = None,
    overrides: Optional[dict] = None,
) -> AnalysisResult:
    """Execute the complete prefeasibility analysis pipeline.

    Pipeline:
      1. Cluster lookup + suitability screening
      2. Solar resource assessment (PVGIS + 8,760-hour factors)
      3. Demand estimation (24-hour + 8,760-hour profiles)
      4. System sizing (8,760-hour dispatch simulation)
      5. Distribution network design (radial estimate + BoQ)
      6. Carbon assessment (emission reductions + credit revenue)
      7. Financial model (25-year DCF with granular CAPEX/OPEX)
      7b. Distribution calibration — adjust coverage so dist = 27% of CAPEX
      8. Grid risk assessment (ESMAP scenario scoring)
      9. Productive use value chain analysis
     10. Environmental & social safeguards screening
     11. Climate rationale (hazards + adaptation + finance)
     12. Comprehensive risk analysis (8 categories)
     13. Confidence scoring (10 output dimensions)
     14. ARENE concession data sheet generation
    """
    overrides = overrides or {}

    site = SiteCoordinates(latitude=latitude, longitude=longitude, name=name)

    cluster = lookup_cluster(latitude, longitude)
    if cluster is None:
        raise ValueError(f"No settlement cluster found near ({latitude}, {longitude})")

    screening = screen_suitability(cluster)

    solar_resource, hourly_solar = assess_solar_resource(latitude, longitude)

    demand, hourly_demand = estimate_demand(cluster, overrides)

    # Run PUE analysis early so its demand feeds into system sizing
    productive_use = _safe_call(analyze_productive_use, cluster, demand)
    pue_kwh_day = 0.0
    if productive_use:
        pue_kwh_day = productive_use.total_productive_demand_kwh_day
        demand, hourly_demand = _apply_pue_scaling(demand, hourly_demand, pue_kwh_day)

    sizing = size_system(
        cluster, demand, solar_resource, hourly_demand, hourly_solar, overrides
    )

    distribution = design_distribution(cluster, demand, overrides)

    annual_served = sizing.annual_energy_served_kwh or demand.annual_energy_kwh
    carbon = assess_carbon(annual_served)

    financial = run_financial_model(sizing, demand, distribution, carbon, overrides)

    # ── Calibrate coverage so distribution = 27% of total CAPEX ──
    # ESMAP benchmark: distribution is 26-27% of total mini-grid CAPEX.
    # Only reduce coverage (never increase beyond initial 50%) — "we don't
    # cover the full village" when distribution would exceed 27%.
    dist_pct, gen_equip = _dist_share(financial, distribution)
    initial_coverage = demand.coverage_pct

    if (distribution
            and dist_pct > DIST_TARGET_PCT + DIST_TOLERANCE
            and distribution.cost_per_connection_usd > 0
            and "coverage_pct" not in overrides):
        total_hh = demand.total_settlement_households
        cost_per_conn = distribution.cost_per_connection_usd

        for _ in range(3):
            target_dist = gen_equip * DIST_TARGET_PCT / (1 - DIST_TARGET_PCT)
            target_n = max(1, min(round(target_dist / cost_per_conn), total_hh))
            new_coverage = min(target_n / max(total_hh, 1), initial_coverage)

            adj_overrides = {**overrides, "coverage_pct": new_coverage}
            demand, hourly_demand = estimate_demand(cluster, adj_overrides)

            if pue_kwh_day > 0:
                demand, hourly_demand = _apply_pue_scaling(
                    demand, hourly_demand, pue_kwh_day
                )

            sizing = size_system(
                cluster, demand, solar_resource,
                hourly_demand, hourly_solar, overrides,
            )
            distribution = design_distribution(cluster, demand, adj_overrides)

            annual_served = sizing.annual_energy_served_kwh or demand.annual_energy_kwh
            carbon = assess_carbon(annual_served)
            financial = run_financial_model(
                sizing, demand, distribution, carbon, overrides
            )

            dist_pct, gen_equip = _dist_share(financial, distribution)
            if abs(dist_pct - DIST_TARGET_PCT) < DIST_TOLERANCE:
                break

    grid_risk = assess_grid_risk(cluster, financial)

    ess = _safe_call(
        screen_ess, cluster, sizing, latitude, longitude
    )

    climate = _safe_call(
        assess_climate_rationale,
        latitude, longitude, cluster, carbon, sizing, annual_served,
    )

    risk_analysis = _safe_call(
        analyze_risks, cluster, financial, sizing, grid_risk, demand
    )

    confidence = _safe_call(
        score_confidence, cluster, demand, sizing, financial, carbon, solar_resource
    )

    result = AnalysisResult(
        site=site,
        cluster=cluster,
        screening=screening,
        demand=demand,
        sizing=sizing,
        financial=financial,
        grid_risk=grid_risk,
        solar_resource=solar_resource,
        distribution=distribution,
        carbon=carbon,
        climate=climate,
        productive_use=productive_use,
        ess=ess,
        risk_analysis=risk_analysis,
        confidence=confidence,
        concession=None,
    )

    # Generate concession data sheet with full result
    concession = _safe_call(
        generate_concession_data,
        result, productive_use, ess, climate, risk_analysis, confidence,
    )
    result.concession = concession

    return result


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None
