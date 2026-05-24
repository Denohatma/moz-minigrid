from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from app.schemas.site import ClusterInfo
from app.schemas.analysis import (
    SystemSizing,
    ProtectedAreaCheck,
    ESSScreening,
)

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

# ── Haversine helper ───────────────────────────────────────────────

EARTH_RADIUS_KM = 6371.0


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two points."""
    rlat1, rlon1 = math.radians(lat1), math.radians(lon1)
    rlat2, rlon2 = math.radians(lat2), math.radians(lon2)
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# ── Protected areas (name, lat, lon, buffer_radius_km) ─────────────

PROTECTED_AREAS = [
    ("Gorongosa National Park", -18.97, 34.35, 50),
    ("Niassa Reserve", -12.50, 37.50, 80),
    ("Bazaruto Archipelago", -21.65, 35.47, 30),
    ("Limpopo National Park", -23.00, 31.50, 40),
    ("Quirimbas National Park", -12.30, 40.50, 40),
    ("Marromeu Reserve", -18.50, 35.50, 30),
    ("Chimanimani", -19.72, 33.47, 20),
]


# ── Main screening function ────────────────────────────────────────

def screen_ess(
    cluster: ClusterInfo,
    sizing: SystemSizing,
    latitude: float,
    longitude: float,
) -> ESSScreening:
    """Perform Environmental and Social Safeguards screening per Mozambique Decree 54/2015."""

    warnings: list[str] = []

    # 1. Protected area / biodiversity screening
    pa_checks = _check_protected_areas(latitude, longitude)
    biodiversity_sensitivity = _rate_biodiversity(pa_checks)

    # 2. Resettlement screening
    land_ha = _estimate_land_requirement(sizing)
    pop_density = cluster.population / cluster.area_km2 if cluster.area_km2 > 0 else 0
    phys_risk = _physical_displacement_risk(pop_density, land_ha, sizing.lv_line_km)
    econ_risk = _economic_displacement_risk(cluster, land_ha)
    resettle_risk = _combined_resettlement_risk(phys_risk, econ_risk)
    resettle_notes = _resettlement_notes(phys_risk, econ_risk, pop_density, cluster)

    # 3. ESIA category (depends on biodiversity + resettlement results)
    location_sensitive = biodiversity_sensitivity == "high" or resettle_risk == "high"
    sensitive_zone = biodiversity_sensitivity != "low"
    esia_cat, esia_rationale = _classify_esia(
        sizing.pv_kwp, location_sensitive, sensitive_zone, resettle_risk,
    )
    esia_reqs = _esia_requirements(esia_cat)

    # 4. Labour & community H&S
    elevation = cluster.elevation_m or 0.0
    labour_risks = _labour_safety_risks(sizing, elevation)
    community_risks = _community_safety_risks(
        sizing, cluster.has_health_facility, cluster.has_education_facility,
    )

    # 5. Stakeholder engagement
    stakeholders = _stakeholder_groups(esia_cat, cluster)
    consultations = _consultation_requirements(esia_cat)

    # 6. GRM
    grm = _grievance_mechanism(esia_cat)

    # 7. GESI
    gesi = _gesi_considerations(cluster)
    womens = _womens_empowerment(cluster)
    inclusion = _inclusion_measures(cluster)

    # 8. Biodiversity notes
    bio_notes = _biodiversity_notes(pa_checks, biodiversity_sensitivity)

    # Overall risk
    overall = _overall_risk(esia_cat, biodiversity_sensitivity, resettle_risk)

    # Recommended actions
    actions = _recommended_actions(
        esia_cat, biodiversity_sensitivity, resettle_risk, overall, warnings,
    )

    # Warnings
    if sizing.pv_kwp > 500:
        warnings.append(
            "System exceeds 500 kWp — full EIA with public consultation likely required."
        )
    if biodiversity_sensitivity == "high":
        warnings.append(
            "Site is within or very close to a protected area. Consult ANAC (National "
            "Administration of Conservation Areas) before proceeding."
        )
    if resettle_risk in ("high", "moderate"):
        warnings.append(
            "Resettlement risk is non-trivial. A Resettlement Action Plan (RAP) or "
            "Abbreviated RAP may be required."
        )

    return ESSScreening(
        esia_category=esia_cat,
        esia_rationale=esia_rationale,
        esia_requirements=esia_reqs,
        biodiversity_sensitivity=biodiversity_sensitivity,
        protected_area_checks=pa_checks,
        biodiversity_notes=bio_notes,
        resettlement_risk=resettle_risk,
        physical_displacement_risk=phys_risk,
        economic_displacement_risk=econ_risk,
        resettlement_notes=resettle_notes,
        estimated_land_requirement_ha=round(land_ha, 3),
        labour_safety_risks=labour_risks,
        community_safety_risks=community_risks,
        stakeholder_groups=stakeholders,
        consultation_requirements=consultations,
        grievance_mechanism=grm,
        gesi_considerations=gesi,
        womens_empowerment_opportunities=womens,
        inclusion_measures=inclusion,
        overall_ess_risk=overall,
        recommended_actions=actions,
        warnings=warnings,
    )


# ── Protected area checks ─────────────────────────────────────────

def _check_protected_areas(lat: float, lon: float) -> list[ProtectedAreaCheck]:
    checks: list[ProtectedAreaCheck] = []
    for name, pa_lat, pa_lon, buffer_km in PROTECTED_AREAS:
        dist = _haversine(lat, lon, pa_lat, pa_lon)
        in_buffer = dist <= buffer_km
        if dist <= buffer_km:
            sensitivity = "high"
        elif dist <= buffer_km * 1.5:
            sensitivity = "moderate"
        else:
            sensitivity = "low"
        checks.append(ProtectedAreaCheck(
            area_name=name,
            distance_km=round(dist, 1),
            buffer_zone=in_buffer,
            sensitivity=sensitivity,
        ))
    checks.sort(key=lambda c: c.distance_km)
    return checks


def _rate_biodiversity(checks: list[ProtectedAreaCheck]) -> str:
    sensitivities = [c.sensitivity for c in checks]
    if "high" in sensitivities:
        return "high"
    if "moderate" in sensitivities:
        return "moderate"
    return "low"


def _biodiversity_notes(checks: list[ProtectedAreaCheck], sensitivity: str) -> str:
    nearest = checks[0] if checks else None
    if sensitivity == "high" and nearest:
        return (
            f"Site is within the buffer zone of {nearest.area_name} "
            f"({nearest.distance_km} km). A biodiversity impact assessment is required. "
            "Consult ANAC and DINAB for species and habitat data. Avoid clearing "
            "indigenous vegetation and minimise footprint."
        )
    if sensitivity == "moderate" and nearest:
        return (
            f"Site is within the extended influence zone of {nearest.area_name} "
            f"({nearest.distance_km} km). A biodiversity baseline survey is recommended. "
            "Screen for critically endangered species and Important Bird Areas."
        )
    return (
        "No major protected areas in close proximity. Standard environmental management "
        "measures apply. Screen for locally significant habitats and watercourses."
    )


# ── ESIA classification (Decree 54/2015) ──────────────────────────

def _classify_esia(
    pv_kwp: float,
    location_sensitive: bool,
    sensitive_zone: bool,
    resettle_risk: str,
) -> tuple[str, str]:
    """Classify per Mozambique Decree 54/2015 Annex I-IV."""

    # Category A: large installations in protected areas (unlikely for mini-grids)
    if pv_kwp > 500 and location_sensitive:
        return "A", (
            f"System capacity ({pv_kwp:.0f} kWp) exceeds 500 kW and site is in a "
            "sensitive location (protected area or high resettlement risk). "
            "Full EIA with public hearing required per Decree 54/2015 Annex I."
        )

    # Category B+: >500 kW or in sensitive zone
    if pv_kwp > 500:
        return "B+", (
            f"System capacity ({pv_kwp:.0f} kWp) exceeds 500 kW. "
            "Full EIA with public consultation required per Decree 54/2015 Annex II."
        )
    if sensitive_zone and pv_kwp > 100:
        return "B+", (
            f"System capacity ({pv_kwp:.0f} kWp) is 100-500 kW range and site is "
            "within a sensitive ecological zone. Full EIA with public consultation "
            "required per Decree 54/2015 Annex II."
        )

    # Category B: 100-500 kW, or near sensitive areas
    if pv_kwp >= 100:
        return "B", (
            f"System capacity ({pv_kwp:.0f} kWp) is in the 100-500 kW range. "
            "Simplified EIA required per Decree 54/2015 Annex III."
        )
    if location_sensitive:
        return "B", (
            f"System capacity ({pv_kwp:.0f} kWp) is below 100 kW but site is in a "
            "sensitive location (protected area proximity or resettlement risk). "
            "Simplified EIA required per Decree 54/2015 Annex III."
        )
    if resettle_risk == "moderate":
        return "B", (
            f"System capacity ({pv_kwp:.0f} kWp) is below 100 kW but moderate "
            "resettlement risk has been identified. Simplified EIA required."
        )

    # Category C: <100 kW, no protected areas, no resettlement
    return "C", (
        f"System capacity ({pv_kwp:.0f} kWp) is below 100 kW with no protected area "
        "proximity and negligible resettlement risk. Simplified environmental form "
        "(Ficha de Informacao Ambiental Simplificada) per Decree 54/2015 Annex IV."
    )


def _esia_requirements(category: str) -> list[str]:
    base = [
        "Environmental Pre-assessment Form (Ficha de Informacao Ambiental Preliminar)",
        "Environmental licence application to DPTADER (Provincial Directorate)",
    ]
    if category == "C":
        return base + [
            "Simplified Environmental Form (FIAS)",
            "Basic Environmental Management Plan (PGA Simplificado)",
            "Community notification (minimum)",
        ]
    if category == "B":
        return base + [
            "Simplified Environmental Impact Study (EAS)",
            "Environmental Management Plan (PGA)",
            "Stakeholder consultation report",
            "Terms of Reference approved by MTA/DPTADER",
        ]
    if category == "B+":
        return base + [
            "Full Environmental Impact Assessment (EIA)",
            "Environmental Management Plan (PGA)",
            "Public consultation with documented proceedings",
            "Terms of Reference approved by MTA",
            "Independent review by MTA-appointed committee",
        ]
    # Category A
    return base + [
        "Full Environmental Impact Assessment (EIA)",
        "Environmental Management Plan (PGA)",
        "Public hearing (Audiencia Publica) with formal notice",
        "Terms of Reference approved by MTA",
        "Independent review panel",
        "Post-EIA monitoring and audit programme",
        "Social Impact Assessment (SIA)",
    ]


# ── Resettlement screening ─────────────────────────────────────────

def _estimate_land_requirement(sizing: SystemSizing) -> float:
    """Estimate total land requirement in hectares.

    Approximation: ~0.01 km2 per kWp for PV + battery + balance of system,
    plus a 10-metre corridor per km of LV line.
    """
    pv_area_km2 = sizing.pv_kwp * 0.01  # km2
    line_corridor_km2 = sizing.lv_line_km * 0.01 * 0.001  # 10m wide corridor
    total_km2 = pv_area_km2 + line_corridor_km2
    return total_km2 * 100  # convert to hectares


def _physical_displacement_risk(
    pop_density: float, land_ha: float, lv_line_km: float,
) -> str:
    """Rate physical displacement risk based on population density and footprint."""
    # Footprint score: larger footprint = higher risk
    footprint_score = land_ha + lv_line_km * 0.5

    if pop_density > 1000 and footprint_score > 5:
        return "high"
    if pop_density > 500 and footprint_score > 2:
        return "moderate"
    if pop_density > 200 and footprint_score > 1:
        return "low"
    return "negligible"


def _economic_displacement_risk(cluster: ClusterInfo, land_ha: float) -> str:
    """Rate economic displacement risk based on agricultural area proximity."""
    ag_area = cluster.ag_area_ha or 0.0
    ag_value = cluster.ag_value_usd or 0.0

    if ag_area > 0 and land_ha > ag_area * 0.1:
        return "high"
    if ag_area > 0 and land_ha > ag_area * 0.05:
        return "moderate"
    if ag_area > 0 or ag_value > 0:
        return "low"
    return "negligible"


def _combined_resettlement_risk(phys: str, econ: str) -> str:
    ranking = {"high": 3, "moderate": 2, "low": 1, "negligible": 0}
    labels = {3: "high", 2: "moderate", 1: "low", 0: "negligible"}
    score = max(ranking.get(phys, 0), ranking.get(econ, 0))
    return labels[score]


def _resettlement_notes(
    phys: str, econ: str, pop_density: float, cluster: ClusterInfo,
) -> str:
    parts: list[str] = []

    if phys == "high":
        parts.append(
            f"High population density ({pop_density:.0f}/km2) combined with system "
            "footprint creates significant physical displacement risk. A full "
            "Resettlement Action Plan (RAP) is required."
        )
    elif phys == "moderate":
        parts.append(
            "Moderate physical displacement risk. An Abbreviated Resettlement Action "
            "Plan (ARAP) is recommended."
        )
    elif phys == "low":
        parts.append("Low physical displacement risk. Land-use agreements should suffice.")
    else:
        parts.append("Negligible physical displacement risk.")

    if econ in ("high", "moderate"):
        ag_ha = cluster.ag_area_ha or 0
        parts.append(
            f"Agricultural land ({ag_ha:.1f} ha) overlaps with project footprint. "
            "A livelihood restoration plan is required."
        )
    elif econ == "low":
        parts.append(
            "Some agricultural activity nearby. Crop compensation may be needed "
            "during construction."
        )

    return " ".join(parts)


# ── Labour & community safety ──────────────────────────────────────

def _labour_safety_risks(sizing: SystemSizing, elevation: float) -> list[str]:
    risks: list[str] = [
        "Electrical hazards during PV and inverter installation",
        "Manual handling injuries during panel and battery transport",
    ]
    if sizing.pv_kwp > 100:
        risks.append("Increased fall risk from elevated mounting structures for larger arrays")
    if sizing.battery_kwh_nominal > 100:
        risks.append(
            "Battery electrolyte handling and thermal runaway risk — "
            "fire suppression required on site"
        )
    if elevation > 1000:
        risks.append(
            "High-altitude terrain increases transport difficulty and "
            "weather-related construction delays"
        )
    if sizing.lv_line_km > 5:
        risks.append(
            "Extended distribution network increases pole-erection and "
            "overhead line stringing hazards"
        )
    risks.append("Heat stress for outdoor workers (tropical climate)")
    risks.append(
        "Road safety risk for material transport, especially on unpaved rural roads"
    )
    return risks


def _community_safety_risks(
    sizing: SystemSizing,
    has_health: Optional[bool],
    has_education: Optional[bool],
) -> list[str]:
    risks: list[str] = [
        "Electrical safety — overhead LV lines and consumer connections",
        "Battery storage chemical and fire hazard requiring secure fencing",
    ]
    if has_education:
        risks.append(
            "Education facility nearby — additional safety measures required for "
            "distribution lines and construction traffic near school"
        )
    if has_health:
        risks.append(
            "Health facility nearby — ensure uninterrupted power during construction "
            "if facility has existing supply; coordinate timing"
        )
    if sizing.pv_kwp > 200:
        risks.append("Larger installation footprint increases exposure to construction dust and noise")
    risks.append(
        "Construction traffic on community roads — traffic management plan required"
    )
    risks.append(
        "Post-commissioning electrical safety training for community members"
    )
    return risks


# ── Stakeholder engagement ─────────────────────────────────────────

def _stakeholder_groups(category: str, cluster: ClusterInfo) -> list[str]:
    groups = [
        "Community leaders (regulo, chefe do posto) and local elders",
        "District government (Servico Distrital de Actividades Economicas — SDAE)",
        "Provincial Directorate (DPTADER) for environmental licensing",
        "ARENE (Autoridade Reguladora de Energia) — energy regulator",
        "EDM (Electricidade de Mocambique) — national utility",
        "Affected households and landowners within project footprint",
    ]
    if category in ("A", "B+"):
        groups.extend([
            "Ministry of Land and Environment (MTA)",
            "National environmental NGOs (e.g., MICAIA Foundation, WWF Mozambique)",
            "Independent environmental review panel",
        ])
    if cluster.has_health_facility:
        groups.append("District health authority (SDSMAS)")
    if cluster.has_education_facility:
        groups.append("District education authority (SDEJT)")
    if cluster.ag_area_ha and cluster.ag_area_ha > 0:
        groups.append("Agricultural cooperatives and farmer associations")
    groups.append("Women's groups and gender-focused CSOs")
    return groups


def _consultation_requirements(category: str) -> list[str]:
    if category == "C":
        return [
            "Community notification meeting (minimum 1 session)",
            "Written notification posted at district administration office",
            "Documentation of community feedback and responses",
        ]
    if category == "B":
        return [
            "Formal stakeholder identification and mapping exercise",
            "Minimum 2 community consultation meetings with documented minutes",
            "Written notification in local language (Portuguese and local language)",
            "21-day public comment period for the Simplified EIA report",
            "Stakeholder engagement report submitted with EIA documentation",
            "Feedback and response documentation",
        ]
    # B+ or A
    reqs = [
        "Formal stakeholder identification, mapping, and engagement plan",
        "Minimum 3 community consultation meetings at different project stages",
        "Public notice in national newspaper and posted at district/provincial level",
        "30-day public comment period for the full EIA report",
    ]
    if category == "A":
        reqs.append(
            "Public hearing (Audiencia Publica) organised by MTA with formal notification "
            "(minimum 15 days advance notice)"
        )
    else:
        reqs.append(
            "Public consultation session documented with independent facilitator"
        )
    reqs.extend([
        "Written submissions in Portuguese and relevant local language",
        "Comprehensive stakeholder engagement report",
        "Ongoing grievance mechanism established before construction",
    ])
    return reqs


# ── Grievance Redress Mechanism ────────────────────────────────────

def _grievance_mechanism(category: str) -> dict:
    grm: dict = {
        "structure": {
            "level_1": "On-site community liaison officer receives and logs complaints",
            "level_2": "Project manager reviews unresolved complaints within 7 days",
            "level_3": "District-level mediation committee (includes community and government representatives)",
            "level_4": "Provincial-level appeal through DPTADER or formal legal channels",
        },
        "channels": [
            "In-person at the community liaison office (on-site)",
            "Dedicated phone line / SMS hotline",
            "Written complaint box at project site and community meeting point",
            "Through community leaders (regulo) as intermediary",
        ],
        "timelines": {
            "acknowledgement": "Within 48 hours of receipt",
            "initial_response": "Within 7 working days",
            "resolution_target": "Within 30 calendar days",
            "escalation": "Automatic escalation if unresolved after 30 days",
        },
        "documentation": [
            "Grievance register maintained with unique tracking numbers",
            "Quarterly grievance summary reports",
            "All resolutions documented and communicated to complainant",
        ],
    }
    if category in ("A", "B+"):
        grm["additional_requirements"] = [
            "Independent grievance review panel for Category A/B+ projects",
            "Publicly accessible grievance log (anonymised)",
            "Semi-annual grievance audit by independent party",
        ]
    return grm


# ── GESI (Gender, Equality, Social Inclusion) ─────────────────────

def _gesi_considerations(cluster: ClusterInfo) -> list[str]:
    considerations: list[str] = [
        "Women typically bear disproportionate energy burden for cooking, water "
        "heating, and agro-processing — ensure demand assessment captures gendered "
        "energy needs",
        "Consultation scheduling must accommodate women's time constraints "
        "(avoid early morning and meal preparation times)",
        "Ensure women are represented in community consultation (minimum 40% target)",
    ]

    urban_label = {0: "rural", 1: "peri-urban", 2: "urban"}.get(cluster.is_urban, "rural")
    if urban_label == "rural":
        considerations.append(
            "Rural women face greater barriers to electricity access — prioritise "
            "affordable connection fees and flexible payment plans"
        )
        considerations.append(
            "Address cultural barriers to women's participation in energy "
            "governance and decision-making"
        )
    else:
        considerations.append(
            "Peri-urban/urban women have higher productive use potential — "
            "support women-led micro-enterprise connections"
        )

    if cluster.has_education_facility:
        considerations.append(
            "School electrification benefits girls' education outcomes "
            "(evening study hours, digital learning)"
        )
    if cluster.has_health_facility:
        considerations.append(
            "Health facility electrification improves maternal health services "
            "(lighting for deliveries, vaccine cold chain)"
        )

    return considerations


def _womens_empowerment(cluster: ClusterInfo) -> list[str]:
    opportunities = [
        "Targeted productive use connections for women-led businesses "
        "(hairdressing, tailoring, food processing, cold storage)",
        "Women-focused financial literacy and business development training",
        "Preferential tariff or connection subsidy for women-headed households",
        "Women's representation on mini-grid management committee (minimum 40%)",
    ]

    urban_label = {0: "rural", 1: "peri-urban", 2: "urban"}.get(cluster.is_urban, "rural")
    if urban_label == "rural":
        opportunities.extend([
            "Agricultural processing equipment for women farmer groups "
            "(milling, drying, irrigation pumping)",
            "Solar-powered water pumping to reduce women's water-fetching burden",
        ])
    else:
        opportunities.extend([
            "Phone and device charging stations operated by women entrepreneurs",
            "Digital literacy training leveraging electricity access",
        ])

    if cluster.ag_area_ha and cluster.ag_area_ha > 0:
        opportunities.append(
            "Electrified agro-processing for women's cooperatives "
            "(cashew processing, rice milling)"
        )

    return opportunities


def _inclusion_measures(cluster: ClusterInfo) -> list[str]:
    measures = [
        "Accessible tariff structure with lifeline tariff for lowest-income households",
        "Connection fee payment plans (minimum 6 months instalment option)",
        "Information materials in local languages (Emakhuwa, Sena, Changana "
        "as appropriate to region)",
        "Disability-accessible design for meter boxes and payment points",
        "Youth employment and apprenticeship opportunities during construction "
        "and operations",
        "Engagement with vulnerable groups: elderly, disabled, female-headed "
        "households, child-headed households",
    ]

    urban_label = {0: "rural", 1: "peri-urban", 2: "urban"}.get(cluster.is_urban, "rural")
    if urban_label == "rural":
        measures.append(
            "Mobile money payment option for households far from payment points"
        )
    measures.append(
        "Community awareness campaigns on electricity safety and efficient use"
    )
    return measures


# ── Overall risk & recommendations ─────────────────────────────────

def _overall_risk(
    esia_cat: str, biodiversity: str, resettlement: str,
) -> str:
    """Derive overall ESS risk from component ratings."""
    high_flags = 0
    if esia_cat == "A":
        high_flags += 2
    elif esia_cat == "B+":
        high_flags += 1
    if biodiversity == "high":
        high_flags += 1
    if resettlement == "high":
        high_flags += 1

    if high_flags >= 2:
        return "high"
    if high_flags == 1:
        return "substantial"
    if esia_cat == "B" or biodiversity == "moderate" or resettlement == "moderate":
        return "moderate"
    return "low"


def _recommended_actions(
    esia_cat: str,
    biodiversity: str,
    resettlement: str,
    overall: str,
    warnings: list[str],
) -> list[str]:
    actions: list[str] = []

    # ESIA-related
    if esia_cat in ("A", "B+"):
        actions.append(
            "Engage a licensed Mozambican environmental consultant to prepare the "
            "full EIA and submit to MTA"
        )
    elif esia_cat == "B":
        actions.append(
            "Engage a licensed Mozambican environmental consultant to prepare the "
            "Simplified EIA (EAS) and submit to DPTADER"
        )
    else:
        actions.append(
            "Complete the Simplified Environmental Form (FIAS) and submit to "
            "DPTADER for environmental licence"
        )

    # Biodiversity
    if biodiversity == "high":
        actions.append(
            "Conduct a biodiversity baseline survey and consult ANAC on "
            "protected area management plan compatibility"
        )
    elif biodiversity == "moderate":
        actions.append(
            "Conduct an ecological screening survey and document any "
            "sensitive habitats or species"
        )

    # Resettlement
    if resettlement == "high":
        actions.append(
            "Prepare a full Resettlement Action Plan (RAP) per IFC PS5 "
            "and Mozambique Land Law"
        )
    elif resettlement == "moderate":
        actions.append(
            "Prepare an Abbreviated Resettlement Action Plan (ARAP) and "
            "livelihood restoration framework"
        )
    elif resettlement == "low":
        actions.append(
            "Negotiate voluntary land-use agreements with affected landowners "
            "and document consent"
        )

    # Standard actions
    actions.extend([
        "Develop an Environmental and Social Management Plan (ESMP) before construction",
        "Establish the Grievance Redress Mechanism and appoint a community liaison officer",
        "Conduct stakeholder consultation and document proceedings before licence application",
        "Integrate GESI action plan into project design and operations manual",
    ])

    if overall in ("high", "substantial"):
        actions.append(
            "Engage an independent environmental and social monitor for "
            "construction and first year of operations"
        )

    return actions
