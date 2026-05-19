from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.site import ClusterInfo
from app.schemas.analysis import (
    DemandEstimate,
    FinancialResults,
    GridRiskAssessment,
    SystemSizing,
)

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"


# ── Output models ──────────────────────────────────────────────────

class RiskItem(BaseModel):
    category: str = Field(description="technical, commercial, regulatory, security, social, climate, currency, political")
    sub_risk: str = Field(description="Specific risk within category")
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    risk_score: int = Field(description="Likelihood x Impact")
    risk_level: str = Field(description="critical (>16), high (12-16), medium (6-11), low (1-5)")
    description: str
    mitigation: list[str]
    allocation: str = Field(description="concessionaire, public_partner, shared, risk_instrument")


class RiskAnalysis(BaseModel):
    risks: list[RiskItem]
    overall_risk_score: float
    overall_risk_level: str = Field(description="critical, high, medium, low")
    top_risks: list[str] = Field(description="Top 3 risk descriptions")
    risk_allocation_summary: dict = Field(description="Mapping of allocation category to list of risk descriptions")
    mitigation_investment_usd: float = Field(description="Estimated cost of mitigation measures")
    warnings: list[str] = Field(default_factory=list)


# ── Category weights for overall score ─────────────────────────────

CATEGORY_WEIGHTS = {
    "technical": 0.15,
    "commercial": 0.20,
    "regulatory": 0.10,
    "security": 0.15,
    "social": 0.10,
    "climate": 0.10,
    "currency": 0.10,
    "political": 0.10,
}


# ── Public entry point ─────────────────────────────────────────────

def analyze_risks(
    cluster: ClusterInfo,
    financial: FinancialResults,
    sizing: SystemSizing,
    grid_risk: GridRiskAssessment,
    demand: DemandEstimate,
) -> RiskAnalysis:
    """Comprehensive 8-category risk analysis for ARENE concession data sheets.

    Evaluates technical, commercial, regulatory, security, social, climate,
    currency and political risks using site-level indicators, financial
    results, and Mozambique-specific context.
    """
    latitude = _abs_lat(cluster)
    longitude = _est_lon(cluster)
    risks: list[RiskItem] = []

    # 1. Technical risks
    risks.extend(_assess_technical_risks(cluster, sizing, demand))

    # 2. Commercial / demand risks
    risks.extend(_assess_commercial_risks(cluster, financial, demand))

    # 3. Regulatory risks
    risks.extend(_assess_regulatory_risks())

    # 4. Security risks
    risks.extend(_assess_security_risks(cluster, latitude, longitude))

    # 5. Social risks
    risks.extend(_assess_social_risks(cluster, sizing, demand))

    # 6. Climate risks
    risks.extend(_assess_climate_risks(cluster, latitude, longitude))

    # 7. Currency risks
    risks.extend(_assess_currency_risks(financial))

    # 8. Political risks
    risks.extend(_assess_political_risks())

    # ── Overall score (weighted average of category max scores) ────
    cat_max: dict[str, int] = {}
    for r in risks:
        cat_max[r.category] = max(cat_max.get(r.category, 0), r.risk_score)

    weighted_sum = 0.0
    weight_sum = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        score = cat_max.get(cat, 5)
        weighted_sum += score * weight
        weight_sum += weight

    overall_score = round(weighted_sum / weight_sum, 1) if weight_sum > 0 else 0.0
    overall_level = _level_from_score(overall_score)

    # ── Top 3 risks ────────────────────────────────────────────────
    sorted_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)
    top_risks = [
        f"{r.category}/{r.sub_risk}: {r.description}" for r in sorted_risks[:3]
    ]

    # ── Risk allocation summary ────────────────────────────────────
    allocation_map: dict[str, list[str]] = {
        "concessionaire": [],
        "public_partner": [],
        "shared": [],
        "risk_instrument": [],
    }
    for r in risks:
        key = r.allocation
        label = f"{r.category}/{r.sub_risk}"
        allocation_map.setdefault(key, []).append(label)

    # ── Mitigation investment estimate ─────────────────────────────
    capex = financial.total_capex_usd
    mitigation_usd = _estimate_mitigation_cost(risks, capex, cluster)

    # ── Warnings ───────────────────────────────────────────────────
    warnings: list[str] = []
    critical_items = [r for r in risks if r.risk_level == "critical"]
    if critical_items:
        warnings.append(
            f"{len(critical_items)} critical risk(s) identified — project may require "
            "additional risk transfer instruments before financial close."
        )
    if overall_level in ("critical", "high"):
        warnings.append(
            "Overall risk profile is elevated. Recommend enhanced due diligence "
            "and DFI guarantee structures."
        )
    security_high = any(
        r.category == "security" and r.risk_level in ("critical", "high") for r in risks
    )
    if security_high:
        warnings.append(
            "Security risk is high — consider conflict-sensitive project design "
            "and insurance requirements for northern Mozambique."
        )

    return RiskAnalysis(
        risks=risks,
        overall_risk_score=overall_score,
        overall_risk_level=overall_level,
        top_risks=top_risks,
        risk_allocation_summary=allocation_map,
        mitigation_investment_usd=round(mitigation_usd, 0),
        warnings=warnings,
    )


# ── 1. Technical Risk ──────────────────────────────────────────────

def _assess_technical_risks(
    cluster: ClusterInfo,
    sizing: SystemSizing,
    demand: DemandEstimate,
) -> list[RiskItem]:
    items: list[RiskItem] = []
    travel = cluster.travel_time_hrs or 0
    pv_kwp = sizing.pv_kwp
    is_remote = travel > 4
    is_large = pv_kwp > 200

    # Equipment reliability
    equip_l = 2
    equip_i = 3
    if is_large:
        equip_l += 1
    if is_remote:
        equip_i += 1
    equip_l = min(equip_l, 5)
    equip_i = min(equip_i, 5)
    items.append(RiskItem(
        category="technical",
        sub_risk="equipment_reliability",
        likelihood=equip_l,
        impact=equip_i,
        risk_score=equip_l * equip_i,
        risk_level=_level_from_score(equip_l * equip_i),
        description=(
            f"Equipment failure risk for {pv_kwp:.0f} kWp system with LFP battery storage. "
            f"{'Remote location (>{travel:.1f}h travel) increases response time for repairs. ' if is_remote else ''}"
            f"{'Larger system complexity increases failure modes.' if is_large else ''}"
        ),
        mitigation=[
            "Specify Tier-1 modules and IEC 62619-certified LFP batteries",
            "Include 2-year EPC defect liability period with performance guarantees",
            "Remote monitoring system with automated fault alerts",
            "Maintain critical spares inventory on-site (inverter boards, fuses, charge controllers)",
            "Establish service-level agreement with regional O&M provider",
        ],
        allocation="concessionaire",
    ))

    # Solar resource variability
    solar_l = 2
    solar_i = 2
    items.append(RiskItem(
        category="technical",
        sub_risk="solar_resource_variability",
        likelihood=solar_l,
        impact=solar_i,
        risk_score=solar_l * solar_i,
        risk_level=_level_from_score(solar_l * solar_i),
        description=(
            "Inter-annual solar resource variability of +/-5-10% around long-term mean. "
            "PVGIS satellite data (2005-2020) provides reasonable P50 estimate but "
            "no ground-measured validation is available at pre-feasibility stage."
        ),
        mitigation=[
            "Use P90 yield estimate for debt sizing (approx. 10% below P50)",
            "Size battery to compensate for 2-3 consecutive low-irradiance days",
            "Commission 6-month ground-based irradiance measurement before financial close",
        ],
        allocation="concessionaire",
    ))

    # Distribution network losses
    dist_l = 2
    dist_i = 2
    if demand.households > 300:
        dist_l = 3
        dist_i = 3
    items.append(RiskItem(
        category="technical",
        sub_risk="distribution_losses",
        likelihood=dist_l,
        impact=dist_i,
        risk_score=dist_l * dist_i,
        risk_level=_level_from_score(dist_l * dist_i),
        description=(
            f"LV distribution network serving {demand.households} connections. "
            "Losses estimated at 8% but may increase with network ageing, "
            "unplanned extensions, or illegal connections."
        ),
        mitigation=[
            "Use pre-paid smart meters to control losses and detect tampering",
            "Design network with adequate conductor sizing for 10-year demand growth",
            "Annual thermal imaging survey of connections and joints",
        ],
        allocation="concessionaire",
    ))

    return items


# ── 2. Commercial / Demand Risk ────────────────────────────────────

def _assess_commercial_risks(
    cluster: ClusterInfo,
    financial: FinancialResults,
    demand: DemandEstimate,
) -> list[RiskItem]:
    items: list[RiskItem] = []
    pop = cluster.population
    tier = demand.demand_tier
    rwi = cluster.mean_rwi
    is_urban = cluster.is_urban >= 1

    # Demand forecast uncertainty
    demand_l = 4 if tier <= 2 else (3 if tier == 3 else 2)
    demand_i = 4 if pop < 200 else (3 if pop < 500 else 2)
    if pop < 200:
        demand_l = min(demand_l + 1, 5)
    items.append(RiskItem(
        category="commercial",
        sub_risk="demand_forecast",
        likelihood=demand_l,
        impact=demand_i,
        risk_score=demand_l * demand_i,
        risk_level=_level_from_score(demand_l * demand_i),
        description=(
            f"Demand estimated at Tier {tier} for {pop:,} people ({demand.households} connections). "
            f"{'Low-tier demand forecasts have high uncertainty (+/-40%) at pre-feasibility. ' if tier <= 2 else ''}"
            f"{'Small population increases per-connection forecast variance. ' if pop < 200 else ''}"
            "No field willingness-to-pay survey has been conducted."
        ),
        mitigation=[
            "Conduct household and enterprise demand/WTP survey before financial close",
            "Design modular system allowing phased capacity additions",
            "Include demand ramp-up assumptions (60% Year 1, growing 5%/year) in financial model",
            "Identify and pre-sign anchor load customers (schools, health centres, telecom towers)",
        ],
        allocation="shared",
    ))

    # Willingness to pay
    wtp_l = 3
    wtp_i = 4
    if rwi is not None and rwi > 0:
        wtp_l = 2
        wtp_i = 3
    elif rwi is not None and rwi < -0.5:
        wtp_l = 4
        wtp_i = 4
    if is_urban:
        wtp_l = max(wtp_l - 1, 1)
    items.append(RiskItem(
        category="commercial",
        sub_risk="willingness_to_pay",
        likelihood=wtp_l,
        impact=wtp_i,
        risk_score=wtp_l * wtp_i,
        risk_level=_level_from_score(wtp_l * wtp_i),
        description=(
            f"Customer ability and willingness to pay at cost-reflective tariffs. "
            f"Mean RWI is {rwi:.2f}" + (" (below average wealth)." if rwi and rwi < 0 else " (above average wealth).") if rwi is not None else
            "No RWI data available — wealth level unknown."
        ) + (
            " Urban/peri-urban customers typically have higher willingness to pay."
            if is_urban else
            " Rural customers may prioritise basic lighting over higher-tier services."
        ),
        mitigation=[
            "Implement lifeline tariff block for basic consumption (first 10 kWh/month)",
            "Offer PAYGO or mobile-money pre-paid billing to reduce payment friction",
            "Structure tariff with cross-subsidy from productive/commercial users",
            "Apply for results-based financing to reduce required tariff level",
        ],
        allocation="shared",
    ))

    # Customer growth uncertainty
    growth_l = 3
    growth_i = 2
    items.append(RiskItem(
        category="commercial",
        sub_risk="customer_growth",
        likelihood=growth_l,
        impact=growth_i,
        risk_score=growth_l * growth_i,
        risk_level=_level_from_score(growth_l * growth_i),
        description=(
            "Connection ramp-up may be slower than modelled 60% Year 1 with "
            "5%/year growth. Household connection costs and internal wiring "
            "represent a barrier for lowest-income customers."
        ),
        mitigation=[
            "Offer connection fee financing (spread over 6-12 months)",
            "Partner with NGOs for productive-use equipment financing",
            "Include connection subsidies in grant financing structure",
        ],
        allocation="concessionaire",
    ))

    # Productive use uptake
    has_economic = (
        cluster.has_education_facility
        or cluster.has_health_facility
        or (cluster.max_ntl > 10)
        or (cluster.ag_area_ha and cluster.ag_area_ha > 0)
    )
    pu_l = 2 if has_economic else 4
    pu_i = 3
    items.append(RiskItem(
        category="commercial",
        sub_risk="productive_use_uptake",
        likelihood=pu_l,
        impact=pu_i,
        risk_score=pu_l * pu_i,
        risk_level=_level_from_score(pu_l * pu_i),
        description=(
            f"Productive use of energy is critical for financial viability. "
            f"{'Existing facilities (education/health) and agricultural activity suggest demand anchors. ' if has_economic else 'Limited evidence of existing economic activity — productive use development needed. '}"
            f"{'Agricultural area of {:.0f} ha may support agro-processing loads.'.format(cluster.ag_area_ha) if cluster.ag_area_ha and cluster.ag_area_ha > 0 else ''}"
        ),
        mitigation=[
            "Develop productive use promotion programme (milling, welding, cold storage, irrigation)",
            "Partner with agricultural cooperatives for anchor demand",
            "Include productive use equipment financing in project design",
            "Engage FUNAE/NGO productive use technical assistance programmes",
        ],
        allocation="shared",
    ))

    return items


# ── 3. Regulatory Risk ─────────────────────────────────────────────

def _assess_regulatory_risks() -> list[RiskItem]:
    items: list[RiskItem] = []

    # ARENE licensing delays
    items.append(RiskItem(
        category="regulatory",
        sub_risk="licensing_delays",
        likelihood=3,
        impact=3,
        risk_score=9,
        risk_level="medium",
        description=(
            "ARENE licensing and concession approval process for mini-grids is "
            "still maturing. Average processing times of 6-12 months reported, "
            "with potential for further delays due to institutional capacity constraints."
        ),
        mitigation=[
            "Begin pre-licensing engagement with ARENE early in project development",
            "Engage experienced local legal counsel familiar with ARENE procedures",
            "Prepare complete application package following 2023 concession regulation template",
            "Maintain regular follow-up with ARENE case officer",
        ],
        allocation="shared",
    ))

    # Tariff regulation changes
    items.append(RiskItem(
        category="regulatory",
        sub_risk="tariff_regulation",
        likelihood=3,
        impact=4,
        risk_score=12,
        risk_level="high",
        description=(
            "Tariff methodology under Decree 93/2021 allows cost-reflective pricing, "
            "but ARENE retains tariff review authority. Risk of tariff cap imposition "
            "or methodology change during concession period. Political pressure for "
            "tariff alignment with EDM grid tariffs (significantly below cost-reflective levels)."
        ),
        mitigation=[
            "Structure concession agreement with tariff adjustment formula indexed to inflation and FX",
            "Include tariff risk sharing mechanism with government/ARENE",
            "Advocate for regulatory predictability through sector associations (AMER)",
            "Design subsidy structure to bridge gap between affordable and cost-reflective tariff",
        ],
        allocation="shared",
    ))

    # Concession term uncertainty
    items.append(RiskItem(
        category="regulatory",
        sub_risk="concession_term",
        likelihood=2,
        impact=3,
        risk_score=6,
        risk_level="medium",
        description=(
            "Mini-grid concession terms under Mozambican law are typically 15-25 years. "
            "Uncertainty around renewal terms, end-of-concession asset transfer provisions, "
            "and conditions for early termination."
        ),
        mitigation=[
            "Negotiate clear concession extension provisions in initial agreement",
            "Include asset transfer valuation methodology in concession terms",
            "Structure financing to fully amortise within initial concession period",
        ],
        allocation="public_partner",
    ))

    # Grid interconnection regime
    items.append(RiskItem(
        category="regulatory",
        sub_risk="grid_interconnection",
        likelihood=2,
        impact=3,
        risk_score=6,
        risk_level="medium",
        description=(
            "No established regulatory framework for mini-grid integration when "
            "the national grid arrives. EDM may not honour existing concession rights. "
            "Compensation mechanisms for stranded assets are untested in Mozambique."
        ),
        mitigation=[
            "Include grid-arrival compensation clause in concession agreement",
            "Reference ESMAP best-practice framework for grid-arrival scenarios",
            "Design system with grid-forming inverter capable of future interconnection",
            "Monitor EDM grid extension plans quarterly",
        ],
        allocation="public_partner",
    ))

    return items


# ── 4. Security Risk ───────────────────────────────────────────────

def _assess_security_risks(
    cluster: ClusterInfo,
    latitude: float,
    longitude: float,
) -> list[RiskItem]:
    items: list[RiskItem] = []
    acled_events = cluster.total_incidents_50km
    security_label = cluster.security_risk or "unknown"

    # Insurgency zone heuristic: northern Cabo Delgado
    # Above -14 latitude and east of 39 longitude → insurgency corridor
    in_insurgency_zone = latitude < 14 and longitude > 39

    # Armed conflict / insurgency
    if in_insurgency_zone or security_label == "high":
        conflict_l = 4
        conflict_i = 5
    elif acled_events and acled_events > 10:
        conflict_l = 3
        conflict_i = 4
    elif acled_events and acled_events > 3:
        conflict_l = 2
        conflict_i = 3
    else:
        conflict_l = 1
        conflict_i = 3

    items.append(RiskItem(
        category="security",
        sub_risk="armed_conflict",
        likelihood=conflict_l,
        impact=conflict_i,
        risk_score=conflict_l * conflict_i,
        risk_level=_level_from_score(conflict_l * conflict_i),
        description=(
            f"{'Site is in or near the Cabo Delgado insurgency-affected corridor. ' if in_insurgency_zone else ''}"
            f"{'Security risk classified as {}.'.format(security_label.upper()) if security_label != 'unknown' else ''} "
            f"{'ACLED data shows {} security incidents within 50 km.'.format(acled_events) if acled_events else 'No ACLED incident data available.'} "
            "Armed conflict can cause total project loss, staff displacement, "
            "and extended operational shutdown."
        ),
        mitigation=(
            [
                "Obtain political risk insurance covering conflict/civil unrest (MIGA, ATI, or private)",
                "Develop conflict-sensitive project design with community ownership component",
                "Establish security protocol with local authorities and community leaders",
                "Install perimeter fencing, CCTV, and 24/7 site security",
                "Maintain evacuation and business continuity plan",
            ] if conflict_l >= 3 else [
                "Standard site security measures (fencing, lighting, guard)",
                "Community engagement to build local ownership and protection",
                "Monitor security situation through ACLED and local intelligence",
            ]
        ),
        allocation="risk_instrument" if conflict_l >= 3 else "concessionaire",
    ))

    # Equipment theft
    travel = cluster.travel_time_hrs or 0
    is_remote = travel > 3
    theft_l = 3 if is_remote else 2
    theft_i = 3
    if in_insurgency_zone:
        theft_l = min(theft_l + 1, 5)
    items.append(RiskItem(
        category="security",
        sub_risk="equipment_theft",
        likelihood=theft_l,
        impact=theft_i,
        risk_score=theft_l * theft_i,
        risk_level=_level_from_score(theft_l * theft_i),
        description=(
            f"Risk of theft of PV panels, batteries, copper cabling, and meters. "
            f"{'Remote location ({:.1f}h travel) increases vulnerability. '.format(travel) if is_remote else ''}"
            "Battery and cable theft is the most commonly reported incident "
            "for mini-grids across Sub-Saharan Africa."
        ),
        mitigation=[
            "Hire local community members as site security guards",
            "Use anti-theft module mounting (tamper-proof bolts, welded clamps)",
            "Install battery in locked, reinforced container",
            "Use aluminium conductors instead of copper where feasible",
            "Comprehensive asset insurance covering theft and vandalism",
        ],
        allocation="concessionaire",
    ))

    return items


# ── 5. Social Risk ─────────────────────────────────────────────────

def _assess_social_risks(
    cluster: ClusterInfo,
    sizing: SystemSizing,
    demand: DemandEstimate,
) -> list[RiskItem]:
    items: list[RiskItem] = []
    pop = cluster.population
    has_facilities = cluster.has_education_facility or cluster.has_health_facility
    pv_kwp = sizing.pv_kwp

    # Community acceptance
    accept_l = 2
    accept_i = 3
    if pop < 150:
        accept_l = 3
    if pv_kwp > 150:
        accept_i = 4
    items.append(RiskItem(
        category="social",
        sub_risk="community_acceptance",
        likelihood=accept_l,
        impact=accept_i,
        risk_score=accept_l * accept_i,
        risk_level=_level_from_score(accept_l * accept_i),
        description=(
            f"Community acceptance risk for {pv_kwp:.0f} kWp installation serving "
            f"{pop:,} people. Potential concerns include tariff affordability, "
            f"equitable access, and expectations management. "
            f"{'Presence of education/health facilities provides institutional engagement points.' if has_facilities else 'No anchor institutions identified for community engagement.'}"
        ),
        mitigation=[
            "Conduct community consultation before project design finalisation",
            "Establish community liaison committee with elected representatives",
            "Implement transparent tariff communication programme",
            "Prioritise local hiring for construction and O&M",
        ],
        allocation="shared",
    ))

    # Land access / tenure
    land_l = 3
    land_i = 4
    # Larger systems need more land, increasing risk
    land_area_m2 = pv_kwp * 10  # rough: ~10 m2 per kWp
    if land_area_m2 < 500:
        land_l = 2
    items.append(RiskItem(
        category="social",
        sub_risk="land_access",
        likelihood=land_l,
        impact=land_i,
        risk_score=land_l * land_i,
        risk_level=_level_from_score(land_l * land_i),
        description=(
            "Land access under Mozambique's DUAT (Direito de Uso e Aproveitamento da Terra) "
            "system requires community consultation and government approval. "
            f"Estimated land requirement ~{land_area_m2:,.0f} m2 for PV array and powerhouse. "
            "Process typically takes 3-6 months but can be delayed by competing claims "
            "or community objections."
        ),
        mitigation=[
            "Initiate DUAT process early — engage district land administration (SPGC)",
            "Conduct community land consultation per Lei de Terras (Law 19/97)",
            "Document existing land use and any competing claims",
            "Consider co-location with community facilities to reduce land requirements",
            "Obtain provisional DUAT before committing significant project expenditure",
        ],
        allocation="public_partner",
    ))

    # Stakeholder conflict
    conflict_l = 2
    conflict_i = 2
    if pop > 1000:
        conflict_l = 3
    items.append(RiskItem(
        category="social",
        sub_risk="stakeholder_conflict",
        likelihood=conflict_l,
        impact=conflict_i,
        risk_score=conflict_l * conflict_i,
        risk_level=_level_from_score(conflict_l * conflict_i),
        description=(
            "Risk of conflict between project stakeholders including community leaders, "
            "local government, competing energy providers, and project developer. "
            f"{'Larger settlement ({:,} people) may have more complex political dynamics.'.format(pop) if pop > 1000 else ''}"
        ),
        mitigation=[
            "Map all stakeholders and establish formal engagement plan",
            "Include local government representatives in project steering committee",
            "Implement grievance redress mechanism accessible to all community members",
        ],
        allocation="concessionaire",
    ))

    return items


# ── 6. Climate Risk ────────────────────────────────────────────────

def _assess_climate_risks(
    cluster: ClusterInfo,
    latitude: float,
    longitude: float,
) -> list[RiskItem]:
    items: list[RiskItem] = []

    # Geographic heuristics for Mozambique
    # Coastal zone: roughly longitude > 34 for central/north
    is_coastal = longitude > 34.5
    # Cyclone Idai corridor: central Mozambique (Sofala/Zambezia) lat ~-17 to -21
    in_idai_corridor = 17 <= latitude <= 21 and is_coastal
    # Cyclone Kenneth zone: northern coast (Cabo Delgado) lat < -13
    in_kenneth_zone = latitude < 13.5 and longitude > 39
    # Flood-prone lowlands: river basins, coastal
    is_lowland = (cluster.elevation_m or 200) < 100
    # Drought zone: interior southern Mozambique
    is_drought_zone = latitude > 21 and longitude < 35

    # Cyclone / extreme weather
    cyclone_l = 2
    cyclone_i = 4
    if in_idai_corridor or in_kenneth_zone:
        cyclone_l = 4
        cyclone_i = 5
    elif is_coastal:
        cyclone_l = 3
        cyclone_i = 4
    items.append(RiskItem(
        category="climate",
        sub_risk="cyclone_extreme_weather",
        likelihood=cyclone_l,
        impact=cyclone_i,
        risk_score=cyclone_l * cyclone_i,
        risk_level=_level_from_score(cyclone_l * cyclone_i),
        description=(
            f"{'Site is within the Cyclone Idai/Kenneth corridor — historically high cyclone exposure. ' if in_idai_corridor or in_kenneth_zone else ''}"
            f"{'Coastal location increases tropical cyclone exposure. ' if is_coastal and not (in_idai_corridor or in_kenneth_zone) else ''}"
            "Mozambique experienced Category 4+ cyclones Idai (2019) and Kenneth (2019) "
            "causing widespread infrastructure damage. Climate models project "
            "increasing cyclone intensity in the Mozambique Channel."
        ),
        mitigation=[
            "Design PV mounting structure for wind speeds >= 180 km/h (IEC 61400 Zone IV)",
            "Use ballasted or driven-pile mounting (not post-and-wire) in cyclone zones",
            "Specify IP65-rated inverters and weatherproof battery enclosure",
            "Obtain comprehensive weather/catastrophe insurance (ACRE Africa, ARC)",
            "Include 10% contingency for climate-resilient design upgrades",
        ],
        allocation="risk_instrument" if cyclone_l >= 4 else "shared",
    ))

    # Flood risk
    flood_l = 2
    flood_i = 3
    if is_lowland and is_coastal:
        flood_l = 4
        flood_i = 4
    elif is_lowland:
        flood_l = 3
        flood_i = 3
    items.append(RiskItem(
        category="climate",
        sub_risk="flood_risk",
        likelihood=flood_l,
        impact=flood_i,
        risk_score=flood_l * flood_i,
        risk_level=_level_from_score(flood_l * flood_i),
        description=(
            f"{'Low-elevation site ({:.0f}m) in potential flood zone. '.format(cluster.elevation_m) if is_lowland and cluster.elevation_m else ''}"
            "Flooding can damage ground-mounted PV arrays, battery systems, "
            "and distribution network. Mozambique river basins (Zambezi, Limpopo, Save) "
            "experience periodic severe flooding events."
        ),
        mitigation=[
            "Elevate battery enclosure and electrical equipment minimum 1m above grade",
            "Site PV array on elevated ground away from flood channels",
            "Design drainage and grading around powerhouse to IFC PS standards",
            "Include flood risk in catastrophe insurance coverage",
        ],
        allocation="shared",
    ))

    # Drought
    drought_l = 2
    drought_i = 2
    if is_drought_zone:
        drought_l = 3
        drought_i = 3
    items.append(RiskItem(
        category="climate",
        sub_risk="drought",
        likelihood=drought_l,
        impact=drought_i,
        risk_score=drought_l * drought_i,
        risk_level=_level_from_score(drought_l * drought_i),
        description=(
            "Drought impacts mini-grid revenues indirectly through reduced agricultural "
            "income and population displacement. "
            f"{'Southern interior location is in drought-prone zone. ' if is_drought_zone else ''}"
            "Can also affect panel cleaning water availability."
        ),
        mitigation=[
            "Diversify revenue base beyond agriculture-dependent customers",
            "Include drought clause in tariff adjustment provisions",
            "Use dry-cleaning methods for PV panel maintenance where feasible",
        ],
        allocation="shared",
    ))

    return items


# ── 7. Currency Risk ───────────────────────────────────────────────

def _assess_currency_risks(financial: FinancialResults) -> list[RiskItem]:
    items: list[RiskItem] = []
    capex = financial.total_capex_usd
    debt = financial.debt_amount_usd or 0

    # MZN depreciation
    dep_l = 4
    dep_i = 4
    items.append(RiskItem(
        category="currency",
        sub_risk="mzn_depreciation",
        likelihood=dep_l,
        impact=dep_i,
        risk_score=dep_l * dep_i,
        risk_level=_level_from_score(dep_l * dep_i),
        description=(
            "Mozambican metical (MZN) has depreciated ~15% annually against USD "
            "over the past decade (MZN 30/USD in 2015 to MZN 64/USD in 2024). "
            f"Revenue collected in MZN while USD {debt:,.0f} debt service and "
            "equipment replacement costs are USD-linked. Currency mismatch is a "
            "structural risk for all Mozambique mini-grid projects."
        ),
        mitigation=[
            "Index tariff to USD/MZN exchange rate with quarterly adjustment mechanism",
            "Seek MZN-denominated concessional debt where available (FSD Moz, BIM)",
            "Structure grant component to cover FX-exposed portion of capital costs",
            "Include currency risk buffer (15-20%) in financial projections",
            "Consider partial revenue collection in USD for commercial/productive customers",
        ],
        allocation="shared",
    ))

    # Debt service FX exposure
    if debt > 0:
        fx_l = 3
        fx_i = 4
        items.append(RiskItem(
            category="currency",
            sub_risk="debt_service_fx",
            likelihood=fx_l,
            impact=fx_i,
            risk_score=fx_l * fx_i,
            risk_level=_level_from_score(fx_l * fx_i),
            description=(
                f"USD {debt:,.0f} in debt with repayment in foreign currency. "
                "Revenue-cost currency mismatch creates DSCR volatility. "
                "A 20% MZN depreciation event would reduce DSCR by ~0.3x, "
                "potentially triggering debt covenant breach."
            ),
            mitigation=[
                "Negotiate DSCR covenant with FX-adjusted calculation methodology",
                "Include cash reserve account sized for 6-month debt service",
                "Seek DFI guarantee or first-loss facility covering FX-related DSCR shortfall",
                "Explore TCX (Currency Exchange Fund) hedge for MZN exposure",
            ],
            allocation="risk_instrument",
        ))

    return items


# ── 8. Political Risk ──────────────────────────────────────────────

def _assess_political_risks() -> list[RiskItem]:
    items: list[RiskItem] = []

    # Government stability
    items.append(RiskItem(
        category="political",
        sub_risk="government_stability",
        likelihood=2,
        impact=3,
        risk_score=6,
        risk_level="medium",
        description=(
            "Mozambique has maintained stable energy sector policy since the "
            "2017 ARENE establishment. The off-grid sector benefits from strong "
            "donor alignment (World Bank, AfDB, DFID/FCDO) which provides policy "
            "continuity incentives. However, periodic political tensions "
            "(2023-24 election disputes) create short-term uncertainty."
        ),
        mitigation=[
            "Obtain MIGA or ATI political risk insurance for investments > USD 500k",
            "Structure project under bilateral investment treaty protections",
            "Maintain relationships with both ruling party and opposition stakeholders",
        ],
        allocation="risk_instrument",
    ))

    # Policy continuity
    items.append(RiskItem(
        category="political",
        sub_risk="policy_continuity",
        likelihood=2,
        impact=3,
        risk_score=6,
        risk_level="medium",
        description=(
            "Off-grid energy policy has strong donor backing (ProEnergia, BRILHO, "
            "World Bank DRE programme). Risk of policy reversal is low but "
            "implementation capacity constraints may slow programme delivery. "
            "Decree 93/2021 provides legal foundation but secondary regulations "
            "are still being developed."
        ),
        mitigation=[
            "Engage actively in sector policy consultations through AMER",
            "Align project with government electrification master plan targets",
            "Document project contribution to SE4ALL and NDC commitments",
        ],
        allocation="public_partner",
    ))

    # Expropriation
    items.append(RiskItem(
        category="political",
        sub_risk="expropriation",
        likelihood=1,
        impact=5,
        risk_score=5,
        risk_level="low",
        description=(
            "Outright expropriation risk is low for small-scale rural energy "
            "infrastructure. However, creeping expropriation through tariff "
            "suppression or forced grid integration without compensation is "
            "a more realistic concern. Land in Mozambique is state-owned "
            "(DUAT is a use right, not ownership)."
        ),
        mitigation=[
            "Include stabilisation and compensation clauses in concession agreement",
            "Obtain political risk insurance covering creeping expropriation",
            "Document all investments and asset values for potential claims",
        ],
        allocation="risk_instrument",
    ))

    # Election cycle
    items.append(RiskItem(
        category="political",
        sub_risk="election_cycle",
        likelihood=2,
        impact=2,
        risk_score=4,
        risk_level="low",
        description=(
            "Mozambique election cycles (every 5 years) can create temporary "
            "policy uncertainty and administrative delays. Next general election "
            "expected 2029. Local elections may affect district-level engagement."
        ),
        mitigation=[
            "Avoid scheduling financial close or major approvals during election periods",
            "Maintain relationship continuity across political transitions",
        ],
        allocation="concessionaire",
    ))

    return items


# ── Helpers ────────────────────────────────────────────────────────

def _level_from_score(score: float) -> str:
    """Map numerical risk score to categorical level."""
    if score > 16:
        return "critical"
    if score >= 12:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def _abs_lat(cluster: ClusterInfo) -> float:
    """Return absolute latitude from cluster elevation heuristic.

    The ClusterInfo schema does not carry latitude directly, so we use
    the SiteCoordinates passed via the router.  For the engine we derive
    a rough latitude from elevation_m as a fallback — Mozambique's
    northern provinces are generally higher elevation.  The caller should
    ideally pass latitude via cluster.admin_region mapping.

    For Mozambique, latitudes range from about -10.5 (north) to -26.9 (south).
    We store as absolute value for comparison convenience.
    """
    # If admin_region gives us a province hint, use centroid latitude
    region = (cluster.admin_region or "").lower()
    province_lats = {
        "cabo delgado": 12.5,
        "niassa": 13.0,
        "nampula": 15.0,
        "zambezia": 17.0,
        "tete": 15.5,
        "manica": 19.5,
        "sofala": 19.5,
        "inhambane": 23.0,
        "gaza": 23.5,
        "maputo": 26.0,
    }
    for prov, lat in province_lats.items():
        if prov in region:
            return lat

    # Fallback: use elevation heuristic (very rough)
    elev = cluster.elevation_m or 200
    if elev > 500:
        return 14.0  # likely northern plateau
    if elev > 200:
        return 17.0  # central
    return 22.0  # likely southern lowlands


def _est_lon(cluster: ClusterInfo) -> float:
    """Estimate longitude from province or distance-to-coast heuristic."""
    region = (cluster.admin_region or "").lower()
    province_lons = {
        "cabo delgado": 40.0,
        "niassa": 35.5,
        "nampula": 39.5,
        "zambezia": 37.0,
        "tete": 33.5,
        "manica": 33.5,
        "sofala": 35.0,
        "inhambane": 35.0,
        "gaza": 33.5,
        "maputo": 32.5,
    }
    for prov, lon in province_lons.items():
        if prov in region:
            return lon

    # Fallback: coastal if close to road and low elevation
    dist_road = cluster.dist_road_km
    elev = cluster.elevation_m or 200
    if dist_road < 20 and elev < 100:
        return 36.0  # likely coastal
    return 35.0  # interior default


def _estimate_mitigation_cost(
    risks: list[RiskItem],
    capex: float,
    cluster: ClusterInfo,
) -> float:
    """Estimate total investment required for risk mitigation measures.

    Rough cost categories:
    - Insurance: 0.5-2% of CAPEX annually
    - Security: USD 1,200-6,000/year
    - Community engagement: USD 5,000-15,000
    - Climate resilience upgrades: 5-10% of CAPEX
    - Currency hedge: 2-3% of debt value
    """
    cost = 0.0

    # Insurance (weather, theft, political risk)
    has_critical_climate = any(
        r.category == "climate" and r.risk_level in ("critical", "high") for r in risks
    )
    insurance_rate = 0.02 if has_critical_climate else 0.01
    cost += capex * insurance_rate  # Annual premium (Year 1)

    # Security enhancements
    has_high_security = any(
        r.category == "security" and r.risk_level in ("critical", "high") for r in risks
    )
    if has_high_security:
        cost += 15_000  # Enhanced security infrastructure
    else:
        cost += 5_000  # Basic security measures

    # Community engagement and land
    cost += 10_000  # Baseline community consultation + DUAT

    # Climate resilience design upgrades
    if has_critical_climate:
        cost += capex * 0.10  # 10% uplift for cyclone/flood resilience
    else:
        cost += capex * 0.03  # 3% for standard climate-proofing

    # Political risk insurance (for larger projects)
    if capex > 500_000:
        cost += capex * 0.015  # PRI premium ~1.5% of insured value

    return cost
