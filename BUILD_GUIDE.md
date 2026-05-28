# Moz — Mini-Grid Prefeasibility Platform: Build & Integration Guide

**Version:** 1.0  
**Last Updated:** 2026-05-28  
**Repository:** https://github.com/Denohatma/moz-minigrid  

---

## 1. Platform Overview

Moz is a full-stack web platform that generates investment-grade prefeasibility studies for solar+battery mini-grid sites in Mozambique. A user selects a location (by clicking a map, entering coordinates, uploading a CSV, or picking from 200+ pre-scored priority sites), and the platform runs 18 analysis engines to produce a complete feasibility assessment — from demand estimation through financial modeling, environmental screening, and regulatory compliance.

An AI chat assistant (powered by Claude) is embedded in the platform. It has access to the full analysis results, settlement data, and AFUR (African Forum for Utility Regulators) policy knowledge, allowing users to interrogate results and get regulatory guidance in natural language.

### What It Produces

| Output | Format | Description |
|--------|--------|-------------|
| Pre-Feasibility Study | .docx (60+ pages) | Full investment-grade PFS document |
| Executive Summary | .docx (5 pages) | Concise decision-maker briefing |
| Financial Model | .xlsx | Color-coded spreadsheet with inputs/outputs |
| HTML Report | .html | Browser-viewable report with charts |
| Concession Application | .json | ARENE (Mozambique regulator) data sheet |
| AI Chat Responses | Streaming text | Context-aware answers using analysis data + AFUR policy |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vercel)                         │
│                                                                   │
│  Next.js 16 + React 19 + TypeScript 5 + Tailwind CSS 4           │
│  MapLibre GL JS (satellite map) + Recharts (charts)               │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Map Panel    │  │  Chat Panel  │  │  Analysis Tool Panel    │ │
│  │  (MapLibre)   │  │  (AI Chat)   │  │  (Wizard + Results)     │ │
│  │  37.5% width  │  │              │  │  62.5% width            │ │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘ │
│         ▲                  ▲                    ▲                  │
└─────────┼──────────────────┼────────────────────┼─────────────────┘
          │                  │                    │
          │  HTTPS/JSON      │  SSE Stream        │  HTTPS/JSON + Blob
          ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND (Railway)                          │
│                                                                   │
│  FastAPI 0.115 + Python 3.11 + Docker (GDAL, PostGIS)            │
│                                                                   │
│  Routers:                                                         │
│  ├── /api/sites/*         → Cluster lookup, screening, priority  │
│  ├── /api/analyze-site    → Full 18-engine analysis pipeline     │
│  ├── /api/reports/*       → PDF, PFS, Excel, Concession export   │
│  ├── /api/chat            → AI chat (Claude Sonnet 4, SSE)       │
│  └── /health              → Health check                         │
│                                                                   │
│  Engines (18):                                                    │
│  gis → demand → solar → sizing → distribution → financial        │
│  → carbon → grid_risk → productive_use → ess → climate           │
│  → risk → confidence → concession → report → pfs → excel         │
│                                                                   │
│  Knowledge:                                                       │
│  └── AFUR Technical Guide (regulatory policy for chat AI)        │
│                                                                   │
│  Data:                                                            │
│  ├── mozambique_dre_atlas_settlements.csv (10,000+ settlements)  │
│  └── countries/mozambique/*.json (configs, profiles, defaults)   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                             │
│                                                                   │
│  • Anthropic Claude API  — AI chat (requires ANTHROPIC_API_KEY)  │
│  • PVGIS API (EU JRC)   — Solar irradiance data (free, no key)  │
│  • PostgreSQL + PostGIS  — Optional spatial DB (Railway managed) │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Repository Structure

```
moz-minigrid/
├── frontend/                          # Next.js 16 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Landing page (/)
│   │   │   ├── analyze/page.tsx       # Main analysis wizard (/analyze)
│   │   │   ├── projects/page.tsx      # Projects list (/projects)
│   │   │   ├── layout.tsx             # Root layout (Inter font, AfCEN theme)
│   │   │   └── globals.css            # AfCEN design tokens
│   │   ├── components/
│   │   │   └── MozMap.tsx             # MapLibre GL interactive map
│   │   └── lib/
│   │       └── api.ts                 # API client (586 lines, typed interfaces)
│   ├── vercel.json                    # Vercel build config
│   ├── .env.local                     # Dev env
│   └── .env.production                # Prod env
│
├── backend/                           # FastAPI application
│   ├── app/
│   │   ├── main.py                    # App entry, CORS, router registration
│   │   ├── routers/
│   │   │   ├── sites.py               # GET /api/sites/lookup, /screen, /priority
│   │   │   ├── analysis.py            # POST /api/analyze-site
│   │   │   ├── reports.py             # POST /api/reports/{format}
│   │   │   └── chat.py                # POST /api/chat (SSE streaming)
│   │   ├── schemas/
│   │   │   ├── site.py                # ClusterInfo, SiteCoordinates
│   │   │   └── analysis.py            # 20+ Pydantic v2 models
│   │   ├── services/
│   │   │   └── analysis_service.py    # Orchestrates all 18 engines
│   │   ├── engines/                   # 18 analysis engines (see Section 5)
│   │   ├── knowledge/
│   │   │   └── afur_guide.py          # AFUR regulatory knowledge for chat AI
│   │   └── templates/
│   │       ├── pfs_template.py        # Full PFS Word template
│   │       └── pfs_summary_template.py # 5-page executive summary
│   ├── Dockerfile                     # Python 3.11 + GDAL
│   └── requirements.txt               # 17 Python dependencies
│
├── countries/mozambique/              # Country configuration data
│   ├── config.json                    # Project-level settings
│   ├── financial_defaults.json        # CAPEX/OPEX cost assumptions
│   ├── demand_tier_mapping.json       # Income → energy demand tier
│   ├── climate_hazards.json           # Hazard definitions
│   ├── ess_defaults.json              # Environmental screening params
│   ├── productive_use_sectors.json    # Sectoral demand by province
│   ├── priority_minigrid_sites.json   # 200+ pre-scored sites
│   └── load_profiles/                 # 24-hour demand profiles
│       ├── rural_residential.json
│       ├── commercial_periurban.json
│       └── mixed_productive.json
│
├── mozambique_dre_atlas_settlements.csv      # 10,000+ settlement database
├── mozambique_dre_atlas_settlements.geojson  # GeoJSON with geometries
├── docker-compose.yml                 # Local dev (PostGIS + API)
└── .env.example                       # Environment variable template
```

---

## 4. API Endpoints

### Sites

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sites/lookup?lat={lat}&lon={lon}` | Find nearest settlement cluster |
| GET | `/api/sites/screen?lat={lat}&lon={lon}` | Suitability screening |
| GET | `/api/sites/priority?province=&min_score=&limit=200` | List pre-scored priority sites |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze-site` | Run full 18-engine analysis pipeline |

**Request body:**
```json
{
  "latitude": -15.4347,
  "longitude": 40.6734,
  "name": "Mossuril",
  "overrides": {
    "households": 120,
    "demand_tier": 3,
    "pv_modules_usd_per_kwp": 580,
    "battery_ems_usd_per_kwh": 285,
    "affordable_tariff": 0.45
  }
}
```

### Reports

| Method | Endpoint | Response |
|--------|----------|----------|
| POST | `/api/reports/pdf` | HTML report |
| POST | `/api/reports/pfs` | Word document (.docx, 60+ pages) |
| POST | `/api/reports/pfs-summary` | 5-page executive summary (.docx) |
| POST | `/api/reports/excel` | Financial model (.xlsx) |
| POST | `/api/reports/concession` | ARENE concession data (.json) |

### Chat (AI Assistant)

| Method | Endpoint | Response |
|--------|----------|----------|
| POST | `/api/chat` | Server-Sent Events (text/event-stream) |

**Request body:**
```json
{
  "message": "Is this site suitable for a mini-grid?",
  "history": [
    {"role": "user", "content": "previous question"},
    {"role": "assistant", "content": "previous answer"}
  ],
  "analysis_result": { ... },
  "cluster": { ... }
}
```

**SSE response format:**
```
data: {"text": "Based on "}
data: {"text": "the analysis, "}
data: {"text": "this site..."}
data: [DONE]
```

### Health

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/health` | `{"status": "ok", "service": "moz-api"}` |

---

## 5. Analysis Engines (18)

The analysis pipeline runs sequentially in `analysis_service.py`. Each engine is independent and produces a typed output.

| # | Engine | Input | Output | What It Does |
|---|--------|-------|--------|-------------|
| 1 | **gis_engine** | lat/lon | ClusterInfo | Finds nearest settlement in DRE Atlas (10,000+ sites), returns population, buildings, infrastructure distances, nightlight, GHI, RWI |
| 2 | **demand_engine** | ClusterInfo + overrides | DemandEstimate | Estimates households, daily kWh, peak kW using ESMAP tier framework. Assigns 24-hour load profile |
| 3 | **solar_engine** | lat/lon | SolarResource | Fetches monthly GHI/DNI/temperature from EU PVGIS API. Calculates specific yield, performance ratio, loss breakdown |
| 4 | **sizing_engine** | DemandEstimate + SolarResource | SystemSizing | 2D sweep (12 PV × 7 battery configs). Simulates hourly dispatch to minimize unmet energy. Outputs PV kWp, battery kWh, inverter kVA |
| 5 | **distribution_engine** | ClusterInfo + DemandEstimate | DistributionDesign | Designs LV network using geometric Poisson model. Calculates line length, pole count, BoQ, voltage drop, technical losses |
| 6 | **financial_engine** | All above + overrides | FinancialResults | CAPEX breakdown (PV, battery, inverter, distribution, BOS, soft costs). LCOE, IRR, NPV, DSCR, payback. 25-year cash flow. Sensitivity analysis (±20%) |
| 7 | **carbon_engine** | sizing + demand | CarbonAssessment | Diesel displacement (litres/yr), CO2e baseline (2.8 kg/L), 25-year crediting. Revenue under 4 carbon price scenarios. NPV of carbon credits |
| 8 | **grid_risk_engine** | ClusterInfo + FinancialResults | GridRiskAssessment | Grid arrival timeline risk (low/medium/high/critical). 7 ESMAP transition scenarios with adjusted IRR/NPV |
| 9 | **productive_use_engine** | ClusterInfo | ProductiveUseAssessment | Sectoral relevance scoring (agro-processing, milling, irrigation, etc.). Anchor customer identification. Equipment recommendations |
| 10 | **ess_engine** | ClusterInfo + sizing | ESSScreening | IFC-aligned ESIA categorization. Protected area buffer checks. Biodiversity, resettlement, GESI screening |
| 11 | **climate_engine** | ClusterInfo + carbon | ClimateRationale | Climate hazard profiling (drought, flood, heat, cyclone). NDC alignment. Climate finance eligibility (GCF, carbon, concessional) |
| 12 | **risk_engine** | All above | RiskAnalysis | 18+ sub-risks across 6 categories. Likelihood × impact scoring (1-5). Top-3 risks. Mitigation allocation |
| 13 | **confidence_engine** | All above | ConfidenceAssessment | Data quality scoring per dimension (0-100). Margin of error (±%). Calibration status. Recommendations |
| 14 | **concession_engine** | All above | ConcessionDataSheet | ARENE (Mozambique regulator) structured application. 8+ sections matching regulatory requirements |
| 15 | **report_engine** | AnalysisResult | HTML string | Full HTML report with tables, badges, financial summaries |
| 16 | **pfs_engine** | AnalysisResult | .docx binary | Investment-grade PFS document (60+ pages) and 5-page summary |
| 17 | **excel_engine** | AnalysisResult | .xlsx binary | Color-coded financial model workbook |
| 18 | **solar_engine** (PVGIS) | lat/lon | API call | External: EU Joint Research Centre solar irradiance database |

---

## 6. AI Chat System

### How It Works

1. User types a question in the chat panel
2. Frontend sends the message + last 20 messages of history + current analysis result + cluster data to `POST /api/chat`
3. Backend builds a system prompt that includes:
   - **AFUR Technical Guide knowledge** (regulatory standards, safety-reliability-affordability framework, voltage economics, component standards, interconnection readiness)
   - **Current analysis results** (if available) — formatted summary of all engine outputs
   - **Cluster/settlement data** (if available) — population, infrastructure, resources
4. Backend calls **Claude Sonnet 4** (`claude-sonnet-4-20250514`) via the Anthropic SDK
5. Response streams back token-by-token via Server-Sent Events (SSE)
6. Frontend displays tokens as they arrive for real-time feel

### Knowledge Base

The AFUR guide (`backend/app/knowledge/afur_guide.py`) contains structured policy content:
- Mini-grid regulatory framework (licensing, tariffs, quality of service)
- Safety-Reliability-Affordability triangle
- Technical standards (IEC 62257, 61215, 61427-1)
- Voltage drop economics and network design guidelines
- Availability vs tariff tradeoffs
- Interconnection readiness levels
- Mozambique-specific regulatory context (ARENE, EDM, FUNAE)

### Required Environment Variable

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

This must be set on Railway for chat to work. Without it, the endpoint returns:
```json
{"detail": "ANTHROPIC_API_KEY not configured"}
```

---

## 7. Deployment Setup

### GitHub Repository

- **URL:** https://github.com/Denohatma/moz-minigrid
- **Branch:** `main` (single branch, auto-deploys to both Vercel and Railway)
- Push to `main` triggers both frontend and backend deployments

### Frontend — Vercel

| Setting | Value |
|---------|-------|
| **Platform** | Vercel |
| **Project** | `denohatmas-projects/frontend` |
| **Production URL** | https://frontend-pi-ten-66.vercel.app |
| **Framework** | Next.js (auto-detected) |
| **Root Directory** | `frontend/` |
| **Build Command** | `next build` (auto) |
| **Output Directory** | `.next` (auto) |
| **Node Version** | 18.x |

**Environment Variables (Vercel):**

| Variable | Value | Where |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `https://amiable-spontaneity-production.up.railway.app` | Set in `vercel.json` build env |

**Deployment Trigger:** Push to `main` on GitHub OR manual via `npx vercel --prod` from `frontend/` directory.

### Backend — Railway

| Setting | Value |
|---------|-------|
| **Platform** | Railway |
| **Production URL** | https://amiable-spontaneity-production.up.railway.app |
| **Root Directory** | `backend/` |
| **Builder** | Dockerfile |
| **Port** | 8000 |
| **Runtime** | Python 3.11 + GDAL |

**Environment Variables (Railway):**

| Variable | Value | Required |
|----------|-------|----------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Yes (for chat) |
| `DATABASE_URL` | Auto-provisioned by Railway | Auto |
| `CORS_ORIGINS` | `https://frontend-pi-ten-66.vercel.app,http://localhost:3000` | Recommended |

**Deployment Trigger:** Push to `main` on GitHub (auto-deploy).

---

## 8. Integration Guide for IT Lead

### Step 1: Clone the Repository

```bash
git clone https://github.com/Denohatma/moz-minigrid.git
cd moz-minigrid
```

### Step 2: Local Development Setup

```bash
# Start PostgreSQL + PostGIS + Backend
docker-compose up -d

# Start Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:3000/analyze
```

The backend runs on `http://localhost:8001` via Docker. The frontend `.env.local` can be changed to point to local backend:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### Step 3: Deploy Backend to Your Own Railway

1. Create a Railway account at https://railway.app
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select `Denohatma/moz-minigrid`
4. Set **Root Directory** to `backend`
5. Railway auto-detects the Dockerfile and builds
6. Add environment variables in the **Variables** tab:
   - `ANTHROPIC_API_KEY` = your Anthropic API key
   - `CORS_ORIGINS` = your frontend URL(s), comma-separated
7. Railway assigns a public URL (e.g., `https://your-project.up.railway.app`)

### Step 4: Deploy Frontend to Your Own Vercel

1. Create a Vercel account at https://vercel.com
2. Click **"Add New"** → **"Project"** → Import from GitHub
3. Select `Denohatma/moz-minigrid`
4. Set **Root Directory** to `frontend`
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = your Railway backend URL from Step 3
6. Deploy — Vercel assigns a URL (e.g., `https://your-project.vercel.app`)
7. Go back to Railway and add this URL to `CORS_ORIGINS`

### Step 5: Get the Anthropic API Key

1. Go to https://console.anthropic.com/settings/keys
2. Create an account or log in
3. Click **"Create Key"**
4. Copy the key (starts with `sk-ant-api03-...`)
5. Add it to Railway as `ANTHROPIC_API_KEY`
6. Railway auto-redeploys — chat is now live

### Step 6: Verify Everything Works

```bash
# Health check
curl https://YOUR-RAILWAY-URL/health
# → {"status": "ok", "service": "moz-api"}

# Cluster lookup
curl "https://YOUR-RAILWAY-URL/api/sites/lookup?lat=-15.4347&lon=40.6734"
# → {"id": "kvkbu98xce", "village_name": "Mossuril", ...}

# Full analysis
curl -X POST https://YOUR-RAILWAY-URL/api/analyze-site \
  -H "Content-Type: application/json" \
  -d '{"latitude": -15.4347, "longitude": 40.6734}'
# → Full AnalysisResult JSON

# Chat test
curl -X POST https://YOUR-RAILWAY-URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AFUR?", "history": []}'
# → SSE stream of text chunks
```

### Step 7: Custom Domain (Optional)

**Vercel:**
1. Go to Project Settings → Domains
2. Add your domain (e.g., `moz.africacen.org`)
3. Update DNS as instructed

**Railway:**
1. Go to Service Settings → Networking → Custom Domain
2. Add your domain (e.g., `api-moz.africacen.org`)
3. Update DNS as instructed
4. Update `CORS_ORIGINS` to include the new frontend domain

---

## 9. Technology Stack Summary

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.2.6 | React framework (SSR/SSG) |
| React | 19.2.4 | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first CSS |
| MapLibre GL JS | 5.24.0 | Interactive satellite map |
| Recharts | 3.8.1 | Charts and data visualization |
| PapaParse | 5.5.3 | CSV file parsing |
| Lucide React | 1.14.0 | Icons |

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115.6 | Web framework |
| Python | 3.11 | Runtime |
| Pydantic | 2.10.4 | Data validation and schemas |
| NumPy | 2.2.1 | Numerical computing |
| Pandas | 2.2.3 | Data manipulation |
| SciPy | 1.15.0 | System sizing optimization |
| GeoPandas | 1.0.1 | Geospatial data processing |
| Shapely | 2.0.6 | Geometry operations |
| Rasterio | 1.4.3 | Raster GIS data |
| SQLAlchemy | 2.0.36 | Database ORM |
| GeoAlchemy2 | 0.17.1 | PostGIS extension |
| OpenPyXL | 3.1.5 | Excel file generation |
| python-docx | 1.1.2 | Word document generation |
| Matplotlib | 3.9.3 | Chart generation for reports |
| Anthropic SDK | 0.52.0 | Claude AI chat |

### Infrastructure

| Service | Purpose |
|---------|---------|
| GitHub | Source code, CI trigger |
| Vercel | Frontend hosting (auto-deploy from `main`) |
| Railway | Backend hosting (Docker, auto-deploy from `main`) |
| PostgreSQL + PostGIS | Spatial database (Railway managed) |
| Anthropic Claude API | AI chat assistant |
| EU PVGIS API | Solar irradiance data |

---

## 10. Data Sources

| Dataset | Source | Records | Usage |
|---------|--------|---------|-------|
| DRE Atlas Settlements | World Bank DRE Atlas 2025 | 10,000+ | Cluster lookup, population, buildings, demand, resources |
| Solar Irradiance | EU JRC PVGIS API | Per-request | Monthly GHI, DNI, temperature |
| AFUR Technical Guide | AFUR Dec 2023 | Policy document | Chat AI knowledge base |
| Priority Sites | AfCEN analysis | 200+ | Pre-scored mini-grid candidates |
| Country Config | AfCEN/World Bank | 8 JSON files | Financial defaults, demand tiers, load profiles, hazards |

---

## 11. Design System (AfCEN Branding)

| Token | Hex | Usage |
|-------|-----|-------|
| `afcen-navy` | `#0f1b2b` | Backgrounds, primary dark |
| `afcen-navy-light` | `#162236` | Card backgrounds |
| `afcen-navy-mid` | `#1c2d42` | Elevated surfaces |
| `afcen-gold` | `#d3a54a` | Primary accent, buttons, highlights |
| `afcen-gold-light` | `#e4c07a` | Hover states |
| `afcen-cream` | `#f5f1e8` | Text, foreground |
| `afcen-cream-dark` | `#f5efe2` | Secondary text |

**Font:** Inter (Google Fonts)  
**Headings:** Uppercase with `tracking-[0.15em]`

---

## 12. Current Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://frontend-pi-ten-66.vercel.app |
| Backend API | https://amiable-spontaneity-production.up.railway.app |
| API Docs (Swagger) | https://amiable-spontaneity-production.up.railway.app/docs |
| GitHub Repo | https://github.com/Denohatma/moz-minigrid |

---

## 13. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Chat returns `"ANTHROPIC_API_KEY not configured"` | Missing env var on Railway | Add `ANTHROPIC_API_KEY` in Railway Variables tab |
| Frontend shows old version after push | Vercel auto-deploy disconnected | Run `cd frontend && npx vercel --prod` manually |
| CORS errors in browser console | Backend doesn't allow frontend origin | Add frontend URL to `CORS_ORIGINS` on Railway |
| Analysis returns 500 error | Settlement CSV not found | Ensure `mozambique_dre_atlas_settlements.csv` is in backend root |
| Solar data missing | PVGIS API timeout | Engine falls back to hardcoded annual averages |
| Docker build fails on M1 Mac | GDAL ARM compatibility | Use `platform: linux/amd64` in docker-compose.yml |
