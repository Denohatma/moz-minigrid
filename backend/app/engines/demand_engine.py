from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from app.schemas.site import ClusterInfo
from app.schemas.analysis import DemandEstimate

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

TIER_KWH_YEAR = {1: 38.7, 2: 219, 3: 803, 4: 2117, 5: 2993}

PROFILES = {
    "rural_residential": [
        0.010, 0.008, 0.008, 0.008, 0.010, 0.015,
        0.025, 0.030, 0.025, 0.020, 0.020, 0.020,
        0.020, 0.020, 0.020, 0.025, 0.035, 0.070,
        0.110, 0.130, 0.120, 0.090, 0.050, 0.020,
    ],
    "mixed_productive": [
        0.010, 0.008, 0.008, 0.008, 0.010, 0.020,
        0.035, 0.055, 0.065, 0.060, 0.055, 0.045,
        0.040, 0.040, 0.035, 0.035, 0.040, 0.060,
        0.085, 0.095, 0.080, 0.060, 0.035, 0.015,
    ],
    "commercial_periurban": [
        0.012, 0.010, 0.010, 0.010, 0.012, 0.020,
        0.040, 0.060, 0.065, 0.065, 0.060, 0.055,
        0.050, 0.050, 0.050, 0.050, 0.050, 0.055,
        0.065, 0.070, 0.060, 0.045, 0.025, 0.012,
    ],
}

MOTOR_KW = {
    "rural_residential": 0.0,
    "mixed_productive": 3.0,
    "commercial_periurban": 1.5,
}
LRA_MULTIPLIER = 4.0
GROWTH_RATE = 0.05
HORIZON_YEARS = 10

DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def estimate_demand(
    cluster: ClusterInfo, overrides: Optional[dict] = None
) -> tuple[DemandEstimate, list[float]]:
    """Estimate electricity demand and produce an 8,760-hour load profile.

    Returns the DemandEstimate for the API response plus an internal
    8,760-hour demand profile (kW per hour) for use by the sizing engine.
    """
    config = _load_config()
    overrides = overrides or {}

    is_urban = cluster.is_urban
    persons_per_hh = config.get(
        "persons_per_hh_urban" if is_urban >= 2 else "persons_per_hh_rural",
        3.8 if is_urban >= 2 else 4.5,
    )
    if "persons_per_hh" in overrides:
        persons_per_hh = float(overrides["persons_per_hh"])

    use_dre = (
        cluster.dre_num_connections
        and cluster.dre_demand_kwh_day
        and "households" not in overrides
        and "demand_tier" not in overrides
    )

    if use_dre:
        households = cluster.dre_num_connections
        daily_energy_kwh = cluster.dre_demand_kwh_day
        annual_energy_kwh = daily_energy_kwh * 365.0
        demand_per_conn = cluster.dre_demand_per_conn_kwh_day or (daily_energy_kwh / households)
        tier = _tier_from_demand_per_conn(demand_per_conn)
    else:
        unelectrified_pop = max(cluster.population - cluster.electrified_pop, 0)
        households = max(int(unelectrified_pop / persons_per_hh), 1)

        if "households" in overrides:
            households = int(overrides["households"])

        tier = _assign_demand_tier(cluster)
        if "demand_tier" in overrides:
            tier = int(overrides["demand_tier"])

        tier_kwh_year = TIER_KWH_YEAR[tier]
        annual_energy_kwh = households * tier_kwh_year
        daily_energy_kwh = annual_energy_kwh / 365.0

    profile_name = _select_profile(cluster)
    profile_shape = _load_profile(profile_name)

    load_profile_kw = [daily_energy_kwh * fraction for fraction in profile_shape]

    # --- Peak load engineering (Strand-Axelsson coincidence + motor surge + growth) ---
    n_customers = households
    coincidence = 0.2 + 0.8 / math.sqrt(max(n_customers, 1))
    diversity = coincidence  # backward-compatible alias
    p_steady = max(load_profile_kw) * coincidence
    largest_motor_kw = MOTOR_KW.get(profile_name, 0.0)
    p_with_surge = p_steady + largest_motor_kw * (LRA_MULTIPLIER - 1)
    peak_demand_kw = p_with_surge * (1 + GROWTH_RATE) ** HORIZON_YEARS

    hourly_8760 = _build_8760_demand(load_profile_kw)

    estimate = DemandEstimate(
        households=households,
        demand_tier=tier,
        daily_energy_kwh=round(daily_energy_kwh, 2),
        peak_demand_kw=round(peak_demand_kw, 2),
        annual_energy_kwh=round(daily_energy_kwh * 365, 1),
        load_profile_kw=[round(v, 3) for v in load_profile_kw],
        persons_per_hh=persons_per_hh,
    )
    return estimate, hourly_8760


def _build_8760_demand(load_profile_24h: list[float]) -> list[float]:
    """Expand 24-hour kW profile to 8,760 hours.

    Repeats the daily shape for each day of the year with a small
    monthly scaling to reflect seasonal variation in demand.
    """
    monthly_demand_scale = [
        1.05, 1.03, 1.00, 0.97, 0.93, 0.90,
        0.90, 0.93, 0.97, 1.00, 1.03, 1.05,
    ]

    profile: list[float] = []
    for m in range(12):
        scale = monthly_demand_scale[m]
        for _d in range(DAYS_PER_MONTH[m]):
            for h in range(24):
                profile.append(load_profile_24h[h] * scale)

    while len(profile) < 8760:
        profile.append(0.0)
    return profile[:8760]


def _tier_from_demand_per_conn(kwh_day: float) -> int:
    kwh_year = kwh_day * 365
    if kwh_year >= 2993:
        return 5
    if kwh_year >= 2117:
        return 4
    if kwh_year >= 803:
        return 3
    if kwh_year >= 219:
        return 2
    return 1


def _assign_demand_tier(cluster: ClusterInfo) -> int:
    tier_mapping = _load_tier_mapping()

    if cluster.is_urban >= 2:
        return tier_mapping.get("urban", 4)

    if cluster.is_urban == 1:
        has_economic = (
            (cluster.max_ntl > 15 and cluster.dist_road_km < 5)
            or (cluster.mean_rwi is not None and cluster.mean_rwi > 0)
            or (cluster.has_education_facility and cluster.has_health_facility)
        )
        if has_economic:
            return tier_mapping.get("periurban_high", 4)
        return tier_mapping.get("periurban", 3)

    has_road_access = cluster.main_road_access if cluster.main_road_access is not None else cluster.dist_road_km < 10
    has_ntl = cluster.has_nightlight if cluster.has_nightlight is not None else cluster.max_ntl > 5
    near_town = (cluster.travel_time_hrs is not None and cluster.travel_time_hrs < 2)
    has_facilities = bool(cluster.has_education_facility or cluster.has_health_facility)

    indicators = sum([has_road_access, has_ntl, near_town, has_facilities])

    if indicators >= 2:
        return tier_mapping.get("rural_connected", 2)

    return tier_mapping.get("rural_remote", 1)


def _select_profile(cluster: ClusterInfo) -> str:
    if cluster.is_urban >= 2:
        return "commercial_periurban"

    has_productive_use = (
        cluster.is_urban == 1
        or (cluster.large_buildings and cluster.large_buildings > 0)
        or (cluster.has_education_facility or cluster.has_health_facility)
        or (cluster.max_ntl > 10 and cluster.dist_road_km < 5)
    )
    if has_productive_use:
        return "mixed_productive"

    return "rural_residential"


def _load_profile(name: str) -> list[float]:
    profile_path = COUNTRY_DIR / "load_profiles" / f"{name}.json"
    if profile_path.exists():
        data = json.loads(profile_path.read_text())
        values = data.get("profile", data)
        if isinstance(values, list) and len(values) == 24:
            total = sum(values)
            return [v / total for v in values] if abs(total - 1.0) > 0.01 else values

    if name in PROFILES:
        return PROFILES[name]

    return PROFILES["rural_residential"]


def _load_tier_mapping() -> dict:
    mapping_path = COUNTRY_DIR / "demand_tier_mapping.json"
    if mapping_path.exists():
        return json.loads(mapping_path.read_text())
    return {
        "urban": 4,
        "periurban_high": 4,
        "periurban": 3,
        "rural_connected": 2,
        "rural_remote": 1,
    }


def _load_config() -> dict:
    config_path = COUNTRY_DIR / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}
