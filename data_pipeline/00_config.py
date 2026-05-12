"""Shared configuration for all pipeline scripts."""
from __future__ import annotations

import os
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
PROCESSED_DIR = BASE_DIR / "processed"
COUNTRY_DIR = PROJECT_DIR / "countries" / "mozambique"

for d in [DOWNLOAD_DIR, PROCESSED_DIR, PROCESSED_DIR / "rasters", PROCESSED_DIR / "vectors"]:
    d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://moz:moz_dev_2026@localhost:5433/moz",
)

# Mozambique bounding box (EPSG:4326)
MOZ_BBOX = (30.21, -26.87, 40.84, -10.47)  # (west, south, east, north)
MOZ_EPSG = 4326
TARGET_RESOLUTION = 0.001  # ~100m at equator

# Data sources with direct download URLs
SOURCES = {
    "worldpop": {
        "url": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/MOZ/moz_ppp_2020_1km_Aggregated_UNadj.tif",
        "filename": "moz_population_2020.tif",
        "description": "WorldPop population 2020 (1km, UN-adjusted)",
    },
    "ghi": {
        "url": "https://globalsolaratlas.info/download/mozambique",
        "filename": "moz_ghi.tif",
        "description": "Global Solar Atlas GHI (long-term average)",
        "manual": True,
        "instructions": "Download GHI GeoTIFF from https://globalsolaratlas.info/download/mozambique → 'GHI' layer → GeoTIFF",
    },
    "wind": {
        "url": "https://globalwindatlas.info/api/gis/country/MOZ/wind-speed/50",
        "filename": "moz_wind_50m.tif",
        "description": "Global Wind Atlas mean wind speed at 50m",
        "manual": True,
        "instructions": "Download from https://globalwindatlas.info → Mozambique → Download → Wind speed 50m → GeoTIFF",
    },
    "srtm": {
        "url": "https://elevation-tiles-prod.s3.amazonaws.com/skadi/",
        "filename": "moz_elevation.tif",
        "description": "SRTM 30m elevation (merged tiles)",
        "manual": True,
        "instructions": "Download SRTM tiles covering Mozambique from https://dwtkns.com/srtm30m/ or NASA Earthdata",
    },
    "ntl": {
        "url": "https://eogdata.mines.edu/nighttime_light/annual/v22/2023/VNL_v22_npp-j01_2023_global_vcmslcfg_c202402081600.average_masked.dat.tif.gz",
        "filename": "moz_ntl_2023.tif",
        "description": "VIIRS Nighttime Lights 2023 annual composite",
        "manual": True,
        "instructions": "Download from https://eogdata.mines.edu/nighttime_light/annual/v22/ → clip to Mozambique",
    },
    "travel_time": {
        "url": "https://data.malariaatlas.org/geoserver/Accessibility/ows?service=CSW&version=2.0.1&request=DirectDownload&ResourceId=Accessibility:202001_Global_Walking_Only_Travel_Time_To_Healthcare",
        "filename": "moz_travel_time.tif",
        "description": "Malaria Atlas Project travel time to nearest city",
        "manual": True,
        "instructions": "Download from https://malariaatlas.org/research-project/accessibility-to-cities/ → Walking travel time",
    },
    "land_cover": {
        "url": "https://zenodo.org/records/7254221/files/ESA_WorldCover_10m_2021_v200_S24E030_Map.tif",
        "filename": "moz_landcover.tif",
        "description": "ESA WorldCover 2021 (10m)",
        "manual": True,
        "instructions": "Download tiles covering Mozambique from https://zenodo.org/records/7254221",
    },
    "admin_boundaries": {
        "url": "https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_MOZ.gpkg",
        "filename": "gadm41_MOZ.gpkg",
        "description": "GADM 4.1 admin boundaries for Mozambique",
    },
    "grid_network": {
        "url": "https://zenodo.org/records/3628142/files/grid.gpkg",
        "filename": "gridfinder_global.gpkg",
        "description": "Gridfinder predicted grid network (global)",
        "manual": True,
        "instructions": "Download from https://zenodo.org/records/3628142 → grid.gpkg, then clip to Mozambique",
    },
    "osm_roads": {
        "url": "https://download.geofabrik.de/africa/mozambique-latest-free.shp.zip",
        "filename": "mozambique-roads.shp.zip",
        "description": "OpenStreetMap roads (Geofabrik extract)",
    },
}
