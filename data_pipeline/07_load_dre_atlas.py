#!/usr/bin/env python3
"""Load World Bank DRE Atlas settlement data into PostGIS.

Reads mozambique_dre_atlas_settlements.csv and inserts 56,510 settlements
into the settlement_clusters table with all DRE Atlas attributes.

Usage:
    python 07_load_dre_atlas.py
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

try:
    from config import DATABASE_URL
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://moz:moz@localhost:5433/moz")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "mozambique_dre_atlas_settlements.csv"
GEOJSON_PATH = PROJECT_ROOT / "mozambique_dre_atlas_settlements.geojson"
BATCH_SIZE = 500


def safe_float(val, default=None):
    try:
        v = float(val)
        return v if not math.isnan(v) else default
    except (ValueError, TypeError):
        return default


def safe_int(val, default=None):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_bool(val):
    if val in ("True", "true", "1"):
        return True
    if val in ("False", "false", "0"):
        return False
    return None


def derive_urban(population, building_density):
    pop = population or 0
    density = building_density or 0
    if pop > 5000 and density > 5:
        return 2
    if pop > 500 or density > 2:
        return 1
    return 0


def main():
    if not CSV_PATH.exists():
        print(f"[error] CSV not found: {CSV_PATH}")
        sys.exit(1)

    print(f"Loading DRE Atlas data from {CSV_PATH}")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("  Connected to database")

        existing = conn.execute(text("SELECT COUNT(*) FROM settlement_clusters")).scalar()
        if existing > 0:
            print(f"  Table has {existing} existing rows")
            resp = input("  Clear existing data and reload? [y/N] ")
            if resp.lower() == "y":
                conn.execute(text("DELETE FROM settlement_clusters"))
                conn.commit()
                print("  Cleared existing data")
            else:
                print("  Appending to existing data")

    insert_sql = text("""
        INSERT INTO settlement_clusters (
            cluster_id, geohash, geom, centroid,
            adm1_name, adm2_name, village_name,
            population, area_km2, is_urban,
            num_buildings, building_density_pct,
            large_buildings, medium_buildings, small_buildings, very_small_structures,
            has_nightlight, nightlight_overlap_pct, dist_nightlight_km,
            max_ntl, electrified_pop,
            pv_kwh_kwp_year, ghi_kwh_m2_year,
            dist_grid_mv_km, dist_grid_planned_km,
            dist_road_km, main_road_access,
            nearest_hub_name, dist_nearest_hub_km,
            closest_distance_water_km,
            num_education_facilities, has_education_facility,
            num_health_facilities, has_health_facility,
            mean_rwi,
            crop_types, ag_area_ha, ag_value_usd, ag_yield_kg_ha, ag_value_per_ha,
            security_risk, fatalities_25km, fatalities_50km, total_incidents_50km,
            dre_num_connections, dre_demand_kwh_day, dre_demand_per_conn_kwh_day,
            pop_source, data_year
        ) VALUES (
            :cluster_id, :geohash,
            ST_GeomFromText(:wkt, 4326),
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
            :adm1, :adm2, :village_name,
            :population, :area_km2, :is_urban,
            :num_buildings, :building_density_pct,
            :large_buildings, :medium_buildings, :small_buildings, :very_small_structures,
            :has_nightlight, :nightlight_overlap_pct, :dist_nightlight_km,
            :max_ntl, :electrified_pop,
            :pv_kwh_kwp_year, :ghi_kwh_m2_year,
            :dist_grid_mv_km, :dist_grid_planned_km,
            :dist_road_km, :main_road_access,
            :nearest_hub_name, :dist_nearest_hub_km,
            :closest_distance_water_km,
            :num_education_facilities, :has_education_facility,
            :num_health_facilities, :has_health_facility,
            :mean_rwi,
            :crop_types, :ag_area_ha, :ag_value_usd, :ag_yield_kg_ha, :ag_value_per_ha,
            :security_risk, :fatalities_25km, :fatalities_50km, :total_incidents_50km,
            :dre_num_connections, :dre_demand_kwh_day, :dre_demand_per_conn_kwh_day,
            'DRE_Atlas_WB', 2025
        )
    """)

    loaded = 0
    skipped = 0
    batch = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            lat = safe_float(row.get("lat"))
            lon = safe_float(row.get("lon"))
            if lat is None or lon is None:
                skipped += 1
                continue

            population = safe_int(row.get("population"), 0)
            building_density = safe_float(row.get("building_density_percent"), 0)
            overlap_pct = safe_float(row.get("overlap_percentage"), 0)
            pv_value = safe_float(row.get("pv_value"), 1800)

            wkt = row.get("geometry", "")
            if not wkt.startswith("MULTI"):
                wkt = f"MULTIPOLYGON EMPTY"

            params = {
                "cluster_id": i,
                "geohash": row.get("geohash", ""),
                "wkt": wkt,
                "lat": lat,
                "lon": lon,
                "adm1": row.get("admin_cgaz_1") or None,
                "adm2": row.get("admin_cgaz_2") or None,
                "village_name": row.get("village_name") or None,
                "population": max(population, 1),
                "area_km2": safe_float(row.get("hull_area"), 0.01),
                "is_urban": derive_urban(population, building_density),
                "num_buildings": safe_int(row.get("num_buildings")),
                "building_density_pct": building_density or None,
                "large_buildings": safe_int(row.get("large_buildings")),
                "medium_buildings": safe_int(row.get("medium_buildings")),
                "small_buildings": safe_int(row.get("small_buildings")),
                "very_small_structures": safe_int(row.get("very_small_structures")),
                "has_nightlight": safe_bool(row.get("has_nightlight", "")),
                "nightlight_overlap_pct": overlap_pct or None,
                "dist_nightlight_km": safe_float(row.get("distance_to_gridlight_targets")),
                "max_ntl": round(overlap_pct * 0.63, 1) if overlap_pct else 0,
                "electrified_pop": round(population * min(overlap_pct / 100.0, 1.0)) if overlap_pct else 0,
                "pv_kwh_kwp_year": pv_value,
                "ghi_kwh_m2_year": pv_value,
                "dist_grid_mv_km": safe_float(row.get("distance_to_existing_transmission_lines"), 100),
                "dist_grid_planned_km": safe_float(row.get("distance_to_planned_transmission_lines")),
                "dist_road_km": safe_float(row.get("dist_main_road_km"), 50),
                "main_road_access": safe_bool(row.get("main_road_access", "")),
                "nearest_hub_name": row.get("nearest_hub_name") or None,
                "dist_nearest_hub_km": safe_float(row.get("dist_nearest_hub_km")),
                "closest_distance_water_km": safe_float(row.get("closest_distance_water")),
                "num_education_facilities": safe_int(row.get("num_education_facilities")),
                "has_education_facility": safe_bool(row.get("has_education_facility", "")),
                "num_health_facilities": safe_int(row.get("num_health_facilities")),
                "has_health_facility": safe_bool(row.get("has_health_facility", "")),
                "mean_rwi": safe_float(row.get("mean_rwi")),
                "crop_types": row.get("crop_types") or None,
                "ag_area_ha": safe_float(row.get("ag_area")),
                "ag_value_usd": safe_float(row.get("ag_value")),
                "ag_yield_kg_ha": safe_float(row.get("ag_yield")),
                "ag_value_per_ha": safe_float(row.get("ag_value_area")),
                "security_risk": row.get("security_risk") or None,
                "fatalities_25km": row.get("fatalities_25km") or None,
                "fatalities_50km": row.get("fatalities_50km") or None,
                "total_incidents_50km": safe_int(row.get("total_incidents_50km")),
                "dre_num_connections": safe_int(row.get("num_connections")),
                "dre_demand_kwh_day": safe_float(row.get("demand")),
                "dre_demand_per_conn_kwh_day": safe_float(row.get("demand_connection")),
            }
            batch.append(params)

            if len(batch) >= BATCH_SIZE:
                with engine.connect() as conn:
                    conn.execute(insert_sql, batch)
                    conn.commit()
                loaded += len(batch)
                batch = []
                if loaded % 5000 == 0:
                    print(f"  Loaded {loaded:,} settlements...")

    if batch:
        with engine.connect() as conn:
            conn.execute(insert_sql, batch)
            conn.commit()
        loaded += len(batch)

    print(f"\nDone: {loaded:,} settlements loaded, {skipped} skipped")

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM settlement_clusters")).scalar()
        print(f"Total rows in settlement_clusters: {count:,}")


if __name__ == "__main__":
    main()
