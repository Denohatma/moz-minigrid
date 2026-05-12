# GIS Data Pipeline

Processes raw GIS data for Mozambique into a PostGIS database that powers the Moz platform.

## Prerequisites

- Python 3.9+
- GDAL (`brew install gdal` on macOS)
- Docker (for PostGIS)
- ~5GB disk space for raw + processed data

## Setup

```bash
pip install -r requirements.txt
docker compose up -d db    # Start PostGIS
```

## Pipeline Steps

Run in order:

```bash
python 01_download_gis_data.py    # Download source datasets
python 02_harmonize_rasters.py    # Reproject & clip to Mozambique
python 03_generate_clusters.py    # Settlement clustering from population raster
python 04_extract_attributes.py   # Zonal stats for each cluster
python 05_load_postgis.py         # Load into PostGIS
python 06_validate_data.py        # Verify data quality
```

## Manual Downloads

Some datasets require free registration:

| Dataset | Where to register | Save as |
|---------|-------------------|---------|
| SRTM elevation | [NASA Earthdata](https://urs.earthdata.nasa.gov/) | `downloads/moz_elevation.tif` |
| Global Solar Atlas (GHI) | [globalsolaratlas.info](https://globalsolaratlas.info/download/mozambique) | `downloads/moz_ghi.tif` |
| Global Wind Atlas | [globalwindatlas.info](https://globalwindatlas.info) | `downloads/moz_wind_50m.tif` |
| VIIRS NTL | [eogdata.mines.edu](https://eogdata.mines.edu/nighttime_light/) | `downloads/moz_ntl_2023.tif` |
| ESA WorldCover | [zenodo.org](https://zenodo.org/records/7254221) | `downloads/moz_landcover.tif` |
| Gridfinder | [zenodo.org](https://zenodo.org/records/3628142) | `downloads/gridfinder_global.gpkg` |
| Travel time | [malariaatlas.org](https://malariaatlas.org/research-project/accessibility-to-cities/) | `downloads/moz_travel_time.tif` |

Auto-downloaded (no registration):
- WorldPop population (1km)
- GADM admin boundaries
- OSM roads (Geofabrik)
