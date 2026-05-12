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

    return AnalysisResult(
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
    )
