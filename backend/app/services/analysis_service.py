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

    sizing = size_system(
        cluster, demand, solar_resource, hourly_demand, hourly_solar, overrides
    )

    distribution = design_distribution(cluster, demand, overrides)

    annual_served = sizing.annual_energy_served_kwh or demand.annual_energy_kwh
    carbon = assess_carbon(annual_served)

    financial = run_financial_model(sizing, demand, distribution, carbon, overrides)

    grid_risk = assess_grid_risk(cluster, financial)

    # ── New TOR-required engines ──────────────────────────────────
    productive_use = _safe_call(
        analyze_productive_use, cluster, demand
    )

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
