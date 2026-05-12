# Moz — Mini-Grid Prefeasibility Platform for Mozambique

A web platform that generates investment-grade prefeasibility studies for solar+battery mini-grid sites in Mozambique from GPS coordinates.

## Architecture

- **Frontend**: Next.js 15 (App Router) + MapLibre GL JS + Recharts
- **Backend**: FastAPI (Python) — GIS processing, demand estimation, system sizing, financial modeling
- **Database**: PostgreSQL + PostGIS
- **Reports**: Puppeteer (PDF) + openpyxl (Excel)

## Project Structure

```
frontend/          # Next.js 15 web application
backend/           # FastAPI computation backend
  app/
    routers/       # API route handlers
    engines/       # Core computation (demand, sizing, financial, GIS)
    models/        # Database models
    schemas/       # Pydantic request/response schemas
    services/      # Business logic orchestration
countries/         # Country configuration packages
  mozambique/      # GIS data, financial defaults, demand mappings
data_pipeline/     # One-time data preparation scripts
database/          # SQL migrations
docs/              # Plans and brainstorm documents
```

## Getting Started

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Data Pipeline
```bash
cd data_pipeline
python 01_download_gis_data.py
python 02_harmonize_rasters.py
python 03_generate_clusters.py
python 04_extract_attributes.py
python 05_load_postgis.py
```
