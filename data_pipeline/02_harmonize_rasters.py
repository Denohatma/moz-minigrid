#!/usr/bin/env python3
"""Harmonize all raster layers: reproject to EPSG:4326, clip to Mozambique boundary.

Produces standardized GeoTIFFs in processed/rasters/ ready for attribute extraction.

Usage:
    python 02_harmonize_rasters.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from config import (  # type: ignore[import-untyped]
    DOWNLOAD_DIR,
    MOZ_BBOX,
    PROCESSED_DIR,
)

RASTER_LAYERS = {
    "population": "moz_population_2020.tif",
    "ghi": "moz_ghi.tif",
    "wind": "moz_wind_50m.tif",
    "elevation": "moz_elevation.tif",
    "ntl": "moz_ntl_2023.tif",
    "travel_time": "moz_travel_time.tif",
    "land_cover": "moz_landcover.tif",
}

OUTPUT_DIR = PROCESSED_DIR / "rasters"


def check_gdal():
    try:
        result = subprocess.run(["gdalwarp", "--version"], capture_output=True, text=True)
        print(f"GDAL: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("[error] gdalwarp not found. Install GDAL:")
        print("  macOS: brew install gdal")
        print("  Ubuntu: sudo apt install gdal-bin")
        return False


def harmonize_raster(name: str, src_file: str):
    src_path = DOWNLOAD_DIR / src_file
    dst_path = OUTPUT_DIR / f"moz_{name}_4326.tif"

    if dst_path.exists():
        print(f"  [skip] Already processed: {dst_path.name}")
        return True

    if not src_path.exists():
        print(f"  [skip] Source not found: {src_path.name} — download first")
        return False

    west, south, east, north = MOZ_BBOX

    cmd = [
        "gdalwarp",
        "-t_srs", "EPSG:4326",
        "-te", str(west), str(south), str(east), str(north),
        "-te_srs", "EPSG:4326",
        "-r", "bilinear",
        "-co", "COMPRESS=LZW",
        "-co", "TILED=YES",
        "-overwrite",
        str(src_path),
        str(dst_path),
    ]

    # Use nearest-neighbor for categorical data
    if name in ("land_cover",):
        cmd[cmd.index("bilinear")] = "near"

    print(f"  [process] {src_path.name} → {dst_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [error] gdalwarp failed:\n{result.stderr}")
        return False

    size_mb = dst_path.stat().st_size / 1e6
    print(f"  [ok] {size_mb:.1f} MB")
    return True


def derive_slope(elevation_path: Path):
    """Generate slope raster from elevation DEM."""
    slope_path = OUTPUT_DIR / "moz_slope_4326.tif"

    if slope_path.exists():
        print(f"  [skip] Already exists: {slope_path.name}")
        return True

    if not elevation_path.exists():
        print(f"  [skip] Elevation raster not found — cannot derive slope")
        return False

    cmd = [
        "gdaldem", "slope",
        str(elevation_path),
        str(slope_path),
        "-co", "COMPRESS=LZW",
        "-co", "TILED=YES",
    ]

    print(f"  [process] Deriving slope from elevation")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [error] gdaldem failed:\n{result.stderr}")
        return False

    print(f"  [ok] {slope_path.stat().st_size / 1e6:.1f} MB")
    return True


def main():
    print("=" * 60)
    print("Raster Harmonization (→ EPSG:4326, clipped to Mozambique)")
    print("=" * 60)

    if not check_gdal():
        sys.exit(1)

    ok = 0
    skip = 0
    for name, filename in RASTER_LAYERS.items():
        print(f"\n--- {name} ---")
        if harmonize_raster(name, filename):
            ok += 1
        else:
            skip += 1

    # Derive slope from elevation
    print(f"\n--- slope (derived) ---")
    elev_path = OUTPUT_DIR / "moz_elevation_4326.tif"
    derive_slope(elev_path)

    print(f"\nDone: {ok} processed, {skip} skipped")
    print("Next step: python 03_generate_clusters.py")


if __name__ == "__main__":
    main()
