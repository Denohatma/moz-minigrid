#!/usr/bin/env python3
"""Generate settlement clusters from population raster.

Implements the Khavari et al. (2021) methodology:
1. Apply population threshold to raster (>= 1 person/cell)
2. Find connected components (8-connectivity)
3. Vectorize connected regions into polygons
4. Split by admin boundaries (province level)
5. Classify urban/rural using Eurostat density thresholds
6. Filter minimum population (>= 50 people)

Requires: rasterio, numpy, scipy, shapely, geopandas, fiona

Usage:
    python 03_generate_clusters.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import fiona
import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from scipy.ndimage import label
from shapely.geometry import shape

from config import (  # type: ignore[import-untyped]
    DOWNLOAD_DIR,
    MOZ_BBOX,
    PROCESSED_DIR,
)

POP_RASTER = PROCESSED_DIR / "rasters" / "moz_population_4326.tif"
ADMIN_GPKG = DOWNLOAD_DIR / "gadm41_MOZ.gpkg"
OUTPUT_GPKG = PROCESSED_DIR / "vectors" / "moz_clusters.gpkg"

# Thresholds from Khavari et al. (2021)
POP_THRESHOLD = 1          # minimum people per cell to consider settled
MIN_CLUSTER_POP = 50       # minimum total population in a cluster
URBAN_DENSITY = 1500       # people/km² for urban classification (Eurostat)
PERIURBAN_DENSITY = 300    # people/km² for peri-urban


def main():
    print("=" * 60)
    print("Settlement Cluster Generation (Khavari et al. methodology)")
    print("=" * 60)

    if not POP_RASTER.exists():
        print(f"[error] Population raster not found: {POP_RASTER}")
        print("Run 02_harmonize_rasters.py first.")
        sys.exit(1)

    # Step 1: Read population raster
    print("\n1. Reading population raster...")
    with rasterio.open(POP_RASTER) as src:
        pop = src.read(1)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

        # Calculate cell area in km²
        pixel_height_deg = abs(transform.e)
        pixel_width_deg = abs(transform.a)
        # Approximate at mid-latitude of Mozambique (-18°)
        lat_mid = -18.0
        cell_area_km2 = (
            pixel_width_deg * 111.32 * np.cos(np.radians(lat_mid))
            * pixel_height_deg * 111.32
        )

    print(f"   Raster shape: {pop.shape}, CRS: {crs}")
    print(f"   Cell area: ~{cell_area_km2:.4f} km²")

    # Step 2: Threshold and find connected components
    print("\n2. Finding connected components (8-connectivity)...")
    if nodata is not None:
        pop = np.where(pop == nodata, 0, pop)
    settled = (pop >= POP_THRESHOLD).astype(np.int32)
    n_settled = settled.sum()
    print(f"   Settled cells: {n_settled:,}")

    structure = np.ones((3, 3), dtype=np.int32)  # 8-connectivity
    labeled, n_clusters_raw = label(settled, structure=structure)
    print(f"   Raw connected components: {n_clusters_raw:,}")

    # Step 3: Vectorize and compute attributes
    print("\n3. Vectorizing clusters and computing attributes...")
    cluster_shapes = []
    cluster_pops = []
    cluster_areas = []

    for geom_dict, cluster_val in features.shapes(
        labeled.astype(np.int32),
        transform=transform,
    ):
        if cluster_val == 0:
            continue

        geom = shape(geom_dict)
        mask = labeled == cluster_val
        total_pop = float(pop[mask].sum())

        if total_pop < MIN_CLUSTER_POP:
            continue

        n_cells = mask.sum()
        area_km2 = float(n_cells * cell_area_km2)

        cluster_shapes.append(geom)
        cluster_pops.append(int(total_pop))
        cluster_areas.append(round(area_km2, 3))

    print(f"   Clusters after filtering (pop >= {MIN_CLUSTER_POP}): {len(cluster_shapes):,}")

    if not cluster_shapes:
        print("[error] No clusters generated. Check population raster.")
        sys.exit(1)

    # Step 4: Build GeoDataFrame
    print("\n4. Building GeoDataFrame...")
    gdf = gpd.GeoDataFrame(
        {
            "cluster_id": range(1, len(cluster_shapes) + 1),
            "population": cluster_pops,
            "area_km2": cluster_areas,
            "geometry": cluster_shapes,
        },
        crs="EPSG:4326",
    )

    # Classify urban/rural
    gdf["density_km2"] = gdf["population"] / gdf["area_km2"].clip(lower=0.001)
    gdf["is_urban"] = 0
    gdf.loc[gdf["density_km2"] >= PERIURBAN_DENSITY, "is_urban"] = 1
    gdf.loc[gdf["density_km2"] >= URBAN_DENSITY, "is_urban"] = 2

    # Add centroids
    gdf["centroid_lat"] = gdf.geometry.centroid.y
    gdf["centroid_lon"] = gdf.geometry.centroid.x

    print(f"   Urban: {(gdf['is_urban'] == 2).sum()}")
    print(f"   Peri-urban: {(gdf['is_urban'] == 1).sum()}")
    print(f"   Rural: {(gdf['is_urban'] == 0).sum()}")
    print(f"   Total population: {gdf['population'].sum():,}")

    # Step 5: Spatial join with admin boundaries
    print("\n5. Assigning admin boundaries...")
    if ADMIN_GPKG.exists():
        # Read level 1 (provinces) and level 2 (districts)
        admin1 = gpd.read_file(ADMIN_GPKG, layer="ADM_ADM_1")
        admin2 = gpd.read_file(ADMIN_GPKG, layer="ADM_ADM_2")

        centroids = gdf.copy()
        centroids.geometry = gdf.geometry.centroid

        joined1 = gpd.sjoin(centroids, admin1[["NAME_1", "geometry"]], how="left", predicate="within")
        gdf["adm1_name"] = joined1["NAME_1"].values

        joined2 = gpd.sjoin(centroids, admin2[["NAME_2", "geometry"]], how="left", predicate="within")
        gdf["adm2_name"] = joined2["NAME_2"].values

        print(f"   Provinces assigned: {gdf['adm1_name'].nunique()}")
    else:
        print("   [skip] Admin boundary file not found — run 01_download_gis_data.py first")
        gdf["adm1_name"] = None
        gdf["adm2_name"] = None

    # Step 6: Save output
    print(f"\n6. Saving to {OUTPUT_GPKG}...")
    OUTPUT_GPKG.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUTPUT_GPKG, driver="GPKG")
    size_mb = OUTPUT_GPKG.stat().st_size / 1e6
    print(f"   [ok] {len(gdf):,} clusters, {size_mb:.1f} MB")

    # Summary statistics
    print(f"\n{'='*60}")
    print("Cluster Summary Statistics")
    print(f"{'='*60}")
    print(f"Total clusters: {len(gdf):,}")
    print(f"Total population: {gdf['population'].sum():,}")
    print(f"Mean population: {gdf['population'].mean():.0f}")
    print(f"Median population: {gdf['population'].median():.0f}")
    print(f"Population range: {gdf['population'].min()} – {gdf['population'].max():,}")
    print(f"Area range: {gdf['area_km2'].min():.3f} – {gdf['area_km2'].max():.1f} km²")
    print(f"\nNext step: python 04_extract_attributes.py")


if __name__ == "__main__":
    main()
