from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.site import ClusterInfo
from app.schemas.analysis import (
    CarbonAssessment,
    DemandEstimate,
    FinancialResults,
    SolarResource,
    SystemSizing,
)

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

# ── TOR margin-of-error targets (±%) ──────────────────────────────

TARGET_MOE: dict[str, float] = {
    "population_household_count": 10.0,
    "total_energy_demand_yr1": 17.5,
    "peak_load_yr1": 20.0,
    "productive_use_demand_share": 25.0,
    "solar_resource_ghi": 5.0,
    "generation_capacity_sizing": 15.0,
    "capex_per_kw": 20.0,
    "opex": 25.0,
    "cost_reflective_tariff": 15.0,
    "avoided_ghg_emissions": 20.0,
}

# Weights for overall weighted-average confidence (demand & CAPEX highest)
DIMENSION_WEIGHTS: dict[str, float] = {
    "population_household_count": 1.0,
    "total_energy_demand_yr1": 2.0,
    "peak_load_yr1": 1.0,
    "productive_use_demand_share": 0.5,
    "solar_resource_ghi": 1.0,
    "generation_capacity_sizing": 1.5,
    "capex_per_kw": 2.0,
    "opex": 1.0,
    "cost_reflective_tariff": 1.5,
    "avoided_ghg_emissions": 0.5,
}

# Fields that count toward data completeness when non-None
_COMPLETENESS_FIELDS = [
    "population", "area_km2", "is_urban", "dre_num_connections",
    "dre_demand_kwh_day", "max_ntl", "mean_rwi", "ag_area_ha",
    "ag_value_usd", "has_education_facility", "has_health_facility",
    "dist_road_km", "num_buildings", "large_buildings", "medium_buildings",
    "small_buildings", "ghi_kwh_m2_year", "dist_grid_mv_km",
    "security_risk", "travel_time_hrs",
]


# ── Output models ─────────────────────────────────────────────────

class ConfidenceDimension(BaseModel):
    dimension: str
    confidence_score: int = Field(ge=0, le=100, description="0-100 confidence")
    margin_of_error_pct: float = Field(description="±% uncertainty at 95% CI")
    data_quality: str = Field(description="high, medium, or low")
    key_assumptions: list[str]
    calibration_status: str = Field(
        description="calibrated, partially_calibrated, or uncalibrated"
    )


class ConfidenceAssessment(BaseModel):
    dimensions: list[ConfidenceDimension]
    overall_confidence_score: int = Field(ge=0, le=100)
    overall_confidence_level: str = Field(description="high (>75), medium (50-75), low (<50)")
    data_completeness_pct: float
    recommendations: list[str]
    warnings: list[str]


# ── Main entry point ──────────────────────────────────────────────

def score_confidence(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    sizing: SystemSizing,
    financial: FinancialResults,
    carbon: Optional[CarbonAssessment] = None,
    solar: Optional[SolarResource] = None,
) -> ConfidenceAssessment:
    """Compute confidence scores and margin of error for every output dimension.

    The assessment is deterministic and driven entirely by which data
    fields are populated in the inputs (i.e. real data vs. proxies).
    """
    has_dre = bool(cluster.dre_num_connections and cluster.dre_num_connections > 0)
    has_dre_demand = bool(cluster.dre_demand_kwh_day and cluster.dre_demand_kwh_day > 0)
    has_crop_data = bool(cluster.ag_area_ha and cluster.ag_area_ha > 0)
    has_crop_value = bool(cluster.ag_value_usd and cluster.ag_value_usd > 0)
    has_large_bldg = bool(cluster.large_buildings and cluster.large_buildings > 0)
    has_rwi = cluster.mean_rwi is not None
    has_buildings = cluster.num_buildings is not None and cluster.num_buildings > 0
    is_urban = cluster.is_urban >= 2
    is_remote = cluster.dist_road_km > 30 if cluster.dist_road_km else False
    has_solar_api = (
        solar is not None
        and solar.data_source
        and "pvgis" in solar.data_source.lower()
    )

    dimensions: list[ConfidenceDimension] = [
        _score_population(cluster, has_dre, has_buildings, is_urban),
        _score_demand(demand, has_dre_demand, has_crop_data, has_large_bldg),
        _score_peak_load(demand, has_dre_demand),
        _score_productive_use(cluster, has_crop_data, has_crop_value, has_large_bldg),
        _score_solar_resource(solar, has_solar_api),
        _score_generation_sizing(sizing, has_solar_api),
        _score_capex(sizing, financial),
        _score_opex(is_remote, financial),
        _score_tariff(sizing, financial, has_dre_demand, has_solar_api),
        _score_ghg(carbon, has_dre_demand),
    ]

    # ── Overall confidence (weighted) ──────────────────────────────
    total_weight = sum(DIMENSION_WEIGHTS.get(d.dimension, 1.0) for d in dimensions)
    weighted_sum = sum(
        d.confidence_score * DIMENSION_WEIGHTS.get(d.dimension, 1.0)
        for d in dimensions
    )
    overall_score = int(round(weighted_sum / total_weight)) if total_weight > 0 else 0

    if overall_score > 75:
        overall_level = "high"
    elif overall_score >= 50:
        overall_level = "medium"
    else:
        overall_level = "low"

    # ── Data completeness ──────────────────────────────────────────
    populated = 0
    for field_name in _COMPLETENESS_FIELDS:
        val = getattr(cluster, field_name, None)
        if val is not None and val != 0 and val != 0.0:
            populated += 1
    completeness = round(populated / len(_COMPLETENESS_FIELDS) * 100, 1)

    # ── Recommendations ────────────────────────────────────────────
    recommendations = _build_recommendations(
        cluster, has_dre, has_dre_demand, has_crop_data,
        has_solar_api, has_buildings, has_rwi, dimensions,
    )

    # ── Warnings ───────────────────────────────────────────────────
    warnings: list[str] = []
    low_dims = [d for d in dimensions if d.confidence_score < 40]
    if low_dims:
        names = ", ".join(d.dimension for d in low_dims)
        warnings.append(
            f"Low confidence (<40) in: {names}. "
            "Results for these dimensions should be treated as indicative only."
        )
    if completeness < 50:
        warnings.append(
            f"Data completeness is only {completeness}%. "
            "Many inputs are estimated from proxies. Consider supplementing "
            "with field survey data before investment decisions."
        )
    exceeded = [
        d for d in dimensions
        if d.margin_of_error_pct > TARGET_MOE.get(d.dimension, 100) * 1.5
    ]
    if exceeded:
        names = ", ".join(d.dimension for d in exceeded)
        warnings.append(
            f"Margin of error exceeds 1.5x the TOR target for: {names}."
        )

    return ConfidenceAssessment(
        dimensions=dimensions,
        overall_confidence_score=overall_score,
        overall_confidence_level=overall_level,
        data_completeness_pct=completeness,
        recommendations=recommendations,
        warnings=warnings,
    )


# ── Per-dimension scoring functions ───────────────────────────────

def _score_population(
    cluster: ClusterInfo,
    has_dre: bool,
    has_buildings: bool,
    is_urban: bool,
) -> ConfidenceDimension:
    """Population & household count — TOR target ±10%."""
    score = 40  # baseline: satellite-derived population estimate
    assumptions: list[str] = ["Population from WorldPop satellite-derived raster"]

    if has_dre:
        score += 30
        assumptions.append("DRE Atlas connection count used as household proxy")
    if has_buildings:
        score += 15
        assumptions.append("Building footprint count from DRE Atlas")
    if is_urban:
        score += 10
        assumptions.append("Urban area — census/admin data more reliable")
    else:
        assumptions.append("Rural area — higher population uncertainty")

    score = min(score, 95)

    # Margin of error: inversely proportional to confidence
    if score >= 80:
        moe = 8.0
        quality = "high"
        calibration = "calibrated"
    elif score >= 55:
        moe = 12.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 18.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="population_household_count",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_demand(
    demand: DemandEstimate,
    has_dre_demand: bool,
    has_crop_data: bool,
    has_large_bldg: bool,
) -> ConfidenceDimension:
    """Total energy demand (year 1) — TOR target ±15-20%."""
    score = 35
    assumptions: list[str] = ["Demand tier assigned from population & socioeconomic proxies"]

    if has_dre_demand:
        score += 30
        assumptions.clear()
        assumptions.append("DRE Atlas demand data used as primary input")
    if has_crop_data:
        score += 10
        assumptions.append("Agricultural productive use informed by crop data")
    if has_large_bldg:
        score += 5
        assumptions.append("Large buildings present — commercial demand included")

    # Tier 1 has the most uncertainty
    if demand.demand_tier == 1:
        score -= 10
        assumptions.append("Tier 1 demand — highest uncertainty in lowest tier")
    elif demand.demand_tier >= 4:
        score += 5
        assumptions.append("Higher demand tier — more predictable consumption patterns")

    score = max(min(score, 95), 10)

    if score >= 75:
        moe = 12.0
        quality = "high"
        calibration = "calibrated"
    elif score >= 50:
        moe = 18.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 28.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="total_energy_demand_yr1",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_peak_load(
    demand: DemandEstimate,
    has_dre_demand: bool,
) -> ConfidenceDimension:
    """Peak load (year 1) — TOR target ±20%.

    Always slightly less confident than demand due to load profile
    shape uncertainty and diversity factor.
    """
    score = 30
    assumptions: list[str] = [
        "Peak derived from daily demand using assumed load profile shape",
        "Diversity factor applied based on number of connections",
    ]

    if has_dre_demand:
        score += 25
        assumptions.append("DRE Atlas demand available, better load shape estimate")

    if demand.households > 100:
        score += 10
        assumptions.append("Large cluster — diversity factor more reliable")
    elif demand.households < 20:
        score -= 5
        assumptions.append("Small cluster — diversity factor less reliable")

    score = max(min(score, 85), 10)

    if score >= 65:
        moe = 15.0
        quality = "high" if score >= 75 else "medium"
        calibration = "partially_calibrated"
    elif score >= 45:
        moe = 22.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 30.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="peak_load_yr1",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_productive_use(
    cluster: ClusterInfo,
    has_crop_data: bool,
    has_crop_value: bool,
    has_large_bldg: bool,
) -> ConfidenceDimension:
    """Productive use demand share — TOR target ±25%."""
    score = 20  # inherently highest variability
    assumptions: list[str] = ["Productive use share estimated from population heuristics"]

    if has_crop_data:
        score += 20
        assumptions.append("Crop area data available for agricultural demand")
    if has_crop_value:
        score += 10
        assumptions.append("Crop value data informs willingness-to-pay")
    if has_large_bldg:
        score += 15
        assumptions.append("Large buildings detected — likely commercial/institutional")

    has_social = bool(cluster.has_education_facility or cluster.has_health_facility)
    if has_social:
        score += 10
        assumptions.append("Social infrastructure (school/clinic) demand included")

    score = max(min(score, 80), 10)

    if score >= 60:
        moe = 20.0
        quality = "medium"
        calibration = "partially_calibrated"
    elif score >= 40:
        moe = 30.0
        quality = "low"
        calibration = "partially_calibrated"
    else:
        moe = 40.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="productive_use_demand_share",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_solar_resource(
    solar: Optional[SolarResource],
    has_solar_api: bool,
) -> ConfidenceDimension:
    """Solar resource (annual GHI) — TOR target ±5%."""
    if has_solar_api:
        score = 90
        moe = 4.0
        quality = "high"
        calibration = "calibrated"
        assumptions = [
            "PVGIS satellite-derived GHI with multi-year average",
            "Validated against ground station network where available",
        ]
    elif solar is not None and solar.annual_ghi_kwh_m2 > 0:
        score = 70
        moe = 7.0
        quality = "medium"
        calibration = "partially_calibrated"
        assumptions = [
            f"GHI from {solar.data_source or 'alternative source'}",
            "Not cross-validated against PVGIS satellite data",
        ]
    else:
        score = 45
        moe = 12.0
        quality = "low"
        calibration = "uncalibrated"
        assumptions = [
            "GHI from cluster-level raster extraction (single-source)",
            "No monthly profile or temperature correction available",
        ]

    return ConfidenceDimension(
        dimension="solar_resource_ghi",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_generation_sizing(
    sizing: SystemSizing,
    has_solar_api: bool,
) -> ConfidenceDimension:
    """Generation capacity sizing — TOR target ±15%."""
    score = 45
    assumptions: list[str] = [
        "PV sizing from demand + solar margin heuristics",
        "Battery sized for autonomy and peak load requirements",
    ]

    if has_solar_api:
        score += 15
        assumptions.append("Solar resource from PVGIS — better yield estimate")

    # 8760 dispatch simulation quality
    unmet = sizing.unmet_energy_pct
    if unmet is not None:
        if unmet < 2.0:
            score += 20
            assumptions.append(
                f"8760-hour dispatch converged well (unmet {unmet:.1f}%)"
            )
        elif unmet < 5.0:
            score += 10
            assumptions.append(
                f"8760-hour dispatch acceptable (unmet {unmet:.1f}%)"
            )
        else:
            score -= 5
            assumptions.append(
                f"High unmet energy ({unmet:.1f}%) suggests sizing constraints"
            )
    else:
        assumptions.append("No dispatch simulation result — sizing from heuristics only")

    score = max(min(score, 90), 15)

    if score >= 70:
        moe = 12.0
        quality = "high"
        calibration = "calibrated"
    elif score >= 50:
        moe = 18.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 25.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="generation_capacity_sizing",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_capex(
    sizing: SystemSizing,
    financial: FinancialResults,
) -> ConfidenceDimension:
    """CAPEX (per kW installed) — TOR target ±20%."""
    score = 55  # benchmark costs from AMDA/SEforAll 2024
    assumptions: list[str] = [
        "Unit costs from AMDA/SEforAll 2024 mini-grid benchmark",
        "Distribution costs estimated from cluster geometry",
    ]

    pv = sizing.pv_kwp
    if 10 <= pv <= 100:
        score += 15
        assumptions.append("Standard system size range (10-100 kWp) — best calibrated")
    elif 5 <= pv < 10 or 100 < pv <= 500:
        score += 5
        assumptions.append("System outside optimal calibration range")
    else:
        score -= 10
        if pv < 5:
            assumptions.append("Very small system (<5 kWp) — limited benchmark data")
        else:
            assumptions.append("Very large system (>500 kWp) — limited benchmark data")

    score = max(min(score, 90), 20)

    if score >= 65:
        moe = 15.0
        quality = "high" if score >= 75 else "medium"
        calibration = "partially_calibrated"
    elif score >= 45:
        moe = 22.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 30.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="capex_per_kw",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_opex(
    is_remote: bool,
    financial: FinancialResults,
) -> ConfidenceDimension:
    """OPEX — TOR target ±25%."""
    score = 40
    assumptions: list[str] = [
        "OPEX estimated as percentage of CAPEX (limited field calibration)",
        "Includes generation O&M, distribution O&M, security, monitoring, insurance",
    ]

    if is_remote:
        score -= 10
        assumptions.append("Remote site (>30 km from road) — higher access cost uncertainty")
    else:
        score += 5
        assumptions.append("Accessible site — O&M logistics more predictable")

    score = max(min(score, 75), 15)

    if score >= 50:
        moe = 22.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 32.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="opex",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_tariff(
    sizing: SystemSizing,
    financial: FinancialResults,
    has_dre_demand: bool,
    has_solar_api: bool,
) -> ConfidenceDimension:
    """Cost-reflective tariff — TOR target ±15%."""
    # Derived metric: compounded from CAPEX + demand uncertainties
    base = 35
    assumptions: list[str] = [
        "Tariff derived from LCOE with 15% margin",
        "Compound uncertainty from CAPEX and demand estimates",
    ]

    if has_dre_demand:
        base += 15
        assumptions.append("DRE demand data reduces demand-side uncertainty")
    if has_solar_api:
        base += 10
        assumptions.append("PVGIS solar data reduces generation uncertainty")

    unmet = sizing.unmet_energy_pct
    if unmet is not None and unmet < 3.0:
        base += 10
        assumptions.append("Low unmet energy — dispatch simulation reliable")

    score = max(min(base, 85), 15)

    if score >= 65:
        moe = 12.0
        quality = "medium"
        calibration = "partially_calibrated"
    elif score >= 45:
        moe = 18.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 25.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="cost_reflective_tariff",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


def _score_ghg(
    carbon: Optional[CarbonAssessment],
    has_dre_demand: bool,
) -> ConfidenceDimension:
    """Avoided GHG emissions — TOR target ±20%."""
    score = 50  # conservative methodology reduces variance
    assumptions: list[str] = [
        "Baseline: diesel genset displacement (standard for off-grid)",
        "Conservative emission factor (IPCC Tier 1 defaults)",
    ]

    if carbon is not None:
        score += 10
        assumptions.append("Full carbon assessment computed")
    else:
        score -= 15
        assumptions.append("No carbon assessment — emission estimate is indicative")

    if has_dre_demand:
        score += 10
        assumptions.append("Demand from DRE data improves energy-served estimate")

    score = max(min(score, 85), 15)

    if score >= 65:
        moe = 15.0
        quality = "medium"
        calibration = "partially_calibrated"
    elif score >= 45:
        moe = 22.0
        quality = "medium"
        calibration = "partially_calibrated"
    else:
        moe = 30.0
        quality = "low"
        calibration = "uncalibrated"

    return ConfidenceDimension(
        dimension="avoided_ghg_emissions",
        confidence_score=score,
        margin_of_error_pct=moe,
        data_quality=quality,
        key_assumptions=assumptions,
        calibration_status=calibration,
    )


# ── Recommendations builder ───────────────────────────────────────

def _build_recommendations(
    cluster: ClusterInfo,
    has_dre: bool,
    has_dre_demand: bool,
    has_crop_data: bool,
    has_solar_api: bool,
    has_buildings: bool,
    has_rwi: bool,
    dimensions: list[ConfidenceDimension],
) -> list[str]:
    """Build prioritised list of data improvements that would most raise confidence."""
    recs: list[str] = []

    if not has_dre and not has_dre_demand:
        recs.append(
            "Obtain DRE Atlas data (connections + demand) — this is the single "
            "highest-impact improvement for demand and population confidence."
        )
    if not has_solar_api:
        recs.append(
            "Use PVGIS API for solar resource — improves GHI, sizing, and "
            "tariff confidence from ±12% to ±4%."
        )
    if not has_crop_data:
        recs.append(
            "Add agricultural land-use data — reduces productive use demand "
            "uncertainty from ±40% to ±20%."
        )
    if not has_buildings:
        recs.append(
            "Include building footprint counts — improves household estimate "
            "and productive use detection."
        )
    if not has_rwi:
        recs.append(
            "Add Relative Wealth Index data — improves demand tier assignment "
            "and willingness-to-pay estimate."
        )

    # Check if any dimension is particularly weak
    weakest = sorted(dimensions, key=lambda d: d.confidence_score)
    for dim in weakest[:2]:
        if dim.confidence_score < 40:
            recs.append(
                f"Priority: {dim.dimension} has confidence {dim.confidence_score}/100. "
                f"A field survey or additional data source would significantly "
                f"improve this estimate."
            )

    return recs
