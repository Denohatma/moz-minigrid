#!/usr/bin/env python3
"""Load processed GIS data into PostGIS database.

Loads:
- Settlement clusters (with all extracted attributes)
- Admin boundaries (GADM provinces + districts)
- Grid network lines (HV/MV)
- Road network (primary + secondary)

Requires: geopandas, sqlalchemy, geoalchemy2, psycopg2

Usage:
    python 05_load_postgis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
from sqlalchemy import create_engine, text

from config import DATABASE_URL, DOWNLOAD_DIR, PROCESSED_DIR  # type: ignore[import-untyped]

ENRICHED_CLUSTERS = PROCESSED_DIR / "vectors" / "moz_clusters_enriched.gpkg"
ADMIN_GPKG = DOWNLOAD_DIR / "gadm41_MOZ.gpkg"
GRID_GPKG = PROCESSED_DIR / "vectors" / "moz_grid_lines.gpkg"
ROADS_GPKG = PROCESSED_DIR / "vectors" / "moz_roads.gpkg"


def get_engine():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT PostGIS_Version()"))
        version = result.scalar()
        print(f"  Connected to PostGIS {version}")
    return engine


def load_clusters(engine):
    """Load enriched settlement clusters into PostGIS."""
    print("\n--- Loading Settlement Clusters ---")

    if not ENRICHED_CLUSTERS.exists():
        print(f"  [skip] Not found: {ENRICHED_CLUSTERS}")
        return

    gdf = gpd.read_file(ENRICHED_CLUSTERS)
    print(f"  Read {len(gdf):,} clusters")

    # Ensure geometry is MultiPolygon
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: g if g.geom_type == "MultiPolygon" else g.buffer(0) if g.is_empty else g
    )

    # Add centroid column
    gdf["centroid"] = gdf.geometry.centroid

    # Map column names to match schema
    col_map = {
        "cluster_id": "cluster_id",
        "population": "population",
        "area_km2": "area_km2",
        "is_urban": "is_urban",
        "adm1_name": "adm1_name",
        "adm2_name": "adm2_name",
        "max_ntl": "max_ntl",
        "electrified_pop": "electrified_pop",
        "electrification_rate": "electrification_rate",
        "ghi_kwh_m2_year": "ghi_kwh_m2_year",
        "wind_speed_ms": "wind_speed_ms",
        "elevation_m": "elevation_m",
        "slope_deg": "slope_deg",
        "land_cover": "land_cover",
        "dist_grid_mv_km": "dist_grid_mv_km",
        "dist_grid_hv_km": "dist_grid_hv_km",
        "dist_road_km": "dist_road_km",
        "travel_time_hrs": "travel_time_hrs",
    }

    # Keep only columns that exist
    existing = {k: v for k, v in col_map.items() if k in gdf.columns}
    load_gdf = gdf[list(existing.keys()) + ["geometry"]].rename(columns=existing)
    load_gdf = load_gdf.set_geometry("geometry")
    load_gdf.crs = "EPSG:4326"

    # Clear existing data and load
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE settlement_clusters RESTART IDENTITY CASCADE"))
        conn.commit()

    load_gdf.to_postgis(
        "settlement_clusters",
        engine,
        if_exists="append",
        index=False,
        dtype={"geometry": "geometry"},
    )
    print(f"  [ok] Loaded {len(load_gdf):,} clusters")


def load_admin_boundaries(engine):
    """Load GADM admin boundaries into PostGIS."""
    print("\n--- Loading Admin Boundaries ---")

    if not ADMIN_GPKG.exists():
        print(f"  [skip] Not found: {ADMIN_GPKG}")
        return

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE admin_boundaries RESTART IDENTITY"))
        conn.commit()

    total = 0

    # Level 1: Provinces
    try:
        adm1 = gpd.read_file(ADMIN_GPKG, layer="ADM_ADM_1")
        adm1_load = gpd.GeoDataFrame({
            "adm0_name": "Mozambique",
            "adm1_name": adm1["NAME_1"],
            "adm1_code": adm1.get("GID_1", adm1.index.astype(str)),
            "level": 1,
            "geom": adm1.geometry,
            "area_km2": adm1.geometry.to_crs(epsg=32736).area / 1e6,
        }, geometry="geom", crs="EPSG:4326")

        adm1_load.to_postgis("admin_boundaries", engine, if_exists="append", index=False)
        total += len(adm1_load)
        print(f"  [ok] {len(adm1_load)} provinces")
    except Exception as e:
        print(f"  [error] Level 1: {e}")

    # Level 2: Districts
    try:
        adm2 = gpd.read_file(ADMIN_GPKG, layer="ADM_ADM_2")
        adm2_load = gpd.GeoDataFrame({
            "adm0_name": "Mozambique",
            "adm1_name": adm2.get("NAME_1"),
            "adm2_name": adm2["NAME_2"],
            "adm2_code": adm2.get("GID_2", adm2.index.astype(str)),
            "level": 2,
            "geom": adm2.geometry,
            "area_km2": adm2.geometry.to_crs(epsg=32736).area / 1e6,
        }, geometry="geom", crs="EPSG:4326")

        adm2_load.to_postgis("admin_boundaries", engine, if_exists="append", index=False)
        total += len(adm2_load)
        print(f"  [ok] {len(adm2_load)} districts")
    except Exception as e:
        print(f"  [error] Level 2: {e}")

    print(f"  Total: {total} boundaries loaded")


def load_grid_network(engine):
    """Load grid lines into PostGIS."""
    print("\n--- Loading Grid Network ---")

    if not GRID_GPKG.exists():
        print(f"  [skip] Not found: {GRID_GPKG}")
        return

    grid = gpd.read_file(GRID_GPKG)
    print(f"  Read {len(grid):,} grid line segments")

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE grid_lines RESTART IDENTITY"))
        conn.commit()

    # Classify HV/MV
    if "voltage_kv" in grid.columns:
        grid["line_type"] = grid["voltage_kv"].apply(lambda v: "HV" if v >= 100 else "MV")
    else:
        grid["line_type"] = "MV"

    grid["status"] = "existing"
    grid["source"] = "gridfinder"

    # Compute length
    grid["length_km"] = grid.geometry.to_crs(epsg=32736).length / 1000

    load_cols = ["line_type", "status", "source", "length_km", "geometry"]
    if "voltage_kv" in grid.columns:
        load_cols.insert(1, "voltage_kv")

    grid[load_cols].to_postgis("grid_lines", engine, if_exists="append", index=False)

    hv = (grid["line_type"] == "HV").sum()
    mv = (grid["line_type"] == "MV").sum()
    print(f"  [ok] {hv} HV lines, {mv} MV lines")


def load_roads(engine):
    """Load road network into PostGIS."""
    print("\n--- Loading Roads ---")

    if not ROADS_GPKG.exists():
        print(f"  [skip] Not found: {ROADS_GPKG}")
        return

    roads = gpd.read_file(ROADS_GPKG)
    print(f"  Read {len(roads):,} road segments")

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE roads RESTART IDENTITY"))
        conn.commit()

    # Filter to major roads only
    major_types = {"motorway", "trunk", "primary", "secondary", "tertiary"}
    if "fclass" in roads.columns:
        roads = roads[roads["fclass"].isin(major_types)]
    elif "highway" in roads.columns:
        roads = roads[roads["highway"].isin(major_types)]

    roads["length_km"] = roads.geometry.to_crs(epsg=32736).length / 1000
    roads = roads.rename(columns={"fclass": "road_type"} if "fclass" in roads.columns else {})

    load_cols = [c for c in ["osm_id", "road_type", "name", "surface", "length_km", "geometry"] if c in roads.columns or c == "geometry"]
    roads[load_cols].to_postgis("roads", engine, if_exists="append", index=False)
    print(f"  [ok] {len(roads):,} major road segments loaded")


def main():
    print("=" * 60)
    print("PostGIS Data Loading")
    print("=" * 60)

    print("\nConnecting to database...")
    try:
        engine = get_engine()
    except Exception as e:
        print(f"[error] Cannot connect to database: {e}")
        print("Make sure PostgreSQL is running:")
        print("  docker compose up -d db")
        sys.exit(1)

    load_clusters(engine)
    load_admin_boundaries(engine)
    load_grid_network(engine)
    load_roads(engine)

    # Print summary
    print(f"\n{'='*60}")
    print("Database Summary")
    print(f"{'='*60}")
    with engine.connect() as conn:
        for table in ["settlement_clusters", "admin_boundaries", "grid_lines", "roads"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table:<25} {count:>8} rows")

    print(f"\nNext step: python 06_validate_data.py")


if __name__ == "__main__":
    main()
