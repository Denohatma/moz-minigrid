from __future__ import annotations

import math
from pathlib import Path

from app.schemas.site import ClusterInfo
from app.schemas.analysis import (
    CarbonAssessment,
    ClimateFinanceEligibility,
    ClimateHazard,
    ClimateRationale,
    SystemSizing,
)

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

# ── Constants ──────────────────────────────────────────────────────

PROJECT_LIFE_YEARS = 25
ANNUAL_DEGRADATION = 0.005  # 0.5 % PV degradation per year

# Mozambique NDC: 40 MtCO2e reduction by 2030 (conditional on int'l support)
NDC_TARGET_MTCO2E = 40.0
NDC_ENERGY_SHARE = 0.12  # energy sector's share of NDC target

# Approximate Mozambique coastline longitude by latitude band.
# Eastern boundary of land is roughly the Indian Ocean coast.
_COAST_LON: list[tuple[float, float, float]] = [
    # (lat_south, lat_north, approx_coast_longitude)
    (-27.0, -25.0, 33.0),   # far south (Maputo area)
    (-25.0, -23.5, 35.0),   # Inhambane coast
    (-23.5, -21.0, 35.5),   # Save river mouth area
    (-21.0, -19.0, 35.0),   # Sofala / Beira
    (-19.0, -17.0, 37.0),   # Zambezia coast
    (-17.0, -15.0, 40.0),   # Nampula coast
    (-15.0, -13.0, 40.5),   # Cabo Delgado southern coast
    (-13.0, -10.0, 40.5),   # Pemba / far north coast
]

# Major river basins — represented as lat/lon bounding boxes with buffer
_RIVER_BASINS: list[tuple[str, float, float, float, float]] = [
    # (name, lat_south, lat_north, lon_west, lon_east)
    ("Zambezi",   -18.5, -15.5, 30.0, 37.0),
    ("Limpopo",   -25.5, -22.5, 31.0, 35.0),
    ("Save",      -22.5, -20.0, 33.0, 35.5),
    ("Incomati",  -26.5, -25.0, 31.5, 33.0),
    ("Buzi",      -20.5, -19.0, 33.5, 35.0),
    ("Rovuma",    -12.5, -11.0, 35.0, 40.5),
]

# Provincial latitude bands (approximate)
_SOUTHERN_LAT_BOUND = -22.0   # Gaza / Inhambane below this
_CENTRAL_LAT_BOUND = -17.0    # Sofala / Zambezia between south and this
_NORTHERN_LAT_BOUND = -14.0   # Nampula / Niassa between central and this
# Above northern bound: Cabo Delgado


# ── Public API ─────────────────────────────────────────────────────

def assess_climate_rationale(
    latitude: float,
    longitude: float,
    cluster: ClusterInfo,
    carbon: CarbonAssessment,
    sizing: SystemSizing,
    annual_energy_served_kwh: float,
) -> ClimateRationale:
    """Build an enhanced climate rationale that extends the carbon assessment.

    Combines mitigation data from the existing carbon engine with
    adaptation narratives, hazard exposure analysis, resilience design
    measures, and climate-finance eligibility scoring — all grounded in
    Mozambique-specific geography and policy context.
    """
    warnings: list[str] = []

    # ── 1. Mitigation ──────────────────────────────────────────────
    lifetime_avoided = _lifetime_avoided_emissions(
        carbon.annual_emission_reductions_tco2e,
    )
    per_capita = (
        lifetime_avoided / max(cluster.population, 1) / PROJECT_LIFE_YEARS
    )
    ndc_text = _ndc_alignment_narrative(carbon.annual_emission_reductions_tco2e)

    # ── 2. Adaptation ──────────────────────────────────────────────
    livelihoods = _climate_resilient_livelihoods(cluster)
    water_sec = _water_security(cluster)
    food_sec = _food_security(cluster)
    energy_adapt = _energy_access_adaptation(cluster)
    adaptation_narrative = _adaptation_narrative(
        cluster, livelihoods, water_sec, food_sec, energy_adapt,
    )

    # ── 3. Hazards ─────────────────────────────────────────────────
    hazards = _assess_hazards(latitude, longitude, cluster)
    overall_hazard = _overall_hazard_level(hazards)
    resilience_measures = _design_resilience_measures(hazards)

    # ── 4. Climate Finance ─────────────────────────────────────────
    finance = _climate_finance_eligibility(
        carbon, cluster, sizing, annual_energy_served_kwh, hazards,
    )
    score = _climate_finance_score(finance)
    total_potential = sum(f.estimated_value_usd for f in finance)

    if total_potential == 0:
        warnings.append(
            "No climate-finance value could be estimated. "
            "Engage a climate finance advisor for detailed structuring."
        )

    return ClimateRationale(
        lifetime_avoided_tco2e=round(lifetime_avoided, 1),
        per_capita_reduction_tco2e=round(per_capita, 4),
        ndc_alignment=ndc_text,
        adaptation_narrative=adaptation_narrative,
        climate_resilient_livelihoods=livelihoods,
        water_security_contribution=water_sec,
        food_security_contribution=food_sec,
        energy_access_adaptation=energy_adapt,
        hazards=hazards,
        overall_hazard_level=overall_hazard,
        design_resilience_measures=resilience_measures,
        climate_finance=finance,
        climate_finance_score=score,
        total_climate_finance_potential_usd=round(total_potential, 0),
        warnings=warnings,
    )


# ── Mitigation helpers ─────────────────────────────────────────────

def _lifetime_avoided_emissions(annual_tco2e: float) -> float:
    """25-year cumulative avoided emissions with 0.5 % annual PV degradation."""
    total = 0.0
    for yr in range(PROJECT_LIFE_YEARS):
        total += annual_tco2e * (1 - ANNUAL_DEGRADATION) ** yr
    return total


def _ndc_alignment_narrative(annual_tco2e: float) -> str:
    energy_target = NDC_TARGET_MTCO2E * NDC_ENERGY_SHARE * 1e6  # tCO2e
    pct = annual_tco2e / energy_target * 100 if energy_target else 0
    return (
        f"Mozambique's NDC targets a {NDC_TARGET_MTCO2E:.0f} MtCO2e conditional "
        f"reduction by 2030, with the energy sector responsible for approximately "
        f"{NDC_ENERGY_SHARE * 100:.0f}% ({energy_target:,.0f} tCO2e). This project "
        f"contributes {annual_tco2e:.1f} tCO2e/yr ({pct:.4f}% of the energy-sector "
        f"target), directly supporting Mozambique's decarbonisation pathway through "
        f"displacement of diesel generation in off-grid communities."
    )


# ── Adaptation helpers ─────────────────────────────────────────────

def _climate_resilient_livelihoods(cluster: ClusterInfo) -> list[str]:
    sectors: list[str] = []
    if cluster.ag_area_ha and cluster.ag_area_ha > 0:
        sectors.append("Agricultural processing and cold storage")
        sectors.append("Solar-powered irrigation")
    if cluster.has_health_facility:
        sectors.append("Health facility electrification and vaccine cold chain")
    if cluster.has_education_facility:
        sectors.append("Electrified education facilities with ICT access")
    if cluster.population > 500:
        sectors.append("Small enterprise development (welding, milling, charging)")
    if cluster.closest_distance_water_km is not None and cluster.closest_distance_water_km < 5:
        sectors.append("Water pumping and treatment")
    if not sectors:
        sectors.append("Basic lighting and phone charging for household resilience")
    return sectors


def _water_security(cluster: ClusterInfo) -> str:
    parts: list[str] = []
    if cluster.has_health_facility:
        parts.append(
            "Energy access enables vaccine cold-chain maintenance and "
            "electric water pumping at health facilities, strengthening "
            "community health resilience against climate-sensitive diseases."
        )
    if cluster.closest_distance_water_km is not None and cluster.closest_distance_water_km < 5:
        parts.append(
            "Proximity to water sources allows solar-powered pumping, "
            "improving drought resilience and reducing time poverty."
        )
    if not parts:
        return (
            "Mini-grid provides energy for water boiling and purification, "
            "a baseline contribution to water security."
        )
    return " ".join(parts)


def _food_security(cluster: ClusterInfo) -> str:
    crop_area = cluster.ag_area_ha or 0
    crop_value = cluster.ag_value_usd or 0
    if crop_area > 0:
        return (
            f"The settlement has {crop_area:.0f} ha of agricultural land "
            f"(estimated value USD {crop_value:,.0f}). Mini-grid electricity "
            f"enables cold storage to reduce post-harvest losses (typically "
            f"30-40% in Mozambique), solar irrigation to extend growing "
            f"seasons, and grain milling to add value locally — all of "
            f"which strengthen food security under increasing climate stress."
        )
    return (
        "Limited local agricultural data. Energy access supports basic "
        "food preservation through refrigeration and enables small-scale "
        "food processing, contributing to household food security."
    )


def _energy_access_adaptation(cluster: ClusterInfo) -> str:
    pop = cluster.population
    return (
        f"Reliable electricity for a community of {pop:,} people strengthens "
        f"disaster preparedness through mobile communication (early warning "
        f"systems), lighting for emergency shelters, and power for community "
        f"radio. Post-disaster recovery is accelerated when health facilities, "
        f"water systems, and communication networks remain energised."
    )


def _adaptation_narrative(
    cluster: ClusterInfo,
    livelihoods: list[str],
    water_sec: str,
    food_sec: str,
    energy_adapt: str,
) -> str:
    n_sectors = len(livelihoods)
    return (
        f"This mini-grid project contributes to climate adaptation across "
        f"{n_sectors} productive-use sectors. By providing reliable "
        f"electricity to an off-grid community of {cluster.population:,} "
        f"people, the project diversifies livelihoods, reduces dependence "
        f"on rain-fed agriculture, and strengthens institutional capacity "
        f"(health, education) to respond to climate shocks. Mozambique "
        f"ranks among the most climate-vulnerable countries globally "
        f"(ND-GAIN rank 162/182); decentralised energy access is a "
        f"proven adaptation strategy that builds resilience from the "
        f"community level."
    )


# ── Hazard assessment ──────────────────────────────────────────────

def _distance_to_coast_km(lat: float, lon: float) -> float:
    """Approximate distance to coast using latitude-band coastline data."""
    coast_lon = _COAST_LON[-1][2]  # default to far-north coast
    for lat_s, lat_n, c_lon in _COAST_LON:
        if lat_s <= lat <= lat_n:
            coast_lon = c_lon
            break
    # 1 degree longitude ~ 111 km * cos(lat)
    delta_lon = coast_lon - lon
    km_per_deg = 111.0 * math.cos(math.radians(abs(lat)))
    return abs(delta_lon) * km_per_deg


def _in_river_basin(lat: float, lon: float) -> str | None:
    for name, lat_s, lat_n, lon_w, lon_e in _RIVER_BASINS:
        if lat_s <= lat <= lat_n and lon_w <= lon <= lon_e:
            return name
    return None


def _assess_cyclone(lat: float, lon: float) -> ClimateHazard:
    dist_coast = _distance_to_coast_km(lat, lon)
    # Central coast (Sofala / Zambezia) — Cyclone Idai/Kenneth corridor
    is_central_coast = -21.0 <= lat <= -15.0 and dist_coast < 150

    if is_central_coast and dist_coast < 100:
        level, desc = "very_high", (
            "Located in the Cyclone Idai/Kenneth corridor (central-northern "
            "Mozambique coast). This area experienced Category 4 cyclones in "
            "2019 and remains highly exposed to tropical cyclone landfall."
        )
    elif dist_coast < 100 and lat > -17.0:
        level, desc = "high", (
            "Northern coastal zone with significant tropical cyclone exposure. "
            "Cabo Delgado and northern Nampula provinces face recurring cyclone "
            "threats during the November-April season."
        )
    elif dist_coast < 100:
        level, desc = "high", (
            "Coastal zone within 100 km of the Indian Ocean shoreline. "
            "Exposed to tropical cyclone wind speeds and storm surge."
        )
    elif dist_coast < 200:
        level, desc = "moderate", (
            "Transitional zone 100-200 km from coast. Reduced but still "
            "significant cyclone wind and rainfall risk."
        )
    else:
        level, desc = "low", (
            "Inland location over 200 km from the coast. Cyclone wind "
            "risk is low, though extreme rainfall from decaying cyclones "
            "can still cause localised flooding."
        )

    measures = _cyclone_design_measures(level)
    return ClimateHazard(
        hazard="cyclone", level=level, description=desc, design_measures=measures,
    )


def _cyclone_design_measures(level: str) -> list[str]:
    if level in ("very_high", "high"):
        return [
            "Cyclone-rated PV mounting structures (wind load >= 200 km/h)",
            "Underground or armoured cabling for LV distribution",
            "Reinforced battery enclosure with waterproof sealing",
            "Elevated control room above historical flood level",
            "Rapid-disconnect systems for pre-cyclone shutdown",
        ]
    if level == "moderate":
        return [
            "Enhanced wind-load rated mounting (>= 150 km/h)",
            "Protected cable routing with strain relief",
            "Waterproof battery and inverter enclosures",
        ]
    return ["Standard mounting with adequate wind-load margins"]


def _assess_flood(lat: float, lon: float, cluster: ClusterInfo) -> ClimateHazard:
    dist_coast = _distance_to_coast_km(lat, lon)
    elevation = cluster.elevation_m or 100.0
    river = _in_river_basin(lat, lon)

    if river and elevation < 50:
        level, desc = "high", (
            f"Located in the {river} river basin at low elevation "
            f"({elevation:.0f} m). Major river basins in Mozambique "
            f"experience severe seasonal flooding, exacerbated by "
            f"upstream rainfall and cyclone events."
        )
    elif river:
        level, desc = "moderate", (
            f"Located within the {river} river basin but at moderate "
            f"elevation ({elevation:.0f} m), providing some natural "
            f"flood protection. Seasonal high-water events still pose risk."
        )
    elif dist_coast < 50 and elevation < 50:
        level, desc = "high", (
            f"Low-lying coastal area ({elevation:.0f} m elevation, "
            f"{dist_coast:.0f} km from coast). Exposed to coastal "
            f"flooding from storm surge and heavy rainfall."
        )
    elif elevation < 50:
        level, desc = "moderate", (
            f"Low elevation ({elevation:.0f} m) with potential for "
            f"localised flooding during heavy rainfall events."
        )
    else:
        level, desc = "low", (
            f"Elevated location ({elevation:.0f} m) with limited "
            f"flood exposure from major river systems or coastal surge."
        )

    measures = _flood_design_measures(level)
    return ClimateHazard(
        hazard="flood", level=level, description=desc, design_measures=measures,
    )


def _flood_design_measures(level: str) -> list[str]:
    if level == "high":
        return [
            "Elevated foundations (minimum 1.5 m above grade / historical flood line)",
            "Raised battery and inverter platform with drainage channels",
            "Flood-resistant cable conduits and sealed junction boxes",
            "Site selection preference for highest local ground",
        ]
    if level == "moderate":
        return [
            "Elevated foundations (minimum 0.5 m above grade)",
            "Sealed electrical enclosures rated IP65 or higher",
            "Graded site drainage to prevent water pooling",
        ]
    return ["Standard foundation with basic site drainage"]


def _assess_drought(lat: float) -> ClimateHazard:
    if lat < _SOUTHERN_LAT_BOUND:
        level, desc = "high", (
            "Southern Mozambique (Gaza / Inhambane provinces) is the "
            "country's primary drought corridor. Multi-year droughts "
            "regularly affect agricultural production and water availability. "
            "Mini-grid energy for irrigation and water pumping is a "
            "critical adaptation measure."
        )
    elif lat < _CENTRAL_LAT_BOUND:
        level, desc = "moderate", (
            "Central Mozambique experiences periodic drought, particularly "
            "in rain shadow areas. Climate projections indicate increasing "
            "dry-spell frequency under warming scenarios."
        )
    elif lat < _NORTHERN_LAT_BOUND:
        level, desc = "moderate", (
            "Northern Mozambique has more reliable rainfall but faces "
            "increasing inter-annual variability. Drought risk is moderate "
            "and growing under climate change projections."
        )
    else:
        level, desc = "low", (
            "Northern highlands and Cabo Delgado receive relatively "
            "consistent rainfall. Drought risk is lower than in the "
            "south, though climate variability is increasing."
        )

    measures: list[str] = []
    if level in ("high", "moderate"):
        measures = [
            "Prioritise solar-powered irrigation as productive use",
            "Include water pumping capacity in demand projections",
            "Design for dry-cooled battery systems (no water dependency)",
        ]
    else:
        measures = ["No specific drought-related design measures required"]
    return ClimateHazard(
        hazard="drought", level=level, description=desc, design_measures=measures,
    )


def _assess_sea_level_rise(lat: float, lon: float) -> ClimateHazard:
    dist_coast = _distance_to_coast_km(lat, lon)

    if dist_coast < 10:
        level, desc = "high", (
            "Located within 10 km of the coast. Sea level rise projections "
            "for Mozambique indicate 0.3-0.6 m rise by 2100 (RCP 4.5/8.5), "
            "increasing saltwater intrusion, coastal erosion, and tidal "
            "flooding frequency at this proximity."
        )
    elif dist_coast < 50:
        level, desc = "moderate", (
            "Located 10-50 km from the coast. Indirect sea level rise "
            "impacts include increased groundwater salinity and amplified "
            "storm surge penetration during cyclone events."
        )
    else:
        level, desc = "negligible", (
            "Inland location with negligible direct sea level rise "
            "exposure. No specific design adaptations required."
        )

    measures: list[str] = []
    if level == "high":
        measures = [
            "Corrosion-resistant materials for all metal components (marine-grade aluminium or stainless steel)",
            "Elevated equipment platforms above projected 50-year flood line",
            "Sealed cable entries to prevent saltwater ingress",
            "Sacrificial anodes or cathodic protection for grounding systems",
        ]
    elif level == "moderate":
        measures = [
            "Corrosion-resistant coatings for external metal surfaces",
            "Monitor groundwater salinity for equipment foundations",
        ]
    else:
        measures = ["No sea-level-rise-specific design measures required"]

    return ClimateHazard(
        hazard="sea_level_rise", level=level, description=desc,
        design_measures=measures,
    )


def _assess_heat_stress(cluster: ClusterInfo) -> ClimateHazard:
    elevation = cluster.elevation_m or 100.0

    if elevation < 200:
        level, desc = "moderate", (
            f"Lowland location ({elevation:.0f} m elevation). Ambient "
            f"temperatures regularly exceed 35 C in the hot season "
            f"(October-March), reducing PV panel efficiency by 5-10% "
            f"and accelerating battery degradation without thermal management."
        )
    elif elevation < 500:
        level, desc = "low", (
            f"Mid-elevation location ({elevation:.0f} m). Heat stress "
            f"is present during peak summer months but is less severe "
            f"than in the lowlands."
        )
    else:
        level, desc = "low", (
            f"Highland location ({elevation:.0f} m). Lower ambient "
            f"temperatures reduce heat-related efficiency losses "
            f"and extend battery lifespan."
        )

    measures: list[str] = []
    if level == "moderate":
        measures = [
            "Battery climate control (ventilated or air-conditioned enclosure)",
            "Temperature-derated battery sizing (add 10-15% capacity margin)",
            "PV module selection with low temperature coefficient",
            "Adequate ventilation gaps beneath PV arrays",
        ]
    else:
        measures = [
            "Standard ventilation for battery enclosure",
            "Monitor ambient temperature for performance tracking",
        ]

    return ClimateHazard(
        hazard="heat_stress", level=level, description=desc,
        design_measures=measures,
    )


def _assess_hazards(
    lat: float, lon: float, cluster: ClusterInfo,
) -> list[ClimateHazard]:
    return [
        _assess_cyclone(lat, lon),
        _assess_flood(lat, lon, cluster),
        _assess_drought(lat),
        _assess_sea_level_rise(lat, lon),
        _assess_heat_stress(cluster),
    ]


_HAZARD_RANK = {
    "very_high": 4,
    "high": 3,
    "moderate": 2,
    "low": 1,
    "negligible": 0,
}


def _overall_hazard_level(hazards: list[ClimateHazard]) -> str:
    if not hazards:
        return "low"
    max_rank = max(_HAZARD_RANK.get(h.level, 0) for h in hazards)
    high_count = sum(1 for h in hazards if _HAZARD_RANK.get(h.level, 0) >= 3)

    if max_rank >= 4 or high_count >= 2:
        return "very_high"
    if max_rank >= 3:
        return "high"
    if max_rank >= 2:
        return "moderate"
    return "low"


def _design_resilience_measures(hazards: list[ClimateHazard]) -> list[str]:
    """Deduplicated set of design measures from all hazard assessments."""
    seen: set[str] = set()
    measures: list[str] = []
    for h in hazards:
        for m in h.design_measures:
            if m not in seen and not m.startswith("No ") and not m.startswith("Standard "):
                seen.add(m)
                measures.append(m)
    return measures


# ── Climate finance eligibility ────────────────────────────────────

def _climate_finance_eligibility(
    carbon: CarbonAssessment,
    cluster: ClusterInfo,
    sizing: SystemSizing,
    annual_energy_kwh: float,
    hazards: list[ClimateHazard],
) -> list[ClimateFinanceEligibility]:
    instruments: list[ClimateFinanceEligibility] = []

    # Green Climate Fund
    gcf = _assess_gcf(cluster, sizing, annual_energy_kwh, hazards)
    instruments.append(gcf)

    # Adaptation Fund
    af = _assess_adaptation_fund(cluster, hazards)
    instruments.append(af)

    # Carbon Market (reference existing assessment)
    market_value = carbon.npv_carbon_revenue.get("market", 0.0)
    instruments.append(ClimateFinanceEligibility(
        instrument="Carbon Market (Article 6 / VCM)",
        eligible=carbon.annual_emission_reductions_tco2e > 0,
        rationale=(
            f"Project generates {carbon.annual_emission_reductions_tco2e:.1f} "
            f"tCO2e/yr under {carbon.recommended_methodology}. "
            f"See carbon assessment for detailed revenue scenarios."
        ),
        estimated_value_usd=market_value,
    ))

    # Bilateral climate finance (ENREDD+ / bilateral)
    bilateral = _assess_bilateral(cluster, carbon)
    instruments.append(bilateral)

    return instruments


def _assess_gcf(
    cluster: ClusterInfo,
    sizing: SystemSizing,
    annual_energy_kwh: float,
    hazards: list[ClimateHazard],
) -> ClimateFinanceEligibility:
    """Green Climate Fund eligibility (simplified heuristic)."""
    high_hazard = any(
        _HAZARD_RANK.get(h.level, 0) >= 3 for h in hazards
    )
    has_adaptation = cluster.has_health_facility or cluster.has_education_facility
    pop = cluster.population

    eligible = True
    rationale_parts: list[str] = [
        "Mozambique is a GCF-eligible developing country with an accredited "
        "national designated authority."
    ]

    if high_hazard:
        rationale_parts.append(
            "High climate hazard exposure strengthens the adaptation rationale."
        )
    if has_adaptation:
        rationale_parts.append(
            "Social infrastructure (health/education) provides a strong "
            "co-benefit narrative aligned with GCF investment criteria."
        )

    # Rough estimate: GCF results-based finance for energy access
    # ~USD 500 per tCO2e avoided or ~USD 500-800 per beneficiary for small projects
    est_value = 0.0
    if pop > 200:
        per_beneficiary = 300.0 if pop > 1000 else 500.0
        est_value = min(pop * per_beneficiary, sizing.pv_kwp * 1500)

    rationale_parts.append(
        f"Estimated value based on results-based finance benchmarks "
        f"for off-grid energy access in LDCs."
    )

    return ClimateFinanceEligibility(
        instrument="Green Climate Fund (GCF)",
        eligible=eligible,
        rationale=" ".join(rationale_parts),
        estimated_value_usd=round(est_value, 0),
    )


def _assess_adaptation_fund(
    cluster: ClusterInfo,
    hazards: list[ClimateHazard],
) -> ClimateFinanceEligibility:
    """Adaptation Fund eligibility assessment."""
    high_hazards = [
        h.hazard for h in hazards if _HAZARD_RANK.get(h.level, 0) >= 3
    ]
    eligible = len(high_hazards) > 0

    if eligible:
        hazard_names = ", ".join(high_hazards)
        rationale = (
            f"Project area faces high/very-high exposure to: {hazard_names}. "
            f"Mini-grid design incorporates climate-resilient features, "
            f"qualifying under the Adaptation Fund's mandate to finance "
            f"concrete adaptation projects in vulnerable developing countries."
        )
        est_value = round(cluster.population * 150.0, 0)
    else:
        rationale = (
            "Climate hazard exposure is moderate-to-low. The project may "
            "still qualify under the Adaptation Fund if bundled with a "
            "larger national programme, but standalone eligibility is weak."
        )
        est_value = 0.0

    return ClimateFinanceEligibility(
        instrument="Adaptation Fund",
        eligible=eligible,
        rationale=rationale,
        estimated_value_usd=est_value,
    )


def _assess_bilateral(
    cluster: ClusterInfo,
    carbon: CarbonAssessment,
) -> ClimateFinanceEligibility:
    """Bilateral climate finance (ENREDD+, KfW, SIDA, etc.)."""
    pop = cluster.population
    eligible = pop >= 100  # meaningful beneficiary count

    if eligible:
        rationale = (
            "Mozambique's ENREDD+ programme and bilateral partnerships "
            "(KfW, SIDA, DFID/FCDO, USAID Power Africa) actively fund "
            "off-grid renewable energy. This project's beneficiary count "
            f"({pop:,}) and emission reductions "
            f"({carbon.annual_emission_reductions_tco2e:.1f} tCO2e/yr) "
            "align with bilateral climate finance eligibility criteria. "
            "Engagement with ProEnergia and FUNAE improves access to "
            "concessional finance windows."
        )
        # Conservative estimate: bilateral grants ~USD 200-400/beneficiary
        est_value = round(pop * 250.0, 0)
    else:
        rationale = (
            "Small beneficiary population may limit bilateral finance "
            "interest as a standalone project. Consider programme-level "
            "bundling across multiple sites."
        )
        est_value = 0.0

    return ClimateFinanceEligibility(
        instrument="Bilateral Climate Finance (ENREDD+ / bilateral)",
        eligible=eligible,
        rationale=rationale,
        estimated_value_usd=est_value,
    )


def _climate_finance_score(
    instruments: list[ClimateFinanceEligibility],
) -> str:
    eligible_count = sum(1 for i in instruments if i.eligible)
    total_value = sum(i.estimated_value_usd for i in instruments)

    if eligible_count >= 3 and total_value > 100_000:
        return "high"
    if eligible_count >= 2 and total_value > 25_000:
        return "medium"
    return "low"
