---
date: 2026-05-12
topic: minigrid-prefeasibility-platform
---

# Mini-Grid Prefeasibility Platform for Mozambique

## Problem Frame

Development finance institutions (DFIs), donors, and impact investors screening mini-grid investment opportunities in Mozambique lack a fast, standardized way to generate prefeasibility studies for candidate sites. Current approaches require expensive consultant engagements or ad-hoc spreadsheet models, making it hard to screen pipeline at scale. There is no tool that combines Mozambique's geospatial context (solar resource, population, grid proximity, terrain) with financial modeling to produce investment-grade prefeasibility outputs from just a GPS coordinate.

The platform should let a DFI analyst drop a pin on a map (or enter GPS coordinates), and receive a full prefeasibility package — technology sizing, financial model, demand estimates, tariff analysis, and subsidy gap quantification — without needing GIS expertise or Python skills.

## Requirements

### Site Input & Data

- R1. **GPS-based site definition**: User enters one or more site locations via GPS coordinates or by clicking on an interactive map of Mozambique.
- R2. **Pre-loaded GIS layers**: Platform ships with core geospatial data pre-processed for Mozambique — solar irradiation (GHI), wind speed, population density/clusters, grid network (HV/MV lines), road network, elevation, slope, land cover, travel time, nighttime lights, administrative boundaries.
- R3. **Automatic data extraction**: Given a GPS coordinate, the system extracts all relevant geospatial attributes for the site and surrounding area (population catchment, solar resource, nearest grid connection, terrain, accessibility).
- R4. **Smart demand estimation**: When no user-supplied demand data exists, the system generates demand estimates from geospatial data — auto-detecting the settlement cluster boundary around the GPS point using the GEP population clustering methodology (adjacent populated cells merged into polygons, split by admin boundaries), then applying urban/rural classification, nighttime light intensity as electrification proxy, and MTF-aligned demand tier assignment. Uses the OnSSET/GEP methodology as the analytical foundation.
- R5. **User data override**: Users can upload supplementary documents (demand surveys, household data, consumption measurements) that override the system-generated demand estimates. The system should parse common formats (CSV, Excel) and map uploaded data to the model inputs.
- R6. **Batch site upload**: Users can upload a CSV/Excel file with multiple GPS coordinates to analyze a portfolio of candidate sites in one session.

### Technology Sizing

- R7. **Solar + battery system design**: For each site, the platform sizes a solar PV + battery storage mini-grid system based on estimated demand profile, solar resource, and standard design parameters (days of autonomy, depth of discharge, system losses, panel degradation).
- R8. **Component specification**: Output includes PV array capacity (kWp), battery storage capacity (kWh), inverter sizing (kVA), and distribution network requirements (LV lines, service connections, meters).
- R9. **Demand growth scenarios**: Model demand growth over the project lifetime (default 20 years) with configurable annual growth rates, accounting for productive use development and connection ramp-up.

### Financial Analysis

- R10. **LCOE calculation**: Compute levelized cost of electricity for the sized system using discounted cash flow methodology — capital costs, O&M, battery replacement, distribution maintenance, all discounted over project life.
- R11. **Return metrics**: Calculate IRR, NPV, payback period, and DSCR for the project under configurable tariff and financing assumptions.
- R12. **Tariff & affordability analysis**: Determine the cost-reflective tariff required for viability, compare against household willingness-to-pay benchmarks for the area (derived from income/poverty data or user-supplied survey data), and flag affordability gaps.
- R13. **Subsidy gap quantification**: Calculate the grant or concessional funding required to bridge the gap between the cost-reflective tariff and an affordable tariff, expressed as $/connection, total grant amount, and % of CAPEX.
- R14. **Sensitivity analysis**: Run key sensitivities — solar resource variation, demand growth scenarios, CAPEX changes, tariff levels, discount rate — and present tornado/spider charts showing which parameters most affect viability.
- R15. **Configurable assumptions**: All financial parameters (discount rate, equipment costs, O&M percentages, tariff, financing terms, tax, inflation) exposed to the user with Mozambique-appropriate defaults that can be overridden.

### Grid Arrival Risk

- R16. **Grid proximity assessment**: For each site, calculate and display distance to nearest existing grid infrastructure (HV and MV lines), distance to planned grid extensions, and estimated grid arrival timeline where data exists.
- R17. **Grid arrival scenario modeling**: Where Mozambique's regulatory framework (ARENE/EDM) provides for grid-connected mini-grids or compensated handover, model financial impact of grid arrival at different years during the project lifetime. Where regulations are absent or unclear, flag grid arrival as a qualitative risk with distance-based severity rating.

### Multi-Site Comparison

- R18. **Site ranking dashboard**: When multiple sites are analyzed, present a comparison view ranking sites by key metrics — LCOE, IRR, subsidy gap per connection, population served, demand density — with sortable columns and visual indicators.
- R19. **Portfolio summary**: Aggregate investment requirement, total population served, and average financial metrics across the selected portfolio of sites.

### Report Generation

- R20. **PDF prefeasibility report**: Generate a professional, formatted PDF report per site containing: executive summary, site description with map, population and demand analysis, system sizing, financial model summary, sensitivity analysis, risk assessment (including grid arrival), and key assumptions. Ready for investment committee presentation.
- R21. **Excel financial model**: Generate a downloadable Excel workbook per site with all assumptions exposed in input sheets, detailed cash flow projections, sensitivity tables, and charts. Analysts can modify inputs and observe recalculated outputs.
- R22. **Batch export**: For multi-site analyses, generate a portfolio summary PDF and individual site reports as a ZIP download.

### Platform & UX

- R23. **Web application**: Browser-based platform with interactive map interface (Mozambique), form-based parameter inputs, and dashboard views. No Python or technical skills required.
- R24. **Mozambique-first, country-extensible**: Launch with Mozambique data, currency (MZN), regulations, and defaults. Architecture allows adding new countries via configuration (GIS data package + country parameters) without rebuilding the platform.
- R25. **User accounts and projects**: Users can save analyses, return to previous studies, and share results with colleagues.

## Success Criteria

- A DFI analyst can go from GPS coordinate to downloadable prefeasibility report in under 15 minutes without technical assistance.
- System-generated demand estimates are within 30% of actuals when validated against sites with known demand data.
- Financial outputs (LCOE, IRR) are consistent with manually-prepared prefeasibility studies for the same sites.
- Platform can process a batch of 20+ sites and produce a ranked portfolio view in a single session.

## Scope Boundaries

- **In scope**: Solar + battery mini-grids only. Other generation technologies (diesel, wind, hydro) are excluded from V1.
- **In scope**: Mozambique only for launch. Country extensibility is an architectural requirement, not a V1 feature.
- **Out of scope**: Detailed engineering design (single-line diagrams, protection schemes, civil works).
- **Out of scope**: Procurement or contractor matching.
- **Out of scope**: Real-time monitoring or operational dashboards for built mini-grids.
- **Out of scope**: Regulatory filing or permit application generation.
- **Not a replacement for full feasibility**: This is a screening and prefeasibility tool. It informs go/no-go decisions and prioritization, not final investment decisions.

## Key Decisions

- **Solar + battery only for V1**: Simplifies the sizing engine significantly. Most Mozambique mini-grid deployments are solar-battery; adding diesel hybrid or other technologies is a future enhancement.
- **Hybrid data approach**: Pre-loaded GIS for Mozambique eliminates the GIS expertise barrier. User uploads override system estimates when better data exists — this gives DFIs flexibility without requiring it.
- **Smart demand estimation with override**: The GEP/OnSSET methodology (population clustering, NTL-based electrification proxy, MTF demand tiers) provides a defensible baseline. User-supplied surveys improve accuracy when available.
- **Grid arrival modeled where regulations exist**: Mozambique has evolving mini-grid regulations under ARENE. Where compensated handover or grid integration frameworks exist, model the financial impact. Otherwise flag qualitatively.
- **Both PDF and Excel outputs**: PDF serves the investment committee; Excel serves the analyst who needs to stress-test assumptions.

## Dependencies / Assumptions

- Pre-processed GIS data for Mozambique must be sourced and prepared before the platform can function. Key datasets: HRSL population (or GHS-POP), SolarGIS/Global Solar Atlas GHI, VIIRS NTL, EDM grid network, GADM admin boundaries, OSM roads, SRTM elevation.
- Mozambique mini-grid regulatory framework (ARENE licensing, EDM grid extension plans) must be researched for grid arrival modeling.
- Equipment cost defaults require market research for Mozambique-specific pricing (solar panels, batteries, inverters, LV distribution).
- Currency handling: financial model should work in both MZN and USD with configurable exchange rate.

## Outstanding Questions

### Resolve Before Planning

None — all blocking questions resolved.

### Deferred to Planning
- [Affects R2][Needs research] What is the most current and complete set of pre-processed GIS data available for Mozambique, and what gaps need to be filled?
- [Affects R7][Technical] What solar PV + battery sizing methodology should be used — simplified analytical model, or integration with an existing tool like HOMER/iHOGA logic?
- [Affects R16, R17][Needs research] What is the current state of Mozambique's mini-grid regulatory framework under ARENE, and what grid arrival compensation mechanisms exist?
- [Affects R20][Technical] What PDF generation library/approach best supports the map + chart + table report format needed?
- [Affects R24][Technical] What architecture pattern best supports the country-extensible requirement — country config files, multi-tenant data, or plugin system?
- [Affects R15][Needs research] What are appropriate default financial parameters for Mozambique mini-grids (equipment costs, O&M rates, typical tariffs, discount rates)?

## Next Steps

One blocking question remains under "Resolve Before Planning" — the site catchment definition approach. Once resolved:

-> `/ce:plan` for structured implementation planning

**Catchment decision resolved**: Auto-detect settlement cluster boundaries from population data using GEP clustering methodology. The GPS point identifies which pre-computed cluster the site belongs to.
