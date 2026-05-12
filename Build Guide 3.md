# Build Guide 3 — AfCEN Minigrid PFS Platform

**Version**: 1.0.0
**Date**: May 2026
**Platform**: AfCEN Minigrid Pre-Feasibility Study Generation Platform
**Repository**: https://github.com/Denohatma/afcen-minigrid-pfs-platform
**Live Frontend**: https://frontend-pi-ten-66.vercel.app

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Backend — FastAPI REST API](#5-backend--fastapi-rest-api)
6. [Computational Pipeline — 7 Adapters](#6-computational-pipeline--7-adapters)
7. [Data Models](#7-data-models)
8. [PFS Document Generator](#8-pfs-document-generator)
9. [Frontend — Next.js Web Application](#9-frontend--nextjs-web-application)
10. [Authentication & Multi-Tenancy](#10-authentication--multi-tenancy)
11. [Reference Data Files](#11-reference-data-files)
12. [Site Data Format](#12-site-data-format)
13. [Deployment](#13-deployment)
14. [Local Development Setup](#14-local-development-setup)
15. [API Reference](#15-api-reference)
16. [User Workflow](#16-user-workflow)

---

## 1. Platform Overview

The AfCEN Minigrid PFS Platform is a web-based system for generating professional Pre-Feasibility Studies (PFS) for mini-grid solar-hybrid projects. It transforms site survey data into comprehensive technical and financial assessments through an automated computational pipeline.

### What It Does

A user enters site data (location, population, customer segments, anchor loads, financial assumptions) through a guided web wizard. The platform then runs 7 sequential computational adapters that produce:

- Demand assessment with 8,760-hour load profiles
- Solar resource analysis from PVGIS satellite data
- Grid arrival risk scoring across 4 ESMAP scenarios
- Optimal PV + battery + inverter sizing via hourly dispatch simulation
- Distribution network routing with bill of quantities
- Carbon credit revenue projections
- 25-year financial model with LCOE, IRR, NPV, and sensitivity analysis

These outputs feed into a 17-section Jinja2 template engine that renders a professional Pre-Feasibility Study document in both Markdown and DOCX formats, complete with embedded charts and location maps.

### Key Capabilities

- **Multi-tenant**: Organization-based isolation with Clerk authentication
- **Role-based access**: Admin, Analyst, and Viewer roles
- **Real-time monitoring**: Server-Sent Events stream pipeline progress to the browser
- **Run comparison**: Side-by-side metric deltas between pipeline runs
- **Site cloning**: Duplicate sites to test variant scenarios (different tariffs, financing structures)
- **Professional output**: Branded DOCX documents with navy/accent color scheme, KV info blocks, data tables, and 7 embedded chart types

---

## 2. Architecture

```
                    ┌──────────────────────────┐
                    │         Browser           │
                    │  (Next.js + Clerk SDK)    │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │    Vercel (Frontend)      │
                    │    Next.js 16 App         │
                    │    /api/proxy/* → BFF     │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Railway (Backend)       │
                    │   FastAPI + Uvicorn       │
                    │   Python 3.11            │
                    └──┬──────────┬────────────┘
                       │          │
          ┌────────────▼──┐  ┌───▼────────────┐
          │ Neon           │  │ Cloudflare R2   │
          │ PostgreSQL     │  │ Object Storage  │
          │                │  │                 │
          │ - organizations│  │ - PFS documents │
          │ - users        │  │   (DOCX, MD)    │
          │ - sites        │  │ - Charts (PNG)  │
          │ - pipeline_runs│  │                 │
          │ - adapter_results│ │                │
          │ - documents    │  │                 │
          └────────────────┘  └─────────────────┘
```

### Data Flow

1. **User** fills in site data through a 7-step wizard in the browser
2. **Frontend** sends site data to the backend via the BFF proxy (`/api/proxy/*`)
3. **Backend** stores the site in the database, then runs the computational pipeline
4. **Pipeline** executes 7 adapters in dependency order, streaming status via SSE
5. **Generator** takes adapter outputs and renders a 17-section PFS document
6. **Charts** are generated as PNG files (matplotlib) and embedded in the DOCX
7. **Documents** are stored in Cloudflare R2 (production) or local filesystem (dev)
8. **User** downloads the finished PFS document

---

## 3. Technology Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| FastAPI | >= 0.115 | REST API framework |
| Uvicorn | >= 0.32 | ASGI server |
| SQLAlchemy | >= 2.0 (async) | ORM with async support |
| aiosqlite | >= 0.20 | SQLite async driver (dev) |
| asyncpg | >= 0.30 | PostgreSQL async driver (prod) |
| Pydantic | >= 2.0 | Request/response validation |
| PyJWT | >= 2.9 | Clerk JWT verification |
| boto3 | >= 1.35 | Cloudflare R2 (S3-compatible) |
| Jinja2 | >= 3.1 | PFS template rendering |
| python-docx | >= 1.0 | Word document generation |
| matplotlib | >= 3.7 | Chart generation |
| staticmap | >= 0.5 | Location map tiles |
| numpy | >= 1.24 | Numerical operations |
| networkx | >= 3.0 | Distribution routing graphs |
| geopy | >= 2.3 | Geospatial utilities |
| shapely | >= 2.0 | Geometry operations |
| httpx | >= 0.28 | Async HTTP client |

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16.2.4 | React framework (App Router) |
| React | 19.2.4 | UI library |
| TypeScript | — | Type safety |
| Tailwind CSS | v4 | Utility-first styling |
| shadcn/ui | 4.6.0 | UI component library |
| @clerk/nextjs | 7.3.0 | Authentication |
| @tanstack/react-query | 5.100.8 | Server state management |
| react-hook-form | 7.75.0 | Form management |
| zod | 4.4.2 | Schema validation |
| react-leaflet | 5.0.0 | Interactive maps |

### Infrastructure

| Service | Purpose |
|---|---|
| Vercel | Frontend hosting + BFF proxy |
| Railway | Backend hosting (Docker) |
| Neon | Managed PostgreSQL |
| Cloudflare R2 | Document storage (S3-compatible) |
| Clerk | Authentication + organizations |
| PVGIS | Solar irradiance data API |

---

## 4. Project Structure

```
/Users/dennisnderitu/Desktop/Minigrids/
│
├── backend/                            # FastAPI backend application
│   ├── app/
│   │   ├── main.py                    # App startup, middleware, CORS, rate limiting
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── api/routes/
│   │   │   ├── sites.py               # Site CRUD endpoints
│   │   │   ├── runs.py                # Pipeline trigger + SSE streaming
│   │   │   └── documents.py           # Document generation + download
│   │   ├── services/
│   │   │   ├── pipeline_service.py    # Adapter orchestration
│   │   │   └── document_service.py    # PFS generation + R2 upload
│   │   ├── db/
│   │   │   ├── models.py             # 7 SQLAlchemy ORM tables
│   │   │   └── session.py            # Async DB session factory
│   │   ├── schemas/
│   │   │   ├── site.py               # Site request/response schemas
│   │   │   └── run.py                # Run + document schemas
│   │   └── dependencies/
│   │       └── auth.py               # Clerk JWT verification + role checks
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                           # Next.js web application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── layout.tsx            # Root layout + Clerk provider
│   │   │   ├── providers.tsx         # React Query client
│   │   │   ├── api/proxy/[...path]/  # BFF proxy to backend
│   │   │   └── (dashboard)/          # Protected route group
│   │   │       ├── sites/
│   │   │       │   ├── page.tsx      # Sites list table
│   │   │       │   ├── new/page.tsx  # Site creation wizard
│   │   │       │   └── [id]/
│   │   │       │       ├── page.tsx  # Site detail + runs + documents
│   │   │       │       └── edit/page.tsx  # Edit wizard
│   │   │       └── layout.tsx        # Dashboard navigation
│   │   ├── components/
│   │   │   ├── navbar.tsx            # Top navigation bar
│   │   │   ├── ui/                   # shadcn/ui primitives (11 files)
│   │   │   └── wizard/               # Multi-step form system
│   │   │       ├── wizard-shell.tsx       # Form orchestration
│   │   │       ├── step-identity.tsx      # Step 1: Name, location
│   │   │       ├── step-settlement.tsx    # Step 2: Population, terrain
│   │   │       ├── step-customers.tsx     # Step 3: Customer segments
│   │   │       ├── step-anchors.tsx       # Step 4: Anchor loads
│   │   │       ├── step-grid-es.tsx       # Step 5: Grid risk, E&S
│   │   │       ├── step-financial.tsx     # Step 6: Tariffs, financing
│   │   │       ├── step-review.tsx        # Step 7: Summary
│   │   │       ├── pipeline-progress.tsx  # Real-time SSE monitor
│   │   │       ├── run-compare.tsx        # Side-by-side diff
│   │   │       └── site-boundary-map.tsx  # Leaflet map
│   │   └── lib/
│   │       ├── api.ts                # Fetch-based API client
│   │       ├── types.ts              # TypeScript interfaces
│   │       ├── schemas.ts            # Zod validation schemas
│   │       ├── utils.ts              # Utilities
│   │       └── hooks/use-role.ts     # Auth role hook
│   ├── package.json
│   ├── vercel.json
│   └── .env.example
│
├── src/                                # Computational pipeline
│   ├── adapters/                      # 7 computational adapters
│   │   ├── demand_assessment.py
│   │   ├── solar_resource.py
│   │   ├── grid_arrival.py
│   │   ├── hybrid_sizing.py
│   │   ├── distribution_routing.py
│   │   ├── carbon_assessment.py
│   │   └── financial_model.py
│   ├── models/                        # Typed dataclass schemas
│   │   ├── site.py                   # SiteData + nested types
│   │   ├── demand.py                 # DemandAssessmentOutput
│   │   ├── solar.py                  # SolarResourceOutput
│   │   ├── sizing.py                 # HybridSizingOutput
│   │   ├── distribution.py           # DistributionDesignOutput
│   │   ├── carbon.py                 # CarbonAssessmentOutput
│   │   ├── financial.py              # FinancialModelOutput
│   │   └── grid_arrival.py           # GridArrivalOutput
│   ├── generator/                     # PFS document generation
│   │   ├── pfs_generator.py          # Main orchestrator
│   │   ├── chart_generator.py        # 7 matplotlib chart types
│   │   ├── docx_writer.py            # Professional DOCX styling
│   │   └── templates/                # 17 Jinja2 markdown templates
│   │       ├── 01_executive_summary.md.j2
│   │       ├── 02_introduction.md.j2
│   │       ├── ... (15 more sections)
│   │       └── 16_annexes.md.j2
│   ├── data/                          # Reference data
│   │   ├── load_benchmarks.json
│   │   ├── financial_defaults.json
│   │   ├── conductor_library.json
│   │   └── load_shapes/              # 6 hourly profiles
│   ├── orchestrator.py               # Pipeline execution engine
│   └── registry.py                   # Adapter registry + base class
│
├── sites/                              # Sample site JSON files
│   └── megaza.json                    # Complete example (Mozambique)
├── run.py                              # Legacy CLI entry point
├── requirements.txt                    # Root Python dependencies
├── railway.toml                        # Railway deployment config
└── .gitignore
```

---

## 5. Backend — FastAPI REST API

### 5.1 Application Entry Point

**File**: `backend/app/main.py`

The FastAPI application initializes with:

- **Lifespan handler**: Creates database tables on startup and cleans stale pipeline runs (>10 minutes old)
- **CORS middleware**: Configurable origins from `CORS_ORIGINS` environment variable
- **Rate limiting**: In-memory store limiting 10 pipeline runs per hour per organization
- **Health endpoint**: `GET /health` returns status, version, and environment
- **Three routers**: sites, runs, documents (all under `/api/v1/`)

### 5.2 Configuration

**File**: `backend/app/config.py`

Pydantic BaseSettings class that reads from environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./minigrid.db` | Database connection string |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `CLERK_SECRET_KEY` | — | Clerk JWT signing secret |
| `CLERK_JWKS_URL` | `https://api.clerk.com/v1/jwks` | Clerk public key endpoint |
| `R2_ENDPOINT_URL` | — | Cloudflare R2 endpoint |
| `R2_ACCESS_KEY_ID` | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | — | R2 secret key |
| `R2_BUCKET_NAME` | `minigrid-documents` | R2 bucket name |
| `CORS_ORIGINS` | — | Allowed frontend origins (JSON array) |

### 5.3 Database Schema

**File**: `backend/app/db/models.py`

Seven SQLAlchemy ORM models with async support:

```
Organization (1) ──── (*) OrgMember (*) ──── (1) User
      │
      └──── (*) Site (1) ──── (*) PipelineRun (1) ──── (*) AdapterResult
                                      │
                                      └──── (*) Document
```

| Model | Key Fields | Purpose |
|---|---|---|
| **Organization** | id, name, clerk_org_id | Multi-tenant organization |
| **User** | id, clerk_user_id, email, name | Platform user |
| **OrgMember** | org_id, user_id, role | Organization membership + role |
| **Site** | org_id, site_name, site_data (JSON), status | Mini-grid site with full input data |
| **PipelineRun** | site_id, status, adapter_timings, adapter_errors, summary_metrics | Pipeline execution record |
| **AdapterResult** | run_id, adapter_name, status, output (JSON), duration_seconds | Individual adapter output |
| **Document** | run_id, format, storage_key, filename, size_bytes | Generated PFS document reference |

**Site status values**: `draft`, `complete`, `archived`
**Run status values**: `pending`, `running`, `completed`, `failed`

### 5.4 Services

#### Pipeline Service (`backend/app/services/pipeline_service.py`)

Orchestrates the computational pipeline:

1. Reconstructs `SiteData` from the JSON dict stored in the database
2. Instantiates the `Orchestrator` with all 7 adapters registered
3. Runs the pipeline via `asyncio.to_thread()` to avoid blocking the event loop
4. Stores individual `AdapterResult` records for each adapter
5. Updates the `PipelineRun` with timings, errors, and summary metrics

#### Document Service (`backend/app/services/document_service.py`)

Generates PFS documents from completed pipeline runs:

1. Reconstructs `SiteData` and adapter outputs from stored JSON
2. Creates a `PipelineContext` with all adapter outputs
3. Calls `PFSGenerator.generate()` to produce Markdown + DOCX
4. Uploads to Cloudflare R2 (production) or saves to local `document_storage/` (development)
5. Creates `Document` records in the database
6. Supports presigned URL generation for downloads

---

## 6. Computational Pipeline — 7 Adapters

### 6.1 Execution Order

The adapters execute in dependency order, resolved via topological sort:

```
demand_assessment ─────┬──→ hybrid_sizing ──→ carbon_assessment ──┐
                       │         ↑                                │
solar_resource ────────┘         │                                ▼
                                 │                         financial_model
grid_arrival (independent)       │                                ↑
                                 │                                │
demand_assessment ──→ distribution_routing ────────────────────────┘
```

**Execution order**: demand_assessment, solar_resource, grid_arrival, hybrid_sizing, distribution_routing, carbon_assessment, financial_model

### 6.2 Adapter Details

#### Adapter 1: Demand Assessment

**File**: `src/adapters/demand_assessment.py`
**Dependencies**: None

Takes customer segments and anchor loads, produces:
- **Peak load** (kW) with diversity factors applied (0.3-1.0 based on customer count)
- **Annual demand** (kWh) from daily shape profiles scaled to 365 days
- **8,760-hour load profile** by repeating 24-hour shapes for each customer type
- **Growth scenarios** (conservative, base, high)

Uses benchmark data from `src/data/load_benchmarks.json` for per-unit peak loads and `src/data/load_shapes/*.json` for 24-hour normalized demand curves.

#### Adapter 2: Solar Resource

**File**: `src/adapters/solar_resource.py`
**Dependencies**: None

Queries the PVGIS 5.3 API with site coordinates to obtain:
- **Monthly GHI** (Global Horizontal Irradiance, kWh/m2)
- **Monthly DNI** (Direct Normal Irradiance, kWh/m2)
- **Monthly temperature** (degrees C)
- **Annual GHI** and **specific yield** (kWh/kWp)
- **8,760 hourly solar factors** (bell-curve modulated by monthly profiles)
- **Performance ratio** (0.77 default, accounting for inverter, wiring, soiling losses)

Falls back to hardcoded regional values if the PVGIS API is unreachable (30-second timeout).

#### Adapter 3: Grid Arrival

**File**: `src/adapters/grid_arrival.py`
**Dependencies**: None

Scores 4 ESMAP grid arrival scenarios based on evidence flags:
- **No arrival**: Grid never reaches the site
- **Overlap risk**: Grid arrives during asset lifetime
- **Compensation exit**: Grid arrives, operator compensated
- **Early replacement**: Grid replaces mini-grid prematurely

Each scenario scored on 5 dimensions (timeline certainty, financial viability, regulatory alignment, implementation complexity, stakeholder acceptability) weighted to produce a recommendation.

#### Adapter 4: Hybrid Sizing

**File**: `src/adapters/hybrid_sizing.py`
**Dependencies**: demand_assessment, solar_resource

Determines optimal PV + battery + inverter configuration:
1. Tests PV candidates at 0.8x to 2.0x peak load
2. Sizes battery for 3.5 hours evening autonomy at 80% depth of discharge
3. Runs 8,760-hour dispatch simulation for each candidate
4. Selects smallest PV where unmet demand is 5% or less
5. Sizes inverter as max(peak load, PV capacity x 0.83)

Produces hourly dispatch data (solar, battery charge/discharge, unmet, curtailed, SOC).

#### Adapter 5: Distribution Routing

**File**: `src/adapters/distribution_routing.py`
**Dependencies**: demand_assessment

Designs the low-voltage distribution network:
- **Routing**: OpenStreetMap Steiner tree (if osmnx available), minimum spanning tree (networkx), or radial estimation
- **Terrain multiplier**: flat 1.10, rolling 1.25, hilly 1.40, mountainous 1.60
- **Bill of quantities**: Conductors, poles, transformers, protection equipment, service drops
- **Cost calculation**: Per-unit costs from `src/data/conductor_library.json`
- **Quality checks**: Voltage drop target ≤3%, technical losses target ≤7%

#### Adapter 6: Carbon Assessment

**File**: `src/adapters/carbon_assessment.py`
**Dependencies**: hybrid_sizing

Calculates carbon credit potential:
- **Baseline**: Diesel genset alternative (0.35 efficiency, 2.80 kgCO2e/litre)
- **Methodology**: Gold Standard TPDDTEC or Verra VM0103
- **Crediting period**: 7 years, issuance starting year 3
- **Revenue scenarios**: Zero, conservative ($5/tCO2e), market ($12/tCO2e), premium ($20/tCO2e)
- **NPV**: Discounted carbon revenue over crediting period

#### Adapter 7: Financial Model

**File**: `src/adapters/financial_model.py`
**Dependencies**: hybrid_sizing, distribution_routing, carbon_assessment, demand_assessment

Comprehensive 25-year financial analysis:

**CAPEX Breakdown**:
- PV modules ($250/kWp), inverters ($150/kWac), mounting ($80/kWp), BOS ($120/kWp)
- Battery storage ($200/kWh), distribution (from routing adapter), civil works ($15,000 fixed)
- Owner's costs (5%), EPC margin (8%), contingency (10%)

**OPEX** (annual):
- Generation O&M (2% of generation CAPEX), distribution O&M (2% of distribution CAPEX)
- Site security ($5,000/yr), administration ($2,000/yr)

**Financing**: Configurable grant/debt/equity split (e.g., 40/35/25)

**25-Year Cashflow**: Revenue (tariff x energy sold, escalated by inflation), carbon revenue, OPEX, debt service, battery replacement (year 10), inverter replacement (year 15)

**Key Metrics**: LCOE, project IRR, equity IRR, NPV at 10%, DSCR, simple payback, subsidy required

**Sensitivity Analysis**: Tests PV cost, tariff, and battery cost variations on IRR impact

### 6.3 Orchestrator

**File**: `src/orchestrator.py`

The `Orchestrator` class manages pipeline execution:

1. Accepts an `AdapterRegistry` with all 7 adapters registered
2. Resolves execution order via topological sort (detects circular dependencies)
3. Executes each adapter sequentially with:
   - Availability check
   - Dependency verification (skip if upstream errored)
   - Input validation
   - Timed execution with error capture
4. Returns a `PipelineContext` containing all outputs, errors, and timings

### 6.4 Registry

**File**: `src/registry.py`

The `AdapterRegistry` maintains the adapter catalog and resolves dependencies. `BaseAdapter` defines the interface:

- `name`: Unique identifier
- `kind`: TOOL (computational adapter)
- `dependencies`: List of adapter names that must run first
- `is_available()`: Whether the adapter can run
- `validate_inputs()`: Check required data is present
- `run(site_data, context)`: Execute and return typed output

---

## 7. Data Models

**Location**: `src/models/`

All models are Python dataclasses providing typed schemas for adapter inputs and outputs.

### 7.1 SiteData (`src/models/site.py`)

The master input model, containing all data needed to run the pipeline:

| Section | Fields |
|---|---|
| **Identity** | site_name, district, province, country, coordinates (lat, lon), developer |
| **Settlement** | population, mapped_structures, settlement_radius_m |
| **Customers** | list[CustomerSegment] — category, sub_type, count, tier, estimated_load_kw, operating_hours |
| **Anchor Loads** | list[AnchorLoad] — load_type, name, count, estimated_load_kw, operating_hours, load_shape |
| **Grid** | grid_status, grid_arrival_evidence (8 evidence flags) |
| **Financial** | tariff_scenarios (low/base/high), discount_rate, inflation_rate, fx_rate, financing_structure, debt terms |
| **Environmental** | protected_area_overlap, flood_risk, biodiversity_risk, ifc_category |
| **Context** | terrain, economic_activities[], social_services[], access_description |
| **Calibration** | existing_pfs (optional — prior PFS metrics for comparison) |

### 7.2 Adapter Output Models

| Model | File | Key Fields |
|---|---|---|
| **DemandAssessmentOutput** | `demand.py` | peak_load_kw, annual_demand_kwh, hourly_profile_8760, customer_details, growth_scenarios |
| **SolarResourceOutput** | `solar.py` | monthly_ghi/dni/temp (12 each), annual_ghi, specific_yield, hourly_solar_factors (8760) |
| **GridArrivalOutput** | `grid_arrival.py` | scenario_scores (4 scenarios x 5 dimensions + weighted score + recommendation) |
| **HybridSizingOutput** | `sizing.py` | pv_capacity_kwp, battery_capacity_kwh, inverter_capacity_kwac, hourly_dispatch (8760), monthly_generation |
| **DistributionDesignOutput** | `distribution.py` | total_line_length_m, pole_count, bill_of_quantities, total_network_cost_usd, network_geojson |
| **CarbonAssessmentOutput** | `carbon.py` | annual_emission_reductions_tco2e, revenue_by_scenario, npv_by_scenario, methodology |
| **FinancialModelOutput** | `financial.py` | capex_breakdown, cashflow_25yr, lcoe, project_irr, equity_irr, npv, sensitivity_results |

---

## 8. PFS Document Generator

### 8.1 Generator Orchestrator

**File**: `src/generator/pfs_generator.py`

The `PFSGenerator` class coordinates document production:

1. Sets up a Jinja2 environment with custom filters (`|usd`, `|pct`, `|num`)
2. Calls `chart_generator.generate_all_charts()` to produce 7 PNG chart files
3. Builds a template context from all adapter outputs plus computed fields (recommendation logic, warnings)
4. Renders all 17 Jinja2 templates in order, joining sections with page breaks
5. Writes the combined Markdown file
6. Calls `docx_writer.write_docx()` to produce the styled Word document

**Recommendation Logic** (computed in `_build_context()`):
- **Go**: IRR >= 8% and subsidy <= 50% of CAPEX
- **Conditional Go**: IRR >= 5% (or IRR available but data gaps exist)
- **Redesign**: IRR < 5% but demand data exists
- **No-Go**: IRR < 5% and no demand data
- **Insufficient Data**: No financial model output

### 8.2 Template System

**Location**: `src/generator/templates/`

17 Jinja2 templates rendering Markdown with embedded tables:

| # | Template | Content |
|---|---|---|
| 01 | executive_summary | Headline metrics, recommendation, PUE summary |
| 02 | introduction | Background, scope, methodology, PUE objective |
| 03 | site_overview | Location, population, terrain, access |
| 04 | demand_assessment | Customer segments, peak/annual demand, load profile, growth |
| 04b | value_chain_pue | 19-activity PUE database, auto-detected value chains, business cases |
| 05 | solar_resource | Monthly GHI/DNI, temperature, specific yield, data source |
| 06 | load_demand_balance | Hourly dispatch visualization |
| 07 | generation_design | PV, battery, inverter sizing, autonomy, monthly generation |
| 08 | distribution_design | Network length, poles, voltage drop, losses, BoQ |
| 09 | environmental_social | E&S risks, IFC category, PUE environmental considerations |
| 10 | financial_model | CAPEX/OPEX, financing, tariff scenarios, key metrics |
| 11 | carbon_assessment | Emission reductions, carbon revenue, methodology |
| 12 | regulatory_grid_arrival | Grid risk scenarios, scoring |
| 13 | risk_register | Operational, market, regulatory risks + mitigation |
| 14 | implementation_timeline | Phased schedule, PUE development milestones |
| 15 | recommendation | Go/No-Go decision, PUE recommendations, next steps |
| 16 | annexes | Key assumptions, glossary, reference data |

**Custom Jinja2 Filters**:
- `{{ value | usd }}` — Format as USD currency ($1,234,567)
- `{{ value | pct }}` — Format as percentage (12.5%)
- `{{ value | num }}` — Format with thousand separators (1,234,567)

### 8.3 Chart Generator

**File**: `src/generator/chart_generator.py`

Generates 7 PNG chart images using matplotlib with a consistent brand palette:

| Chart | Type | Data Source |
|---|---|---|
| **chart_load_profile.png** | 24-hour line plot with fill | demand_assessment (hourly_profile_8760 averaged) |
| **chart_monthly_gen_demand.png** | Grouped bar chart (12 months) | demand + hybrid_sizing (monthly generation vs demand) |
| **chart_dispatch.png** | Stacked area + twin-axis SOC line | hybrid_sizing (sample mid-year day from hourly_dispatch) |
| **chart_solar_resource.png** | Dual-axis bars (GHI/DNI) + temp line | solar_resource (monthly values) |
| **chart_capex.png** | Horizontal bar sorted by value | financial_model (capex_breakdown) |
| **chart_cashflow.png** | Bar chart (green/red) + cumulative line | financial_model (cashflow_25yr) |
| **map_location.png** | Static map tile with marker | site_data (coordinates via staticmap/OSM) |

**Brand Color Palette**:
- Navy: `#1B3A5C` — Headers, borders
- Accent: `#2E75B6` — Links, highlights
- Solar Gold: `#F4A300` — Solar data
- Battery Green: `#27AE60` — Battery/positive values
- Demand Red: `#C0392B` — Demand/negative values
- Curtailment Gray: `#BFBFBF` — Curtailed energy

The map generator uses staticmap to fetch OpenStreetMap tiles with a red circle marker. A matplotlib fallback plots coordinates with labeled axes if the map server is unreachable.

### 8.4 DOCX Writer

**File**: `src/generator/docx_writer.py`

Converts the rendered Markdown into a professionally styled Word document:

**Smart Table Detection**: The writer uses a KV detection heuristic to distinguish between two table types:
- **Key-Value tables** (2-column, ≤15 rows, header keywords like "Parameter", "Value", "Metric"): Rendered as borderless info blocks with bold gray labels and alternating row shading
- **Data tables** (multi-column or many rows): Rendered with navy header rows, white text, and alternating gray/white body rows

**Professional Styling**:
- Cover page with branded horizontal rules (navy + accent)
- Calibri font throughout (titles 28pt, headings 16pt/13pt, body 10.5pt)
- Page breaks before each major section (`##` headings)
- Headers with site name, footers with page numbers
- Status symbol colorization (green checkmarks, red crosses, amber triangles)
- Bold markdown markers stripped from headings
- Charts embedded at 5.8-inch width with italic captions

**Chart Embedding**: The `_CHART_PLACEMENTS` dictionary maps chart keys to section heading fragments. Charts are inserted before the second subsection heading of their matching section, providing natural placement after introductory text.

**Centralized Imports**: All python-docx imports are loaded once via a `_load_docx()` function that sets module-level globals, avoiding repeated import overhead.

---

## 9. Frontend — Next.js Web Application

### 9.1 Application Structure

The frontend uses Next.js 16 App Router with React 19:

- **Root layout** (`src/app/layout.tsx`): Clerk provider, global styles
- **Providers** (`src/app/providers.tsx`): React Query client
- **BFF Proxy** (`src/app/api/proxy/[...path]/`): Forwards requests to the backend with auth headers
- **Dashboard group** (`src/app/(dashboard)/`): Protected pages behind Clerk auth

### 9.2 Pages

#### Landing Page (`/`)
Logo, platform title, description, "Get Started" button navigating to `/sites`.

#### Sites List (`/sites`)
Table view of all organization sites with columns: Site Name, District, Country, Status (badge), Customers, Created, Actions. Includes skeleton loading states and empty state with "New Site" CTA.

#### Site Detail (`/sites/[id]`)
Comprehensive view with:
- Site metadata (name, location, status)
- Summary metrics from latest completed run (PV capacity, battery, CAPEX, LCOE, IRR)
- Runs table with status, timing, and actions
- Documents table with download links
- "Run Pipeline" button with SSE progress monitoring
- "Compare Runs" toggle for side-by-side metric deltas

#### Site Creation (`/sites/new`) and Edit (`/sites/[id]/edit`)
7-step wizard form with auto-save between steps.

### 9.3 Wizard System

**File**: `src/components/wizard/wizard-shell.tsx`

The WizardShell orchestrates a 7-step form using React Hook Form with Zod validation:

| Step | Component | Fields |
|---|---|---|
| 1. Identity | `step-identity.tsx` | site_name, district, province, country, coordinates, developer |
| 2. Settlement | `step-settlement.tsx` | population, mapped_structures, settlement_radius_m, terrain, economic_activities, social_services, access |
| 3. Customers | `step-customers.tsx` | Dynamic array of customer segments (category, sub_type, count, tier, load, hours) |
| 4. Anchors | `step-anchors.tsx` | Dynamic array of anchor loads (load_type, name, count, load, hours, shape) |
| 5. Grid & E&S | `step-grid-es.tsx` | grid_status, grid_arrival_evidence flags, flood/biodiversity/IFC risks |
| 6. Financial | `step-financial.tsx` | tariff_scenarios, discount_rate, inflation, fx_rate, financing_structure, debt terms |
| 7. Review | `step-review.tsx` | Read-only summary with "Edit" buttons to jump to any step |

### 9.4 Real-Time Pipeline Monitoring

**File**: `src/components/wizard/pipeline-progress.tsx`

The PipelineProgress component connects to the SSE endpoint (`/api/v1/sites/{id}/runs/stream`) and displays:
- Per-adapter status badges (pending → running → completed/failed)
- Execution timing for each adapter
- Progress bar
- Error messages for failed adapters
- Automatic status badge updates

### 9.5 Run Comparison

**File**: `src/components/wizard/run-compare.tsx`

Accepts two `RunDetailResponse` objects and renders side-by-side metric comparison with colored deltas (green for improvement, red for degradation).

### 9.6 API Client

**File**: `src/lib/api.ts`

Fetch-based client proxying through `/api/proxy`:

```typescript
api.sites.list()                          // GET /sites
api.sites.get(id)                         // GET /sites/{id}
api.sites.create(siteData)                // POST /sites
api.sites.update(id, siteData)            // PUT /sites/{id}
api.sites.delete(id)                      // DELETE /sites/{id}
api.sites.clone(id)                       // POST /sites/{id}/clone

api.runs.list(siteId)                     // GET /sites/{id}/runs
api.runs.get(siteId, runId)               // GET /sites/{id}/runs/{runId}
api.runs.trigger(siteId)                  // POST /sites/{id}/runs

api.documents.generate(siteId, runId)     // POST /sites/{id}/runs/{runId}/documents
api.documents.list(siteId, runId)         // GET /sites/{id}/runs/{runId}/documents
api.documents.downloadUrl(siteId, runId, docId)  // Returns download URL
```

### 9.7 Validation

**File**: `src/lib/schemas.ts`

Zod schemas mirror the backend Pydantic schemas, providing client-side validation for:
- Customer segment fields
- Anchor load fields
- Site data master schema with conditional validation
- Per-step validation subsets for the wizard

---

## 10. Authentication & Multi-Tenancy

### 10.1 Clerk Integration

**Authentication Flow**:
1. User visits the platform and is redirected to Clerk sign-in
2. Clerk issues a JWT containing: `sub` (user ID), `org_id`, `org_role`, `email`, `name`
3. Frontend stores the JWT via Clerk SDK (secure HttpOnly cookie)
4. Every API request includes `Authorization: Bearer {jwt}`
5. Backend verifies the JWT against Clerk's JWKS (RS256 signature)
6. Backend auto-creates User, Organization, and OrgMember records on first login

**Development Mode**: When no Clerk token is present and `ENVIRONMENT=development`, the backend creates a default `dev_user`/`dev_org` with admin role. No Clerk keys are required for local development.

### 10.2 Organization Isolation

All data queries are filtered by the authenticated user's organization:
- Sites are scoped to `Site.org_id == auth.org_id`
- Runs inherit org context from their parent site
- Documents are stored in org-namespaced paths: `orgs/{org_id}/sites/{site_id}/runs/{run_id}/`

### 10.3 Roles

| Role | Create/Edit Sites | Run Pipeline | Download Docs | Manage Org |
|---|---|---|---|---|
| **Admin** | Yes | Yes | Yes | Yes |
| **Analyst** | Yes | Yes | Yes | No |
| **Viewer** | No | No | Yes | No |

Role enforcement uses the `require_role()` dependency in FastAPI routes.

---

## 11. Reference Data Files

### 11.1 Load Benchmarks (`src/data/load_benchmarks.json`)

Contains per-sector peak loads, annual consumption estimates, and diversity factors:

- **Diversity factors**: From 1.0 (single anchor) down to 0.3 (200+ customers)
- **Anchors**: hospital_rural (15 kW), primary_school (5 kW), grain_mill (3 kW), etc.
- **Customers**: residential_basic (0.2 kW), residential_improved (0.5 kW), commercial (1.5 kW), productive_use (3.0 kW)

### 11.2 Load Shapes (`src/data/load_shapes/`)

Six 24-hour normalized demand profiles (each sums to 24):

| Profile | Pattern |
|---|---|
| `residential.json` | Evening peak 18:00-22:00 |
| `commercial.json` | Daytime peak 09:00-17:00 |
| `commercial_evening.json` | Evening peak 18:00-21:00 |
| `institutional.json` | Daytime 08:00-16:00 + light evening |
| `institutional_24hr.json` | Flat 24-hour (hospitals) |
| `productive_use.json` | Daytime peak 06:00-18:00 |

### 11.3 Financial Defaults (`src/data/financial_defaults.json`)

Unit costs for CAPEX, OPEX, and technical parameters:

- **CAPEX**: PV modules ($250/kWp), inverters ($150/kWac), battery ($200/kWh), mounting ($80/kWp), BOS ($120/kWp), civil works ($15,000 fixed)
- **Margins**: Owner's costs (5%), EPC margin (8%), contingency (10%)
- **OPEX**: Generation O&M (2%/yr of CAPEX), distribution O&M (2%/yr), security ($5,000/yr), admin ($2,000/yr)
- **Technical**: Genset efficiency (0.35), diesel energy density (9.8 kWh/litre)

### 11.4 Conductor Library (`src/data/conductor_library.json`)

Distribution network component specifications and costs:
- Conductor types (4mm, 6mm, etc.) with cost per meter and voltage drop characteristics
- Pole costs ($200 each, 40m average span)
- Transformer costs by capacity (10kVA, 25kVA, etc.)
- Protection equipment costs (MCBs, RCDs)

---

## 12. Site Data Format

### 12.1 Complete Example

The `sites/megaza.json` file provides a complete real-world example — the Megaza 60 kWp Solar Hybrid Mini-Grid in Morrumbala District, Zambezia Province, Mozambique.

**Key characteristics**:
- **537 customers**: 83 improved residential + 435 basic residential + 19 commercial
- **7 anchor loads**: hospital, 2 schools, administration, fish chilling, grain mill, rice/cotton processing
- **Grid risk**: Grid extension planned but no confirmed timeline or funding
- **Existing PFS**: Calibrated to real project (60 kWp, 150 kWh battery, $230k CAPEX)
- **Financing**: 40% grant, 35% debt, 25% equity
- **Tariffs**: $0.30 (low), $0.40 (base), $0.50 (high) per kWh

### 12.2 Required Fields

At minimum, a site needs:

```json
{
  "site_name": "string",
  "district": "string",
  "province": "string",
  "country": "string",
  "coordinates": [latitude, longitude],
  "population": number,
  "mapped_structures": number,
  "settlement_radius_m": number,
  "customers": [{ "category": "...", "sub_type": "...", "count": N, "tier": "..." }],
  "tariff_scenarios": { "low": 0.30, "base": 0.40, "high": 0.50 },
  "discount_rate": 0.10,
  "financing_structure": { "grant_pct": 0.40, "debt_pct": 0.35, "equity_pct": 0.25 }
}
```

---

## 13. Deployment

### 13.1 Infrastructure Overview

| Component | Service | Configuration |
|---|---|---|
| Frontend | Vercel | Root: `frontend/`, Next.js framework auto-detected |
| Backend | Railway | Docker build from `backend/Dockerfile` |
| Database | Neon | Managed PostgreSQL (`postgresql+asyncpg://...`) |
| Storage | Cloudflare R2 | S3-compatible object storage |
| Auth | Clerk | JWT + organizations |

### 13.2 Backend Deployment (Railway)

**Dockerfile** (`backend/Dockerfile`):
- Base: `python:3.11-slim`
- Installs `gcc`, `libpq-dev` for PostgreSQL
- Copies `backend/requirements.txt` + entire `src/` directory
- Sets `PYTHONPATH=/app`
- Entry: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

**Railway Configuration** (`railway.toml`):
```toml
[build]
dockerfilePath = "backend/Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

**Required Environment Variables**:

| Variable | Source |
|---|---|
| `DATABASE_URL` | Neon connection string |
| `ENVIRONMENT` | `production` |
| `CLERK_SECRET_KEY` | Clerk dashboard |
| `R2_ENDPOINT_URL` | Cloudflare R2 settings |
| `R2_ACCESS_KEY_ID` | R2 API token |
| `R2_SECRET_ACCESS_KEY` | R2 API token |
| `R2_BUCKET_NAME` | `minigrid-documents` |
| `CORS_ORIGINS` | `["https://your-frontend.vercel.app"]` |

### 13.3 Frontend Deployment (Vercel)

**Configuration** (`frontend/vercel.json`):
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "installCommand": "npm install"
}
```

**Required Environment Variables**:

| Variable | Source |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk dashboard |
| `CLERK_SECRET_KEY` | Clerk dashboard |
| `BACKEND_URL` | Railway deployment URL |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | `/sign-up` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL` | `/sites` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL` | `/sites` |

### 13.4 Database Setup (Neon)

1. Create a Neon project
2. Copy the connection string: `postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/minigrid?sslmode=require`
3. Tables are auto-created on first backend startup via SQLAlchemy `create_all()`

### 13.5 Storage Setup (Cloudflare R2)

1. Create an R2 bucket named `minigrid-documents`
2. Create an API token with read/write access
3. Note the endpoint URL, access key, and secret key
4. Documents are stored at: `orgs/{org_id}/sites/{site_id}/runs/{run_id}/{filename}`

---

## 14. Local Development Setup

### 14.1 Prerequisites

- Python 3.11+
- Node.js 20+
- A Clerk account (optional — dev mode works without it)

### 14.2 Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

The backend auto-creates a dev user and org when no Clerk token is present. SQLite is used by default for local development.

### 14.3 Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. The BFF proxy at `/api/proxy/*` forwards requests to `http://127.0.0.1:8000`.

### 14.4 Running the CLI Pipeline (Legacy)

The original CLI entry point still works for testing without the web UI:

```bash
cd /Users/dennisnderitu/Desktop/Minigrids
python3 run.py sites/megaza.json --output-dir output/
```

This runs all 7 adapters and generates the PFS document in the specified output directory.

---

## 15. API Reference

### 15.1 Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check |
| **Sites** | | | |
| `POST` | `/api/v1/sites` | admin, analyst | Create site |
| `GET` | `/api/v1/sites` | any | List org sites |
| `GET` | `/api/v1/sites/{id}` | any | Get site detail |
| `PUT` | `/api/v1/sites/{id}` | admin, analyst | Update site |
| `DELETE` | `/api/v1/sites/{id}` | admin, analyst | Delete site |
| `POST` | `/api/v1/sites/{id}/clone` | admin, analyst | Clone site |
| **Runs** | | | |
| `POST` | `/api/v1/sites/{id}/runs` | admin, analyst | Trigger pipeline (blocking) |
| `POST` | `/api/v1/sites/{id}/runs/stream` | admin, analyst | Trigger pipeline (SSE) |
| `GET` | `/api/v1/sites/{id}/runs` | any | List runs |
| `GET` | `/api/v1/sites/{id}/runs/{rid}` | any | Get run detail + adapter results |
| **Documents** | | | |
| `POST` | `/api/v1/sites/{id}/runs/{rid}/documents` | any | Generate PFS documents |
| `GET` | `/api/v1/sites/{id}/runs/{rid}/documents` | any | List documents |
| `GET` | `/api/v1/sites/{id}/runs/{rid}/documents/{did}/download` | any | Download document |

### 15.2 Rate Limiting

Pipeline runs are limited to 10 per hour per organization (in-memory counter in `main.py`).

### 15.3 Interactive API Docs

With the backend running: http://localhost:8000/docs (Swagger UI)

---

## 16. User Workflow

### Step-by-Step Usage

1. **Sign up** at the platform URL and create or join an organization
2. **Create a site** using the 7-step wizard:
   - Step 1: Enter site name, location coordinates, developer
   - Step 2: Enter population, terrain, economic activities
   - Step 3: Add customer segments (residential, commercial, institutional, productive use)
   - Step 4: Add anchor loads (hospital, school, grain mill, etc.)
   - Step 5: Set grid arrival evidence and environmental/social risks
   - Step 6: Configure tariff scenarios, financing structure, debt terms
   - Step 7: Review all data and submit
3. **Run the pipeline** — click "Run Pipeline" and watch all 7 adapters execute in real-time via the SSE progress monitor
4. **Generate PFS documents** — click "Generate Documents" on a completed run
5. **Download** the Markdown or DOCX pre-feasibility study
6. **Compare runs** — select two completed runs to see how changes in site data affect metrics
7. **Clone sites** — duplicate a site to test alternative scenarios (different tariffs, financing splits, customer counts)

### What the PFS Contains

The generated document includes 17 sections covering:
- Executive summary with Go/No-Go recommendation
- Site overview with location map
- Demand assessment with 24-hour load profile chart
- Productive Use of Energy (PUE) value chain analysis
- Solar resource assessment with monthly GHI/DNI chart
- Load-demand balance analysis
- Generation system design with dispatch simulation chart
- Distribution network design with bill of quantities
- Environmental and social impact assessment
- Financial model with CAPEX breakdown chart and 25-year cashflow chart
- Carbon credit assessment
- Regulatory and grid arrival risk analysis
- Risk register with mitigation strategies
- Implementation timeline with PUE development phases
- Final recommendation with next steps
- Technical annexes

---

*Build Guide 3 — AfCEN Minigrid PFS Platform*
*Generated May 2026*
