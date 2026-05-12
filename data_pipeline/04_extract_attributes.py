#!/usr/bin/env python3
"""Extract raster attributes for each settlement cluster.

For each cluster polygon, sample all raster layers (GHI, wind, elevation,
slope, NTL, travel time, land cover) and compute zonal statistics.

Also computes distances to nearest grid lines and roads.

Requires: rasterio, geopandas, numpy, rasterstats

Usage:
    python 04_extract_attributes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from rasterstats import zonal_stats

from config import DOWNLOAD_DIR, MOZ_BBOX, PROCESSED_DIR  # type: ignore[import-untyped]

CLUSTERS_GPKG = PROCESSED_DIR / "vectors" / "moz_clusters.gpkg"
RASTER_DIR = PROCESSED_DIR / "rasters"
OUTPUT_GPKG = PROCESSED_DIR / "vectors" / "moz_clusters_enriched.gpkg"

RASTER_LAYERS = {
    "ghi_kwh_m2_year": ("moz_ghi_4326.tif", "mean"),
    "wind_speed_ms": ("moz_wind_4326.tif", "mean"),
    "elevation_m": ("moz_elevation_4326.tif", "mean"),
    "slope_deg": ("moz_slope_4326.tif", "mean"),
    "max_ntl": ("moz_ntl_4326.tif", "max"),
    "travel_time_hrs": ("moz_travel_time_4326.tif", "mean"),
    "land_cover": ("moz_land_cover_4326.tif", "majority"),
}


def extract_raster_attributes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Extract raster values for each cluster polygon."""
    for attr_name, (filename, stat) in RASTER_LAYERS.items():
        raster_path = RASTER_DIR / filename

        if not raster_path.exists():
            print(f"  [skip] {filename} not found — {attr_name} will be NULL")
            gdf[attr_name] = None
            continue

        print(f"  [extract] {attr_name} from {filename} (stat={stat})...")

        try:
            stats = zonal_stats(
                gdf.geometry,
                str(raster_path),
                stats=[stat],
                nodata=-9999,
                all_touched=True,
            )
            gdf[attr_name] = [s.get(stat) for s in stats]

            non_null = gdf[attr_name].notna().sum()
            print(f"           → {non_null}/{len(gdf)} clusters extracted")

            if attr_name == "travel_time_hrs":
                # Convert minutes to hours if source is in minutes
                median_val = gdf[attr_name].median()
                if median_val and median_val > 24:
                    gdf[attr_name] = gdf[attr_name] / 60.0
                    print(f"           → Converted from minutes to hours")

        except Exception as e:
            print(f"  [error] Failed to extract {attr_name}: {e}")
            gdf[attr_name] = None

    return gdf


def compute_distances(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Compute distance from each cluster centroid to nearest grid line and road."""
    centroids = gdf.geometry.centroid

    # Grid distances
    grid_files = [
        (PROCESSED_DIR / "vectors" / "moz_grid_mv.gpkg", "dist_grid_mv_km"),
        (PROCESSED_DIR / "vectors" / "moz_grid_hv.gpkg", "dist_grid_hv_km"),
    ]

    for grid_path, col_name in grid_files:
        if not grid_path.exists():
            # Try combined grid file
            combined = PROCESSED_DIR / "vectors" / "moz_grid_lines.gpkg"
            if combined.exists():
                grid = gpd.read_file(combined)
                voltage_col = "voltage_kv" if "voltage_kv" in grid.columns else None
                if voltage_col:
                    if "mv" in col_name:
                        grid = grid[grid[voltage_col] < 100]
                    else:
                        grid = grid[grid[voltage_col] >= 100]
            else:
                print(f"  [skip] {grid_path.name} not found — {col_name} will be NULL")
                gdf[col_name] = None
                continue
        else:
            grid = gpd.read_file(grid_path)

        if grid.empty:
            gdf[col_name] = None
            continue

        print(f"  [distance] Computing {col_name}...")
        # Approximate km conversion (1 degree ≈ 111 km at equator, adjust for latitude)
        grid_union = grid.geometry.unary_union
        distances_deg = centroids.distance(grid_union)
        # Convert degrees to approximate km at Mozambique latitude (-18°)
        gdf[col_name] = distances_deg * 111.0 * np.cos(np.radians(18))
        gdf[col_name] = gdf[col_name].round(1)
        print(f"           → median: {gdf[col_name].median():.1f} km")

    # Road distance
    road_path = PROCESSED_DIR / "vectors" / "moz_roads.gpkg"
    if road_path.exists():
        print(f"  [distance] Computing dist_road_km...")
        roads = gpd.read_file(road_path)
        road_union = roads.geometry.unary_union
        distances_deg = centroids.distance(road_union)
        gdf["dist_road_km"] = (distances_deg * 111.0 * np.cos(np.radians(18))).round(1)
        print(f"           → median: {gdf['dist_road_km'].median():.1f} km")
    else:
        print(f"  [skip] Roads not found — dist_road_km will be NULL")
        gdf["dist_road_km"] = None

    return gdf


def compute_electrification(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Estimate electrified population from NTL proxy."""
    if "max_ntl" in gdf.columns and gdf["max_ntl"].notna().any():
        # NTL > threshold as proxy for electrification (calibrated for Mozambique)
        ntl_threshold = 5.0
        gdf["electrification_rate"] = np.clip(gdf["max_ntl"].fillna(0) / 63.0, 0, 0.95)
        gdf["electrified_pop"] = (gdf["population"] * gdf["electrification_rate"]).round(0).astype(int)
        print(f"  [electrification] Estimated from NTL proxy")
        print(f"           → mean rate: {gdf['electrification_rate'].mean():.1%}")
    else:
        gdf["electrification_rate"] = 0
        gdf["electrified_pop"] = 0

    return gdf


def main():
    print("=" * 60)
    print("Attribute Extraction for Settlement Clusters")
    print("=" * 60)

    if not CLUSTERS_GPKG.exists():
        print(f"[error] Clusters not found: {CLUSTERS_GPKG}")
        print("Run 03_generate_clusters.py first.")
        sys.exit(1)

    print("\nLoading clusters...")
    gdf = gpd.read_file(CLUSTERS_GPKG)
    print(f"  {len(gdf):,} clusters loaded")

    print("\n--- Raster Attributes ---")
    gdf = extract_raster_attributes(gdf)

    print("\n--- Distance Calculations ---")
    gdf = compute_distances(gdf)

    print("\n--- Electrification Estimation ---")
    gdf = compute_electrification(gdf)

    print(f"\nSaving enriched clusters to {OUTPUT_GPKG}...")
    gdf.to_file(OUTPUT_GPKG, driver="GPKG")
    print(f"  [ok] {len(gdf):,} clusters with {len(gdf.columns)} attributes")

    print(f"\nAttribute completeness:")
    for col in gdf.columns:
        if col == "geometry":
            continue
        non_null = gdf[col].notna().sum()
        pct = non_null / len(gdf) * 100
        print(f"  {col:<25} {non_null:>6}/{len(gdf)}  ({pct:.0f}%)")

    print(f"\nNext step: python 05_load_postgis.py")


if __name__ == "__main__":
    main()
