from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Optional

import numpy as np

from app.schemas.site import ClusterInfo, SuitabilityScreening, SuitabilityWarning

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DRE_CSV_PATH = PROJECT_ROOT / "mozambique_dre_atlas_settlements.csv"

DATABASE_URL = os.environ.get("DATABASE_URL")

MOZ_LAT_MIN, MOZ_LAT_MAX = -26.87, -10.47
MOZ_LON_MIN, MOZ_LON_MAX = 30.21, 40.84

GRID_CRITICAL_KM = 1.0
GRID_WARNING_KM = 5.0
MIN_HOUSEHOLDS = 50
MAX_HOUSEHOLDS = 10000
HIGH_ELECTRIFICATION_RATIO = 0.5

_dre_data: Optional[dict] = None


def _load_dre_atlas() -> dict:
    """Load DRE Atlas CSV into memory with a BallTree for spatial lookup."""
    global _dre_data
    if _dre_data is not None:
        return _dre_data

    if not DRE_CSV_PATH.exists():
        _dre_data = {"loaded": False}
        return _dre_data

    rows = []
    lats = []
    lons = []

    with open(DRE_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (ValueError, KeyError):
                continue
            lats.append(lat)
            lons.append(lon)
            rows.append(row)

    if not rows:
        _dre_data = {"loaded": False}
        return _dre_data

    lat_arr = np.radians(np.array(lats, dtype=np.float64))
    lon_arr = np.radians(np.array(lons, dtype=np.float64))
    coords = np.column_stack([lat_arr, lon_arr])

    from scipy.spatial import cKDTree

    x = np.cos(lat_arr) * np.cos(lon_arr)
    y = np.cos(lat_arr) * np.sin(lon_arr)
    z = np.sin(lat_arr)
    tree = cKDTree(np.column_stack([x, y, z]))

    _dre_data = {
        "loaded": True,
        "rows": rows,
        "tree": tree,
        "lats": np.array(lats),
        "lons": np.array(lons),
    }
    return _dre_data


def _safe_float(val: str, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if not math.isnan(v) else default
    except (ValueError, TypeError):
        return default


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_bool(val: str) -> Optional[bool]:
    if val in ("True", "true", "1"):
        return True
    if val in ("False", "false", "0"):
        return False
    return None


def validate_coordinates(lat: float, lon: float) -> None:
    if not (MOZ_LAT_MIN <= lat <= MOZ_LAT_MAX and MOZ_LON_MIN <= lon <= MOZ_LON_MAX):
        raise ValueError(
            f"Coordinates ({lat}, {lon}) fall outside Mozambique. "
            f"Valid range: lat [{MOZ_LAT_MIN}, {MOZ_LAT_MAX}], lon [{MOZ_LON_MIN}, {MOZ_LON_MAX}]"
        )


def lookup_cluster(lat: float, lon: float) -> Optional[ClusterInfo]:
    """Find the nearest DRE Atlas settlement to the given point.

    Priority: PostGIS → DRE Atlas CSV → synthetic fallback.
    Raises ValueError if no settlement is found within 50 km.
    """
    validate_coordinates(lat, lon)

    if DATABASE_URL:
        result = _lookup_postgis(lat, lon)
        if result:
            return result

    result = _lookup_dre_atlas(lat, lon)
    if result:
        return result

    data = _load_dre_atlas()
    if data.get("loaded"):
        raise ValueError(
            f"No settlement found within 50 km of ({lat:.4f}, {lon:.4f}). "
            "The location may be in the ocean or an uninhabited area. "
            "Please select a point closer to a known settlement."
        )

    return _lookup_synthetic(lat, lon)


def _lookup_dre_atlas(lat: float, lon: float) -> Optional[ClusterInfo]:
    """Find the nearest DRE Atlas settlement using cKDTree."""
    data = _load_dre_atlas()
    if not data.get("loaded"):
        return None

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    x = math.cos(lat_rad) * math.cos(lon_rad)
    y = math.cos(lat_rad) * math.sin(lon_rad)
    z = math.sin(lat_rad)

    dist, idx = data["tree"].query([x, y, z])

    EARTH_RADIUS_KM = 6371.0
    dist_km = dist * EARTH_RADIUS_KM
    if dist_km > 50:
        return None

    row = data["rows"][idx]
    return _dre_row_to_cluster(row)


def _dre_row_to_cluster(row: dict) -> ClusterInfo:
    """Convert a DRE Atlas CSV row to a ClusterInfo."""
    population = _safe_int(row.get("population", "0"), 0)
    num_buildings = _safe_int(row.get("num_buildings", "0"), 0)
    building_density = _safe_float(row.get("building_density_percent", "0"))

    has_nightlight = _safe_bool(row.get("has_nightlight", ""))
    overlap_pct = _safe_float(row.get("overlap_percentage", "0"))

    if population > 5000 and building_density > 5:
        is_urban = 2
    elif population > 500 or building_density > 2:
        is_urban = 1
    else:
        is_urban = 0

    ntl_proxy = overlap_pct * 0.63 if overlap_pct else 0.0
    electrified_pop = round(population * min(overlap_pct / 100.0, 1.0)) if overlap_pct else 0

    pv_value = _safe_float(row.get("pv_value", "0"), 1800.0)
    dist_existing = _safe_float(row.get("distance_to_existing_transmission_lines", "50"), 50.0)
    dist_planned = _safe_float(row.get("distance_to_planned_transmission_lines", ""), 0.0)
    dist_road = _safe_float(row.get("dist_main_road_km", "10"), 10.0)
    dist_hub = _safe_float(row.get("dist_nearest_hub_km", ""), 0.0)
    travel_est = dist_hub / 30.0 if dist_hub > 0 else None

    return ClusterInfo(
        id=row.get("geohash", "unknown"),
        village_name=row.get("village_name") or None,
        admin_region=row.get("admin_cgaz_1") or None,
        admin_district=row.get("admin_cgaz_2") or None,
        population=max(population, 1),
        area_km2=round(_safe_float(row.get("hull_area", "0.1"), 0.1), 3),
        is_urban=is_urban,

        num_buildings=num_buildings or None,
        building_density_pct=round(building_density, 2) if building_density else None,
        large_buildings=_safe_int(row.get("large_buildings", ""), 0) or None,
        medium_buildings=_safe_int(row.get("medium_buildings", ""), 0) or None,
        small_buildings=_safe_int(row.get("small_buildings", ""), 0) or None,

        max_ntl=round(ntl_proxy, 1),
        electrified_pop=electrified_pop,
        has_nightlight=has_nightlight,
        nightlight_overlap_pct=round(overlap_pct, 1) if overlap_pct else None,

        ghi_kwh_m2_year=round(pv_value, 1),
        pv_kwh_kwp_year=round(pv_value, 1),
        wind_speed_ms=None,
        elevation_m=None,
        slope_deg=None,

        dist_grid_mv_km=round(dist_existing, 1),
        dist_grid_hv_km=None,
        dist_grid_planned_km=round(dist_planned, 1) if dist_planned else None,
        dist_road_km=round(dist_road, 1),
        travel_time_hrs=round(travel_est, 1) if travel_est else None,

        dre_demand_kwh_day=_safe_float(row.get("demand", ""), 0.0) or None,
        dre_demand_per_conn_kwh_day=_safe_float(row.get("demand_connection", ""), 0.0) or None,
        dre_num_connections=_safe_int(row.get("num_connections", ""), 0) or None,

        main_road_access=_safe_bool(row.get("main_road_access", "")),
        nearest_hub_name=row.get("nearest_hub_name") or None,
        dist_nearest_hub_km=round(dist_hub, 1) if dist_hub else None,
        closest_distance_water_km=_safe_float(row.get("closest_distance_water", ""), 0.0) or None,

        num_education_facilities=_safe_int(row.get("num_education_facilities", ""), 0) or None,
        has_education_facility=_safe_bool(row.get("has_education_facility", "")),
        num_health_facilities=_safe_int(row.get("num_health_facilities", ""), 0) or None,
        has_health_facility=_safe_bool(row.get("has_health_facility", "")),

        mean_rwi=_safe_float(row.get("mean_rwi", ""), 0.0) or None,

        crop_types=row.get("crop_types") or None,
        ag_area_ha=_safe_float(row.get("ag_area", ""), 0.0) or None,
        ag_value_usd=_safe_float(row.get("ag_value", ""), 0.0) or None,

        security_risk=row.get("security_risk") or None,
        fatalities_25km=row.get("fatalities_25km") or None,
        fatalities_50km=row.get("fatalities_50km") or None,
        total_incidents_50km=_safe_int(row.get("total_incidents_50km", ""), 0) or None,
    )


def _lookup_postgis(lat: float, lon: float) -> Optional[ClusterInfo]:
    """Query PostGIS for the nearest settlement cluster."""
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    cluster_id, population, area_km2, is_urban,
                    max_ntl, electrified_pop,
                    ghi_kwh_m2_year, wind_speed_ms,
                    elevation_m, slope_deg,
                    dist_grid_mv_km, dist_grid_hv_km,
                    dist_road_km, travel_time_hrs
                FROM settlement_clusters
                WHERE ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    50000  -- 50km search radius
                )
                ORDER BY ST_Distance(
                    centroid::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                )
                LIMIT 1
            """), {"lat": lat, "lon": lon}).fetchone()

            if not row:
                return None

            return ClusterInfo(
                id=str(row[0]),
                population=row[1],
                area_km2=round(row[2], 2),
                is_urban=row[3],
                max_ntl=round(row[4] or 0, 1),
                electrified_pop=round(row[5] or 0),
                ghi_kwh_m2_year=round(row[6] or 1800, 1),
                wind_speed_ms=round(row[7] or 4.0, 1) if row[7] else None,
                elevation_m=round(row[8] or 100, 0) if row[8] else None,
                slope_deg=round(row[9] or 2.0, 1) if row[9] else None,
                dist_grid_mv_km=round(row[10] or 50, 1),
                dist_grid_hv_km=round(row[11] or 80, 1) if row[11] else None,
                dist_road_km=round(row[12] or 10, 1),
                travel_time_hrs=round(row[13] or 2.0, 1) if row[13] else None,
            )
    except Exception:
        return None


def _lookup_synthetic(lat: float, lon: float) -> ClusterInfo:
    """Generate synthetic cluster data for development without data files."""
    seed = abs(hash((round(lat, 3), round(lon, 3)))) % 10000

    lat_factor = (lat - MOZ_LAT_MIN) / (MOZ_LAT_MAX - MOZ_LAT_MIN)
    lon_factor = (lon - MOZ_LON_MIN) / (MOZ_LON_MAX - MOZ_LON_MIN)

    population = 200 + (seed % 3000)
    area_km2 = 0.5 + (seed % 100) / 20.0
    is_urban = 2 if population > 2000 else (1 if population > 800 else 0)

    ghi = 1600 + lat_factor * 400 + (seed % 200)
    wind = 3.0 + lon_factor * 3.0 + (seed % 20) / 10.0
    max_ntl = (seed % 40) + (10 if is_urban >= 1 else 0)

    dist_mv = 5.0 + (seed % 200) / 5.0
    dist_hv = dist_mv + 10.0 + (seed % 100) / 5.0

    electrified_ratio = min(max_ntl / 63.0, 0.95)

    return ClusterInfo(
        id=str(seed),
        population=population,
        area_km2=round(area_km2, 2),
        is_urban=is_urban,
        max_ntl=round(max_ntl, 1),
        electrified_pop=round(population * electrified_ratio),
        ghi_kwh_m2_year=round(ghi, 1),
        wind_speed_ms=round(wind, 1),
        elevation_m=round(50 + (seed % 800), 0),
        slope_deg=round((seed % 150) / 10.0, 1),
        dist_grid_mv_km=round(dist_mv, 1),
        dist_grid_hv_km=round(dist_hv, 1),
        dist_road_km=round(1.0 + (seed % 50) / 5.0, 1),
        travel_time_hrs=round(0.5 + (seed % 40) / 10.0, 1),
    )


def screen_suitability(cluster: ClusterInfo) -> SuitabilityScreening:
    """Screen a cluster for mini-grid suitability and return warnings."""
    warnings: list[SuitabilityWarning] = []
    is_suitable = True

    config = _load_config()
    persons_per_hh = config.get("persons_per_hh_rural", 4.5)

    if cluster.dre_num_connections:
        households = cluster.dre_num_connections
    else:
        households = cluster.population / persons_per_hh

    if cluster.dist_grid_mv_km < GRID_CRITICAL_KM:
        warnings.append(SuitabilityWarning(
            type="grid_proximity",
            message=f"Site is only {cluster.dist_grid_mv_km:.1f} km from transmission grid — grid extension is likely cheaper than a mini-grid.",
            severity="error",
        ))
        is_suitable = False
    elif cluster.dist_grid_mv_km < GRID_WARNING_KM:
        warnings.append(SuitabilityWarning(
            type="grid_proximity",
            message=f"Site is {cluster.dist_grid_mv_km:.1f} km from transmission grid — grid extension may be more economical.",
            severity="warning",
        ))

    if cluster.dist_grid_planned_km and cluster.dist_grid_planned_km < GRID_WARNING_KM:
        warnings.append(SuitabilityWarning(
            type="planned_grid",
            message=f"Planned transmission line is {cluster.dist_grid_planned_km:.1f} km away — check national grid expansion plans.",
            severity="warning",
        ))

    if households < MIN_HOUSEHOLDS:
        warnings.append(SuitabilityWarning(
            type="population_low",
            message=f"Estimated {int(households)} connections — solar home systems may be more appropriate.",
            severity="warning",
        ))

    if households > MAX_HOUSEHOLDS:
        warnings.append(SuitabilityWarning(
            type="population_high",
            message=f"Estimated {int(households)} connections — consider utility-scale or grid extension solution.",
            severity="warning",
        ))

    if cluster.has_nightlight and cluster.nightlight_overlap_pct and cluster.nightlight_overlap_pct > 50:
        warnings.append(SuitabilityWarning(
            type="already_electrified",
            message=f"Settlement shows {cluster.nightlight_overlap_pct:.0f}% nightlight coverage. Verify electrification status on the ground.",
            severity="info",
        ))
    elif cluster.electrified_pop > 0:
        electrified_ratio = cluster.electrified_pop / max(cluster.population, 1)
        if electrified_ratio > HIGH_ELECTRIFICATION_RATIO and cluster.max_ntl > 20:
            warnings.append(SuitabilityWarning(
                type="already_electrified",
                message=f"Area appears ~{electrified_ratio:.0%} electrified based on nighttime lights. Verify on the ground.",
                severity="info",
            ))

    if cluster.security_risk and cluster.security_risk.lower() == "high":
        warnings.append(SuitabilityWarning(
            type="security_risk",
            message="High security risk area (ACLED conflict data). Factor security costs and risk into project planning.",
            severity="warning",
        ))

    return SuitabilityScreening(is_suitable=is_suitable, warnings=warnings)


def _load_config() -> dict:
    config_path = COUNTRY_DIR / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}
