---
title: "feat: Mini-Grid Prefeasibility Platform for Mozambique"
type: feat
status: active
date: 2026-05-12
origin: docs/brainstorms/2026-05-12-minigrid-prefeasibility-platform-requirements.md
---

# Mini-Grid Prefeasibility Platform for Mozambique

## Overview

A web platform that enables DFI analysts to generate investment-grade prefeasibility studies for solar+battery mini-grid sites in Mozambique from GPS coordinates alone. The system combines pre-loaded geospatial data (solar, population, grid proximity, terrain) with automated demand estimation, PV+battery sizing, and financial modeling to produce downloadable PDF reports and editable Excel financial models — no GIS or Python expertise required.

Target: GPS coordinate in → full prefeasibility package out, under 15 minutes.

## Problem Statement

(see origin: `docs/brainstorms/2026-05-12-minigrid-prefeasibility-platform-requirements.md`)

DFIs screening mini-grid investments in Mozambique currently rely on expensive consultant engagements or ad-hoc spreadsheets. There is no tool that combines Mozambique's geospatial context with financial modeling to produce standardized, comparable prefeasibility outputs at portfolio scale.

## Proposed Solution

A three-tier architecture:

1. **Next.js web frontend** with MapLibre GL JS interactive map of Mozambique, wizard-driven parameter input, and results dashboards
2. **FastAPI (Python) computation backend** handling GIS data extraction (rasterio), demand estimation, PV+battery sizing, and financial modeling
3. **PostgreSQL + PostGIS** database storing pre-processed settlement clusters, grid network, admin boundaries, and user projects

The platform ships with all core GIS layers pre-processed for Mozambique. Users enter GPS coordinates; the system identifies the settlement cluster, extracts geospatial attributes, estimates demand, sizes a solar+battery system, runs the financial model, and generates reports.

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js 15)              │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ MapLibre  │  │ Wizard   │  │ Results Dashboard │  │
│  │ GL JS Map │  │ Forms    │  │ Charts (Recharts) │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │ REST/SSE
┌────────────────────────┴────────────────────────────┐
│               BACKEND (FastAPI / Python)              │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ GIS      │  │ Sizing   │  │ Financial Model   │  │
│  │ Engine   │  │ Engine   │  │ Engine            │  │
│  │(rasterio)│  │          │  │                   │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
│  ┌──────────┐  ┌──────────┐                          │
│  │ PDF Gen  │  │ Excel Gen│                          │
│  │(Puppeteer│  │(openpyxl)│                          │
│  └──────────┘  └──────────┘                          │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────┐
│            DATABASE (PostgreSQL + PostGIS)            │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────┐  │
│  │ Settlement   │  │ Grid Lines │  │ User        │  │
│  │ Clusters     │  │ (HV/MV)    │  │ Projects    │  │
│  │ (polygons)   │  │ (lines)    │  │             │  │
│  └──────────────┘  └────────────┘  └─────────────┘  │
│  ┌──────────────┐  ┌────────────┐                    │
│  │ Admin        │  │ Raster     │                    │
│  │ Boundaries   │  │ Metadata   │                    │
│  └──────────────┘  └────────────┘                    │
└─────────────────────────────────────────────────────┘

RASTER FILES (filesystem / object storage)
  ├── solar_ghi.tif          (Global Solar Atlas, ~1km)
  ├── wind_speed.tif         (Global Wind Atlas, ~1km)
  ├── population.tif         (HRSL/GHS-POP, ~30m/250m)
  ├── nighttime_lights.tif   (VIIRS DNB, ~500m)
  ├── elevation.tif          (SRTM, ~30m)
  ├── slope.tif              (derived from SRTM)
  ├── land_cover.tif         (MODIS, ~500m)
  └── travel_time.tif        (MAP/Oxford, ~1km)
```

### Country-Extensible Design (R24)

All country-specific data and parameters are isolated into a **country configuration package**:

```
countries/
  mozambique/
    config.json          # currency, defaults, thresholds, regulatory flags
    financial_defaults.json
    demand_tier_mapping.json
    load_profiles/       # archetype hourly profiles
    rasters/             # GIS layers (GeoTIFF)
    vectors/             # clusters, grid, admin (loaded into PostGIS)
```

Adding a new country = creating a new config package + loading data. No code changes.

### Data Pipeline

**Pre-processing (one-time, before launch):**

1. **Source GIS data for Mozambique** — all layers harmonized to EPSG:4326 (WGS84):

| Layer | Source | Resolution | Format |
|-------|--------|-----------|--------|
| Solar GHI | Global Solar Atlas (World Bank) | ~1km | GeoTIFF |
| Wind speed | Global Wind Atlas (DTU) | ~1km | GeoTIFF |
| Population | HRSL (Facebook/CIESIN) | ~30m | GeoTIFF |
| Nighttime lights | VIIRS DNB annual composite | ~500m | GeoTIFF |
| Elevation | SRTM v4 (CGIAR-CSI) | ~30m | GeoTIFF |
| Slope | Derived from SRTM | ~30m | GeoTIFF |
| Land cover | MODIS MCD12Q1 | ~500m | GeoTIFF |
| Travel time | MAP/Oxford accessibility | ~1km | GeoTIFF |
| Grid network (HV/MV) | energydata.info (ESMAP) + OSM | Vector | PostGIS |
| Road network | OpenStreetMap | Vector | PostGIS |
| Admin boundaries | GADM v4.1 (level 0-2) | Vector | PostGIS |
| Settlement clusters | GEP pre-computed OR generate via Clustering repo | Vector | PostGIS |
| Hydropower sites | KTH dESA (energydata.info) | Vector | PostGIS |

2. **Generate settlement clusters** for Mozambique using the GEP Clustering methodology:
   - Input: HRSL population raster + VIIRS NTL + GADM admin boundaries (level 2)
   - Parameters: population threshold = 50 people/cell, 8-connected adjacency, split by admin level 2
   - Output per cluster: id, geometry (polygon), population, area_km2, max_NTL, electrified_pop, is_urban (0/1/2)
   - Store in PostGIS with GIST spatial index

3. **Pre-extract GIS attributes** for each cluster (attach raster values):
   - For each cluster polygon: mean GHI, mean wind speed, mean elevation, max slope, dominant land cover, min distance to HV/MV grid, min distance to road, travel time to nearest town
   - Store as columns on the cluster table — eliminates runtime raster queries for pre-computed clusters

### Site Analysis Pipeline (Runtime)

When a user enters a GPS coordinate:

```
GPS Point
  │
  ├─► 1. VALIDATION
  │     ├── Within Mozambique boundary? (ST_Contains query)
  │     ├── Coordinate format valid?
  │     └── FAIL: clear error with map showing point location
  │
  ├─► 2. CLUSTER IDENTIFICATION
  │     ├── Find settlement cluster containing the point (ST_Contains)
  │     ├── If no cluster: expand search to nearest cluster within 10km (ST_DWithin)
  │     ├── If still none: flag "no population data" → prompt for manual input
  │     └── Return: cluster geometry, pre-extracted attributes
  │
  ├─► 3. SITE SUITABILITY SCREENING
  │     ├── Grid proximity check:
  │     │     < 5km from MV line → WARNING: "Grid extension may be cheaper"
  │     │     < 1km from MV line → STRONG WARNING: "Not a mini-grid candidate"
  │     ├── Population check:
  │     │     < 50 households → WARNING: "Consider solar home systems"
  │     │     > 10,000 households → WARNING: "Consider utility-scale solution"
  │     ├── Already electrified check (NTL proxy):
  │     │     High NTL + high electrified_pop ratio → WARNING: "Area may already be electrified"
  │     └── Return: suitability flags (proceed/warning/block)
  │
  ├─► 4. DEMAND ESTIMATION (details below)
  │     └── Return: daily_energy_kwh, peak_demand_kw, hourly_profile, household_count, demand_tier
  │
  ├─► 5. USER REVIEW CHECKPOINT
  │     ├── Display: cluster boundary on map, population, demand tier, estimated demand
  │     ├── User can: adjust demand tier, override population, upload survey data (R5)
  │     └── User confirms → proceed to sizing
  │
  ├─► 6. SYSTEM SIZING (details below)
  │     └── Return: pv_kwp, battery_kwh, inverter_kva, distribution costs
  │
  ├─► 7. FINANCIAL MODEL (details below)
  │     └── Return: lcoe, irr, npv, payback, dscr, tariff, subsidy_gap, sensitivities
  │
  ├─► 8. GRID ARRIVAL RISK ASSESSMENT (details below)
  │     └── Return: grid_distance, risk_rating, scenario_impacts (if modeled)
  │
  └─► 9. REPORT GENERATION
        ├── PDF report (Puppeteer rendering HTML template)
        ├── Excel financial model (openpyxl with live formulas)
        └── Save to user project
```

### Demand Estimation Engine (R4)

**Step 1: Cluster characterization**
- Population from cluster attributes (calibrated to most recent year using national growth rate)
- Household count = population / persons_per_hh (rural: 4.5, urban: 3.8 — Mozambique INE defaults)
- Urban/rural from cluster is_urban attribute (0=rural, 1=peri-urban, 2=urban)

**Step 2: Electrification status**
- NTL-based proxy: clusters with max_NTL > threshold AND electrified_pop/population > 0.5 → likely already electrified
- Grid distance cross-check: < 5km from MV line → likely grid-connected
- Unelectrified population = total population - electrified population estimate

**Step 3: MTF demand tier assignment**

| Condition | Assigned Tier | kWh/HH/year |
|-----------|--------------|-------------|
| Rural, low NTL, no productive use indicators | Tier 1 | 38.7 |
| Rural, some NTL, near road | Tier 2 | 219 |
| Peri-urban or rural with commercial indicators | Tier 3 | 803 |
| Peri-urban, higher density, near town | Tier 4 | 2,117 |
| Urban fringe | Tier 5 | 2,993 |

Users can override the tier assignment. The mapping uses the OnSSET MTF values (see origin).

**Step 4: Load profile generation**

Critical gap identified by spec-flow analysis. Solution: **archetype load profiles**.

Define 3 standard 24-hour load profile shapes for Mozambique:

- **Rural residential**: evening peak (17:00-21:00), minimal daytime load. ~70% of energy consumed after sunset.
- **Mixed residential + productive**: dual peak — morning productive (08:00-12:00) + evening residential (17:00-21:00). ~40% daytime.
- **Commercial/peri-urban**: broader daytime consumption (07:00-18:00) + evening peak. ~55% daytime.

Each profile is normalized (sums to 1.0 over 24 hours). Scaled by daily energy demand to produce kW values per hour.

```
daily_energy_kwh = households × tier_kwh_per_year / 365
hourly_profile_kw = daily_energy_kwh × archetype_shape[hour]
peak_demand_kw = max(hourly_profile_kw)
```

Profile archetype selected based on: urban/rural classification + productive use indicator.

**Step 5: Demand growth projection (R9)**
- Connection ramp-up: S-curve reaching 100% of target households by year 5
- Consumption growth: 3% annual increase per connected household (tier migration)
- Productive use growth: 5% annual increase starting year 3
- Compound formula per year: `demand_year_n = connected_hh_n × (tier_kwh × 1.03^n + productive_kwh × 1.05^max(0, n-3))`

### Solar + Battery Sizing Engine (R7, R8)

Uses simplified analytical methodology validated against ESMAP/NREL benchmarks.

**PV Array Sizing:**

```
E_daily = daily_energy_kwh (from demand engine)
PSH = site GHI / 365 / 1.0  (convert kWh/m²/year to peak sun hours)

eta_system = 0.75 (composite: temp 0.90 × soiling 0.95 × wiring 0.97 × inverter 0.96 × battery_rt 0.92 × availability 0.98 × degradation 0.98)

evening_fraction = fraction of demand after sunset (from load profile)
charging_factor = 1.0 + (evening_fraction × 0.25)  # extra PV to charge batteries for evening load

PV_kWp = (E_daily × charging_factor) / (PSH × eta_system)
```

**Battery Sizing:**

```
evening_energy = E_daily × evening_fraction
DoA = 1.5  # days of autonomy (LFP default)
DoD = 0.85  # depth of discharge (LFP)

Battery_kWh_nominal = (evening_energy × DoA) / DoD
Battery_kWh_usable = evening_energy × DoA
```

**Inverter Sizing:**

```
power_factor = 0.85
safety_margin = 1.25  # accounts for motor starting surges

Inverter_kVA = peak_demand_kw / power_factor × safety_margin
```

**Distribution Network (R8):**

Based on OnSSET T&D methodology (see origin: GEP reference):

```
cluster_area_km2 = cluster area from PostGIS
hh_count = household count
persons_per_hh = from country config

LV_line_km = estimated from cluster area and household density
  (simplified: LV_km = sqrt(cluster_area_km2) × 2 × ceil(hh_count / 300))
service_transformers = ceil(peak_demand_kw / 50)  # 50 kVA each
meters = hh_count
service_connections = hh_count
```

**Year-over-year sizing:** Size for year-5 demand (when connections fully ramped). Include 10% headroom for growth years 5-10.

### Financial Model Engine (R10-R15)

**Cost Structure (Mozambique defaults, all configurable):**

| Component | Unit Cost | Source |
|-----------|----------|-------|
| PV modules + mounting | $1,100/kWp | SEforAll 2024 benchmark |
| LFP battery (installed) | $450/kWh | AMDA 2024 benchmark |
| Inverter + BOS | $400/kVA | AMDA 2024 benchmark |
| LV distribution | $1,200/connection | ESMAP estimate |
| Meters (prepaid) | $80/unit | Market estimate |
| Service transformer (50 kVA) | $4,250/unit | OnSSET defaults |
| Installation & commissioning | 15% of equipment | Industry standard |
| Development & soft costs | 10% of CAPEX | Industry standard |
| Annual O&M | 3% of CAPEX | SEforAll benchmark |
| Battery replacement (year 12) | 80% of original battery cost | Degradation adjusted |
| Inverter replacement (year 15) | 100% of original inverter cost | End of life |

**CAPEX Calculation:**

```
capex_pv = PV_kWp × cost_per_kwp
capex_battery = Battery_kWh_nominal × cost_per_kwh
capex_inverter = Inverter_kVA × cost_per_kva
capex_distribution = hh_count × cost_per_connection + transformers × cost_per_transformer
capex_meters = hh_count × cost_per_meter
capex_equipment = capex_pv + capex_battery + capex_inverter + capex_distribution + capex_meters
capex_installation = capex_equipment × 0.15
capex_soft = (capex_equipment + capex_installation) × 0.10
TOTAL_CAPEX = capex_equipment + capex_installation + capex_soft
```

**LCOE Calculation (R10):**

```
For t = 0 to project_life (25 years):
  C_t = CAPEX (year 0) + OPEX_t + replacements_t
  E_t = annual_energy_served_t (accounting for connection ramp-up and growth)

LCOE = Σ(C_t / (1+r)^t) / Σ(E_t / (1+r)^t)

Default discount rate r = 10% (nominal, DFI standard for SSA)
```

**Revenue & Return Metrics (R11):**

```
revenue_t = energy_served_t × tariff + connection_fees_t
opex_t = TOTAL_CAPEX × om_rate
free_cash_flow_t = revenue_t - opex_t - replacements_t

Project IRR = rate where NPV of free_cash_flows = TOTAL_CAPEX
NPV = Σ(free_cash_flow_t / (1+r)^t) - TOTAL_CAPEX
Payback period = first year where cumulative cash flow ≥ 0
DSCR = (revenue_t - opex_t) / debt_service_t (if debt-financed)
```

**Tariff & Affordability Analysis (R12):**

```
cost_reflective_tariff = LCOE × (1 + margin)  # margin for profit/contingency
affordable_tariff = derived from poverty/income data or default $0.35/kWh
affordability_gap = cost_reflective_tariff - affordable_tariff
```

**Subsidy Gap (R13):**

```
NPV_costs = Σ(C_t / (1+r)^t)
NPV_revenue_at_affordable_tariff = Σ(E_t × affordable_tariff / (1+r)^t)
total_subsidy_gap = NPV_costs - NPV_revenue_at_affordable_tariff
subsidy_per_connection = total_subsidy_gap / hh_count
subsidy_pct_capex = total_subsidy_gap / TOTAL_CAPEX × 100
```

**Sensitivity Analysis (R14):**

Run ±20% variations on 6 key parameters:
1. CAPEX (total)
2. Demand growth rate
3. Tariff level
4. Discount rate
5. Battery replacement cost
6. Grant percentage

Output: tornado chart data (parameter, low_value, base_value, high_value, IRR_at_low, IRR_at_base, IRR_at_high).

**Currency Model:**
- Primary calculation in USD
- MZN conversion for tariff display and local cost inputs
- Configurable exchange rate (default: current market rate)
- All outputs presented in both USD and MZN

### Grid Arrival Risk Engine (R16, R17)

**Grid proximity assessment:**

```sql
-- Nearest HV line distance
SELECT ST_Distance(cluster.geom::geography, hv.geom::geography) / 1000 AS dist_km
FROM grid_lines hv
ORDER BY hv.geom <-> cluster.geom LIMIT 1;

-- Same for MV lines
```

**Risk rating:**

| Distance to MV | Distance to HV | Risk Level | Label |
|---------------|---------------|-----------|-------|
| < 5 km | any | Critical | Grid extension likely cheaper |
| 5-15 km | < 30 km | High | Grid may arrive within 10 years |
| 15-30 km | < 50 km | Medium | Grid possible within 20 years |
| > 30 km | > 50 km | Low | Outside EDM 30km mandate |

**Regulatory context (Mozambique-specific):**
- EDM is mandated to electrify populations within 30km of existing/planned grid or substations (see origin: best practices research — ARENE framework)
- ARENE Normative Resolution No. 2/2022 governs mini-grid interconnection — where this applies, model grid arrival scenarios:
  - Scenario A: No grid arrival (base case)
  - Scenario B: Grid arrives at year 5 — show stranded asset impact
  - Scenario C: Grid arrives at year 10 — show reduced project life impact
  - For each scenario: adjusted IRR, NPV, and recovery of investment at point of handover

### Report Generation

**PDF Report (R20) — Puppeteer-based:**

An HTML report template (React component) rendered server-side, then printed to PDF via headless Chromium:

Sections:
1. Cover page (site name, date, platform branding)
2. Executive summary (1-page: key metrics table, go/no-go recommendation)
3. Site description (map with cluster boundary highlighted, satellite imagery, key GIS attributes)
4. Population & demand analysis (cluster data, demand tier, load profile chart, growth projections)
5. System sizing (PV, battery, inverter specs; component table; schematic)
6. Financial summary (CAPEX breakdown waterfall chart, LCOE, IRR, NPV, payback)
7. Tariff & affordability (cost-reflective vs affordable tariff, subsidy gap)
8. Sensitivity analysis (tornado chart, scenario table)
9. Risk assessment (grid arrival, demand uncertainty, regulatory)
10. Assumptions & methodology (all parameters listed, data sources)

**Excel Financial Model (R21) — openpyxl:**

Workbook structure:
- **Inputs** sheet: all assumptions with yellow-highlighted editable cells
- **Demand** sheet: year-by-year demand projections with formulas
- **Sizing** sheet: system component calculations
- **Cash Flow** sheet: 25-year cash flow with CAPEX, revenue, OPEX, replacements
- **Returns** sheet: IRR, NPV, payback, DSCR calculations (Excel formulas, not hardcoded)
- **Sensitivity** sheet: data tables for parameter sweeps
- **Charts** sheet: CAPEX waterfall, cash flow bar chart, sensitivity tornado

Key design: all downstream sheets reference the Inputs sheet via cell references, so analysts can change any assumption and see results update automatically.

## Implementation Phases

### Phase 1: Foundation & Data Pipeline (Weeks 1-3)

**Goal:** Project scaffolding, GIS data sourced and processed, database seeded.

**Tasks:**

- [x] Initialize Next.js 15 project with App Router, TypeScript, Tailwind CSS
- [x] Set up FastAPI Python backend with project structure
- [x] Set up PostgreSQL + PostGIS database (Docker Compose + 6 SQL migrations)
- [x] Define country config schema (`countries/mozambique/config.json`)
- [x] Source and download all GIS layers for Mozambique (pipeline script with auto/manual download)
- [x] Harmonize all raster layers to EPSG:4326, clip to Mozambique boundary
- [x] Run GEP Clustering algorithm on Mozambique population data → generate settlement clusters
- [x] Pre-extract raster attributes for each cluster (GHI, wind, elevation, slope, land cover, travel time, NTL)
- [x] Load vector data into PostGIS (clusters, grid lines, admin boundaries, roads)
- [x] Build and test raster point-query API endpoint (FastAPI + rasterio)
- [x] Build and test cluster lookup API endpoint (PostGIS ST_Contains + synthetic fallback)
- [x] Create seed data validation notebook — verify extracted values match known sites

**Key files:**
```
moz-platform/
  frontend/                    # Next.js 15
    app/
    package.json
  backend/                     # FastAPI
    app/
      main.py
      routers/
        sites.py
        analysis.py
        reports.py
      engines/
        gis_engine.py
        demand_engine.py
        sizing_engine.py
        financial_engine.py
      models/
      schemas/
    requirements.txt
  countries/
    mozambique/
      config.json
      financial_defaults.json
      demand_tier_mapping.json
      load_profiles/
        rural_residential.json
        mixed_productive.json
        commercial_periurban.json
      rasters/
      vectors/
  data_pipeline/               # One-time scripts
    01_download_gis_data.py
    02_harmonize_rasters.py
    03_generate_clusters.py
    04_extract_attributes.py
    05_load_postgis.py
    06_validate_data.ipynb
  docker-compose.yml
```

**Success criteria:** Can query any GPS point in Mozambique and get back cluster ID + all GIS attributes via API.

### Phase 2: Core Computation Engines (Weeks 3-6)

**Goal:** Demand estimation, system sizing, and financial model engines working end-to-end.

**Tasks:**

- [x] Implement demand estimation engine (`demand_engine.py`):
  - Cluster characterization (population, households, urban/rural)
  - Electrification status assessment (NTL + grid distance)
  - MTF demand tier assignment with configurable mapping
  - Load profile generation from archetype library
  - Demand growth projection (S-curve connections + consumption growth)
- [x] Implement system sizing engine (`sizing_engine.py`):
  - PV array sizing (E_daily, PSH, eta_system, charging factor)
  - Battery sizing (evening energy fraction, DoA, DoD)
  - Inverter sizing (peak load, power factor, safety margin)
  - Distribution network estimation (LV lines, transformers, meters)
  - Year-5 target sizing with headroom
- [x] Implement financial model engine (`financial_engine.py`):
  - CAPEX calculation from component quantities × unit costs
  - 25-year cash flow projection (revenue, OPEX, replacements)
  - LCOE calculation (discounted costs / discounted generation)
  - Return metrics (IRR, NPV, payback, DSCR)
  - Tariff determination (cost-reflective and affordable)
  - Subsidy gap calculation (per connection, total, % CAPEX)
  - Sensitivity analysis (6-parameter sweep)
  - Currency conversion (USD ↔ MZN)
- [x] Implement grid arrival risk engine:
  - Grid proximity query (PostGIS nearest line)
  - Risk rating assignment
  - Grid arrival scenario modeling (years 5, 10)
- [x] Implement site suitability screening:
  - GPS validation (within Mozambique)
  - Grid proximity warning thresholds
  - Population min/max thresholds
  - Electrification status check
- [x] Build end-to-end analysis API endpoint (`POST /api/analyze-site`)
  - Input: GPS coordinate + optional parameter overrides
  - Output: complete analysis results JSON
- [ ] Write unit tests for each engine with known-site benchmarks
- [ ] Validate outputs against manually-prepared prefeasibility for 3+ known sites

**Success criteria:** API endpoint accepts GPS coordinate, returns complete analysis JSON with demand, sizing, financials, and risk assessment. LCOE values within 15% of manual calculations for test sites.

### Phase 3: Web Interface (Weeks 5-8)

**Goal:** Complete web UI with map, wizard flow, and results dashboard.

**Tasks:**

- [x] Implement interactive map page (`app/(map)/page.tsx`):
  - MapLibre GL JS with satellite+labels base layer (MapTiler)
  - Mozambique admin boundary outline
  - Grid network overlay (HV/MV lines, toggleable)
  - Settlement clusters overlay (color-coded by population)
  - Solar GHI raster overlay (toggleable heatmap)
  - Click-to-select site (places pin, shows coordinates)
  - GPS coordinate manual entry with format validation
  - Geocoding search bar (search by place name)
- [x] Implement site analysis wizard:
  - Step 1: Site selection (map or coordinates) → validation → suitability screening
  - Step 2: Data review (cluster boundary, population, demand tier, GIS attributes) with override options
  - Step 3: Parameters (financial assumptions form with Mozambique defaults, all editable)
  - Step 4: Results (runs analysis, shows progress via SSE streaming)
- [x] Implement results dashboard (single site):
  - Key metrics cards (LCOE, IRR, NPV, subsidy gap, population served)
  - System sizing summary (PV kWp, battery kWh, inverter kVA)
  - CAPEX waterfall chart (Recharts)
  - Load profile chart (24-hour)
  - Cash flow bar chart (25-year)
  - Sensitivity tornado chart
  - Grid arrival risk indicator
  - Map with cluster boundary highlighted
- [ ] Implement user data upload (R5):
  - CSV/Excel upload for demand data
  - Column mapping interface
  - Preview and validation before applying
  - Side-by-side comparison: system estimate vs uploaded data
- [ ] Implement batch upload (R6):
  - CSV/Excel file with GPS coordinates + optional site names
  - Template download
  - Upload validation (format, within Mozambique, duplicates)
  - Batch processing with progress indicator
  - Overlap detection between site catchment areas
- [ ] Implement parameter override UI:
  - Demand tier selector
  - Population/household count manual entry
  - Financial assumptions form (all R15 parameters)
  - "Reset to defaults" button

**Success criteria:** User can complete the full flow (GPS → review → results) in the browser. Map loads with all overlays. All charts render correctly.

### Phase 4: Reports & Export (Weeks 7-9)

**Goal:** PDF and Excel report generation, batch export.

**Tasks:**

- [x] Build PDF report HTML template (React component):
  - Cover page with site name and platform branding
  - Executive summary with key metrics table
  - Site map (static MapLibre render or map screenshot)
  - Demand analysis section with load profile chart
  - System sizing table
  - Financial summary with CAPEX waterfall and cash flow charts
  - Tariff & affordability section
  - Sensitivity tornado chart
  - Grid arrival risk section
  - Assumptions appendix
- [ ] Set up Puppeteer service for HTML-to-PDF rendering
- [x] Build Excel financial model template (`openpyxl`):
  - Inputs sheet with all assumptions (yellow cells = editable)
  - Demand sheet with growth formulas
  - Sizing sheet with component calculations
  - 25-year cash flow sheet with Excel formulas (not hardcoded values)
  - Returns sheet (IRR via `=IRR()`, NPV via `=NPV()`)
  - Sensitivity data tables
  - Charts (CAPEX waterfall, cash flow, sensitivity)
- [x] Implement report generation API endpoints:
  - `POST /api/reports/pdf/{analysis_id}` → PDF download
  - `POST /api/reports/excel/{analysis_id}` → Excel download
- [ ] Implement batch export (R22):
  - Portfolio summary PDF (aggregated metrics across all sites)
  - Individual site PDFs
  - ZIP packaging for download
- [x] Add "Download PDF" and "Download Excel" buttons to results dashboard
- [ ] Test report quality with sample sites — verify charts render, numbers match dashboard

**Success criteria:** PDF is investor-grade quality with maps, charts, and tables. Excel formulas are live (analysts can change inputs and see recalculated outputs). Batch export produces a clean ZIP.

### Phase 5: Multi-Site, Users & Polish (Weeks 8-11)

**Goal:** Portfolio comparison, user accounts, and production readiness.

**Tasks:**

- [ ] Implement multi-site comparison dashboard (R18):
  - Sortable table: site name, LCOE, IRR, subsidy gap/connection, population, demand density
  - Color-coded viability indicators (green/yellow/red)
  - Map view with all sites plotted, color-coded by metric
  - Click site row → navigate to detailed single-site view
- [ ] Implement portfolio summary view (R19):
  - Total investment required across all sites
  - Total population served
  - Average LCOE, IRR, subsidy gap
  - Portfolio CAPEX breakdown chart
- [ ] Implement catchment overlap detection:
  - When batch sites share the same cluster, flag and let user choose resolution
  - Options: merge into single site, assign households by proximity, keep separate with warning
- [ ] Implement user accounts (R25):
  - Authentication (email/password or OAuth)
  - Project creation and management
  - Save/load analyses
  - Share analysis via link (view-only)
- [ ] Implement navigation and layout:
  - Dashboard home (recent projects, quick actions)
  - Project list view
  - Settings page (default parameters, currency preference)
- [ ] Error handling and edge cases:
  - Graceful handling of partial batch failures (show succeeded + failed sites)
  - Loading states and progress indicators throughout
  - Input validation with helpful error messages
  - Timeout handling for long-running analyses
- [ ] Performance optimization:
  - Target: single site analysis < 30 seconds backend processing
  - Target: batch of 20 sites < 10 minutes
  - Raster dataset preloading at server startup
  - PostGIS query optimization with proper spatial indexes
- [ ] Localization preparation:
  - English UI (primary)
  - Portuguese labels for Mozambique place names on map
  - All user-facing strings in i18n-ready format

**Success criteria:** Full end-to-end platform working. 20-site batch completes within 10 minutes. User can save, reload, and share analyses.

## System-Wide Impact

### Interaction Graph

```
User clicks map → MapLibre click handler → sends GPS to Next.js API route
  → Next.js proxies to FastAPI /analyze-site
    → GIS Engine: PostGIS cluster lookup + rasterio point query
    → Demand Engine: tier assignment + load profile + growth projection
    → Sizing Engine: PV + battery + inverter + distribution calculation
    → Financial Engine: CAPEX + cash flow + LCOE + IRR + sensitivity
    → Grid Risk Engine: PostGIS nearest-line + risk rating
  → JSON response streamed back via SSE (progress updates per stage)
  → Frontend renders results dashboard + charts
```

Report generation is a separate request triggered by user action (not automatic).

### Error & Failure Propagation

| Error Point | Impact | Handling |
|------------|--------|---------|
| GPS outside Mozambique | Blocks analysis | Immediate validation error with map feedback |
| No cluster found | Blocks demand estimation | Prompt user for manual population input |
| Raster read failure (corrupt file) | Blocks GIS extraction | Return available data, flag missing layers |
| Demand estimation produces 0 | Blocks sizing | Minimum demand floor (Tier 1 × 10 households) |
| Financial model negative IRR | Valid result | Display with warning "Project not viable without subsidy" |
| PDF generation timeout | Blocks report | Retry once, then offer Excel-only download |
| Batch: partial site failures | Partial results | Show succeeded sites + error list for failed sites |

### State Lifecycle Risks

- **Analysis state**: Saved to database after completion. If backend crashes mid-analysis, the request is stateless — user retries. No partial state persisted.
- **User uploads**: Stored temporarily during analysis, permanently if user saves project.
- **Report files**: Generated on-demand, cached for 24 hours. Regenerated if parameters change.

### API Surface Parity

The frontend is the only interface for V1. No public API planned initially. If an API is added later, all computation is already behind FastAPI endpoints — the frontend calls the same endpoints a public API would expose.

## Acceptance Criteria

### Functional Requirements

- [ ] User can enter GPS coordinates or click map to select a site in Mozambique
- [ ] System auto-detects settlement cluster and extracts all GIS attributes
- [ ] System generates demand estimates with MTF tier assignment when no user data uploaded
- [ ] User can override demand with uploaded CSV/Excel survey data
- [ ] System sizes solar PV + battery + inverter + distribution network
- [ ] Financial model calculates LCOE, IRR, NPV, payback, DSCR
- [ ] Tariff analysis shows cost-reflective tariff and affordability gap
- [ ] Subsidy gap quantified per connection and as % of CAPEX
- [ ] Sensitivity analysis covers 6 key parameters with tornado chart
- [ ] Grid arrival risk rated and displayed for each site
- [ ] PDF report downloadable with maps, charts, tables, and executive summary
- [ ] Excel workbook downloadable with live formulas for analyst modification
- [ ] Batch upload of 20+ sites via CSV with portfolio comparison view
- [ ] User accounts with save/load/share functionality

### Non-Functional Requirements

- [ ] Single site: GPS to results dashboard in < 2 minutes
- [ ] Single site: GPS to downloadable report in < 5 minutes
- [ ] Batch of 20 sites: complete analysis in < 10 minutes
- [ ] System-generated demand estimates within 30% of actuals for validated sites
- [ ] LCOE/IRR consistent with manually-prepared studies (< 15% deviation)
- [ ] PDF report quality suitable for investment committee presentation

### Quality Gates

- [ ] Unit tests for all engine functions (demand, sizing, financial, grid risk)
- [ ] Integration tests for end-to-end API pipeline with 5+ test sites
- [ ] Validation against 3+ sites with known prefeasibility data
- [ ] PDF report reviewed for formatting, chart clarity, and data accuracy
- [ ] Excel formulas verified to recalculate correctly when inputs changed

## Success Metrics

(see origin: `docs/brainstorms/2026-05-12-minigrid-prefeasibility-platform-requirements.md`)

1. **Speed**: GPS to report in < 15 minutes (user time including review)
2. **Accuracy**: Demand estimates within 30% of validated actuals
3. **Consistency**: LCOE/IRR within 15% of manually-prepared studies
4. **Scale**: 20+ sites batch-processed with ranked portfolio output
5. **Adoption**: DFI analysts can self-serve without technical support

## Dependencies & Prerequisites

1. **GIS data sourcing**: All raster and vector layers must be downloaded, harmonized, and validated before Phase 2 can begin. This is the critical-path dependency.
2. **Settlement cluster generation**: Run the GEP Clustering algorithm on Mozambique data. If pre-computed clusters are available from the GEP/World Bank, use those; otherwise generate from HRSL + VIIRS + GADM.
3. **Mozambique financial defaults**: Equipment costs, tariffs, and regulatory parameters must be researched and set. Sources: SEforAll CAPEX benchmark, AMDA 2024 report, ARENE tariff regulations.
4. **Map tile provider**: MapTiler account for satellite+labels base tiles (free tier may suffice for initial development).
5. **Hosting**: Vercel (frontend) + Railway/Render (FastAPI backend) + Neon (PostgreSQL+PostGIS) + object storage for rasters.

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| GIS data gaps for Mozambique | Medium | High | Identify gaps early in Phase 1; use multiple sources; flag missing data in outputs |
| Demand estimation accuracy | High | Medium | Conservative defaults; prominent override option; validate against known sites |
| Settlement cluster quality | Medium | High | Validate against satellite imagery and known villages; allow manual boundary adjustment |
| PDF report rendering quality | Medium | Medium | Use Puppeteer (real browser rendering); iterate on template design early |
| Performance at batch scale | Low | Medium | Pre-extract cluster attributes; parallelize batch processing; set user expectations |
| Mozambique regulatory changes | Low | Low | Country config is external; update config when regulations change |

## Alternative Approaches Considered

1. **HOMER integration**: Full HOMER-level simulation for each site. Rejected — too slow for screening tool, requires proprietary license, overkill for prefeasibility.
2. **Jupyter notebook interface**: Like the GEP Generator. Rejected — target users are DFI analysts without Python skills. Web UI is essential.
3. **Client-side computation**: All sizing/financial calculations in JavaScript. Rejected — Python ecosystem (rasterio, numpy, openpyxl) is far stronger for GIS processing and scientific computing.
4. **Monolithic Next.js**: All computation in Next.js API routes. Rejected — rasterio and GIS processing require Python; a Python backend is necessary.

## Future Considerations

- **Additional generation technologies**: Diesel hybrid, wind, small hydro — extend sizing engine with additional technology modules
- **Additional countries**: Add country config packages for Tanzania, Malawi, Kenya, etc.
- **API access**: Expose computation endpoints as a public API for programmatic access
- **Real demand data integration**: Partner with mini-grid operators to incorporate actual consumption data for model calibration
- **Machine learning demand estimation**: Train models on actual mini-grid consumption data to improve demand predictions
- **Integration with financing platforms**: Connect to DFI deal management systems

## Sources & References

### Origin

- **Origin document:** [docs/brainstorms/2026-05-12-minigrid-prefeasibility-platform-requirements.md](docs/brainstorms/2026-05-12-minigrid-prefeasibility-platform-requirements.md) — Key decisions carried forward: solar+battery only for V1, hybrid data approach (pre-loaded GIS + user override), auto-detect settlement clusters from population data, model grid arrival where ARENE regulations exist, both PDF + Excel outputs.

### Internal References

- GEP/OnSSET technical reference (in project memory): platform architecture, OnSSET model logic, clustering methodology, LCOE formulas, T&D network cost model, demand tier definitions
- Khavari et al. (2021) Scientific Data paper: clustering methodology, validation, data sources

### External References

- SEforAll Mini-grid CAPEX and OPEX Benchmark Study (August 2024)
- AMDA Benchmarking Africa's Minigrids Report 2024
- Global Solar Atlas — Mozambique: https://globalsolaratlas.info/download/mozambique
- energydata.info (ESMAP): Mozambique grid network data
- ARENE regulatory framework: Normative Resolutions 1-3/2022
- GRID3 Mozambique: settlement boundaries and population
- OnSSET T&D model: https://www.mdpi.com/1996-1073/12/7/1395
- GEP User Guide: https://gep-user-guide.readthedocs.io/en/latest/
- GEP OnSSET repo: https://github.com/global-electrification-platform/gep-onsset
- GEP Clustering repo: https://github.com/babakkhavari/Clustering
- GIS Extraction repo: https://github.com/babakkhavari/OnSSET_GIS_Extraction_notebook

### Mozambique Context

- EDM 30km electrification mandate for grid extension
- ARENE tariff regulation for off-grid areas (Normative Resolution No. 1/2022)
- ARENE interconnection regulation (Normative Resolution No. 2/2022)
- National electrification target: 68% grid + 30% off-grid by 2030
- Current national electrification rate: ~40%
- Grid residential electricity price: ~MZN 8.12/kWh (~$0.12/kWh)
- Mini-grid tariffs: typically $0.30-0.60/kWh (cost-reflective)
