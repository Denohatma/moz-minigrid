from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.site import ClusterInfo
from app.schemas.analysis import DemandEstimate

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"


# ── Output Models ──────────────────────────────────────────────────────


class ProductiveUseSector(BaseModel):
    sector: str
    relevance: str = Field(description="high, medium, low, or none")
    rationale: str
    indicative_activities: list[str]
    estimated_demand_kwh_day: float
    seasonal_pattern: str = Field(description="year-round, seasonal, or post-harvest")


class AnchorCustomer(BaseModel):
    type: str
    name: str
    estimated_demand_kwh_day: float
    estimated_peak_kw: float
    confidence: str = Field(description="high, medium, or low")
    contract_type: str = Field(description="take-or-pay, minimum-offtake, or standard")


class ProductiveUseEquipment(BaseModel):
    sector: str
    equipment: str
    power_kw: float
    capex_usd_low: float
    capex_usd_high: float
    ownership_model: str


class ProductiveUseAssessment(BaseModel):
    sectors: list[ProductiveUseSector]
    anchors: list[AnchorCustomer]
    total_productive_demand_kwh_day: float
    productive_demand_pct: float
    demand_projections: dict = Field(description="year -> kwh/day")
    equipment_recommendations: list[ProductiveUseEquipment]
    complementary_investment_usd: dict = Field(
        description="equipment, working_capital, market_access, training, total"
    )
    jobs: dict = Field(description="direct, indirect, total")
    incremental_income_usd_year: float
    demand_stimulation: dict = Field(
        description="uptake targets, finance model, aggregation strategy"
    )
    warnings: list[str] = Field(default_factory=list)


# ── Province mappings for sector relevance ─────────────────────────────

# Normalised lower-case province names used to match admin_region.
_CASHEW_PROVINCES = {"nampula", "zambezia", "zambezia", "manica", "tete"}
_HORTICULTURE_PROVINCES = {"manica", "zambezia", "tete"}
_FISHERY_PROVINCES = {
    "cabo delgado", "nampula", "zambezia", "sofala", "inhambane",
    "gaza", "maputo", "maputo cidade", "tete",  # Lake Cahora Bassa
}
_LIVESTOCK_PROVINCES = {"manica", "tete"}
_MINING_PROVINCES = {"manica", "tete", "cabo delgado"}
_TOURISM_PROVINCES = {"manica", "inhambane", "cabo delgado", "sofala", "gaza"}

# ── Growth rates ───────────────────────────────────────────────────────

_PRODUCTIVE_GROWTH_RATE = 0.05
_RESIDENTIAL_GROWTH_RATE = 0.03


# ── Main entry point ──────────────────────────────────────────────────


def analyze_productive_use(
    cluster: ClusterInfo,
    demand: DemandEstimate,
) -> ProductiveUseAssessment:
    """Analyse productive-use value chain potential for a mini-grid site.

    Returns a full assessment even when cluster data is sparse — missing
    fields trigger population-based heuristics instead of errors.
    """
    config = _load_config()
    province = _normalise_province(cluster.admin_region)
    warnings: list[str] = []

    # ── 1. Sector scanning ─────────────────────────────────────────
    sectors = _scan_sectors(cluster, province, config, warnings)

    # ── 2. Anchor load identification ──────────────────────────────
    anchors = _identify_anchors(cluster, demand, province, warnings)

    # ── 3. Demand quantification ───────────────────────────────────
    anchor_demand = sum(a.estimated_demand_kwh_day for a in anchors)
    sme_demand = _estimate_sme_demand(cluster, demand)
    productive_demand = anchor_demand + sme_demand
    total_site_demand = demand.daily_energy_kwh + productive_demand
    productive_pct = (
        (productive_demand / total_site_demand * 100) if total_site_demand > 0 else 0.0
    )

    projections = _project_demand(
        productive_demand, demand.daily_energy_kwh,
    )

    # ── 4. Equipment recommendations ───────────────────────────────
    equipment = _recommend_equipment(sectors)

    # ── 5. Complementary investment ────────────────────────────────
    investment = _estimate_complementary_investment(
        equipment, cluster, demand, sectors,
    )

    # ── 6. Job & income projections ────────────────────────────────
    jobs = _project_jobs(cluster, demand, sectors)
    incremental_income = _estimate_incremental_income(
        cluster, productive_demand, demand.households,
    )

    # ── 7. Demand stimulation programme ────────────────────────────
    stimulation = _design_stimulation_programme(cluster, demand, sectors)

    return ProductiveUseAssessment(
        sectors=sectors,
        anchors=anchors,
        total_productive_demand_kwh_day=round(productive_demand, 2),
        productive_demand_pct=round(productive_pct, 1),
        demand_projections=projections,
        equipment_recommendations=equipment,
        complementary_investment_usd=investment,
        jobs=jobs,
        incremental_income_usd_year=round(incremental_income, 0),
        demand_stimulation=stimulation,
        warnings=warnings,
    )


# ── Sector scanning ───────────────────────────────────────────────────


def _scan_sectors(
    cluster: ClusterInfo,
    province: str,
    config: dict,
    warnings: list[str],
) -> list[ProductiveUseSector]:
    """Assess relevance of 11 productive-use sectors."""
    pop = cluster.population
    is_urban = cluster.is_urban
    has_ag = cluster.ag_area_ha is not None and cluster.ag_area_ha > 0
    ag_area = cluster.ag_area_ha or 0.0
    road_ok = cluster.dist_road_km < 10
    has_facilities = bool(
        cluster.has_education_facility or cluster.has_health_facility
    )
    ntl = cluster.max_ntl
    rwi = cluster.mean_rwi
    large_bldg = cluster.large_buildings or 0

    if not has_ag and pop > 200:
        warnings.append(
            "No crop data available; using population-based heuristics for "
            "agriculture-related sectors."
        )

    sectors: list[ProductiveUseSector] = []

    # 1. Cereal & tuber processing — universal across Mozambique
    cereal_rel, cereal_rat, cereal_demand = _assess_cereal(
        pop, has_ag, ag_area, is_urban,
    )
    sectors.append(ProductiveUseSector(
        sector="Cereal & tuber processing",
        relevance=cereal_rel,
        rationale=cereal_rat,
        indicative_activities=[
            "Maize milling", "Cassava chipping/drying",
            "Rice hulling", "Flour packaging",
        ],
        estimated_demand_kwh_day=cereal_demand,
        seasonal_pattern="post-harvest",
    ))

    # 2. Oilseed & cashew processing
    cashew_rel, cashew_rat, cashew_demand = _assess_cashew(
        pop, province, has_ag, ag_area, is_urban,
    )
    sectors.append(ProductiveUseSector(
        sector="Oilseed & cashew processing",
        relevance=cashew_rel,
        rationale=cashew_rat,
        indicative_activities=[
            "Cashew nut shelling", "Groundnut pressing",
            "Sunflower oil extraction", "Sesame cleaning & grading",
        ],
        estimated_demand_kwh_day=cashew_demand,
        seasonal_pattern="post-harvest",
    ))

    # 3. Horticulture & irrigation
    horti_rel, horti_rat, horti_demand = _assess_horticulture(
        pop, province, has_ag, ag_area, cluster,
    )
    sectors.append(ProductiveUseSector(
        sector="Horticulture & irrigation",
        relevance=horti_rel,
        rationale=horti_rat,
        indicative_activities=[
            "Solar irrigation pumping", "Drip irrigation",
            "Vegetable nurseries", "Post-harvest handling",
        ],
        estimated_demand_kwh_day=horti_demand,
        seasonal_pattern="seasonal",
    ))

    # 4. Fisheries & aquaculture
    fish_rel, fish_rat, fish_demand = _assess_fisheries(
        pop, province, cluster,
    )
    sectors.append(ProductiveUseSector(
        sector="Fisheries & aquaculture",
        relevance=fish_rel,
        rationale=fish_rat,
        indicative_activities=[
            "Fish cold storage", "Ice making",
            "Fish drying/smoking (electric)", "Aquaculture aeration",
        ],
        estimated_demand_kwh_day=fish_demand,
        seasonal_pattern="year-round",
    ))

    # 5. Livestock & dairy
    live_rel, live_rat, live_demand = _assess_livestock(
        pop, province, has_ag, is_urban,
    )
    sectors.append(ProductiveUseSector(
        sector="Livestock & dairy",
        relevance=live_rel,
        rationale=live_rat,
        indicative_activities=[
            "Milk chilling", "Poultry hatchery/brooding",
            "Feed milling", "Veterinary cold chain",
        ],
        estimated_demand_kwh_day=live_demand,
        seasonal_pattern="year-round",
    ))

    # 6. Cold chain (vaccines, perishables) — universal
    cold_rel, cold_rat, cold_demand = _assess_cold_chain(
        pop, cluster, is_urban,
    )
    sectors.append(ProductiveUseSector(
        sector="Cold chain",
        relevance=cold_rel,
        rationale=cold_rat,
        indicative_activities=[
            "Vaccine refrigeration", "Perishable food storage",
            "Pharmaceutical cold storage", "Community cold room",
        ],
        estimated_demand_kwh_day=cold_demand,
        seasonal_pattern="year-round",
    ))

    # 7. Artisanal mining services
    mine_rel, mine_rat, mine_demand = _assess_mining(
        pop, province, cluster,
    )
    sectors.append(ProductiveUseSector(
        sector="Artisanal mining services",
        relevance=mine_rel,
        rationale=mine_rat,
        indicative_activities=[
            "Ore crushing/grinding", "Water pumping for sluicing",
            "Lighting for underground work", "Welding & tool maintenance",
        ],
        estimated_demand_kwh_day=mine_demand,
        seasonal_pattern="year-round",
    ))

    # 8. Light manufacturing & trades
    mfg_rel, mfg_rat, mfg_demand = _assess_manufacturing(
        pop, is_urban, large_bldg, ntl, road_ok,
    )
    sectors.append(ProductiveUseSector(
        sector="Light manufacturing & trades",
        relevance=mfg_rel,
        rationale=mfg_rat,
        indicative_activities=[
            "Carpentry & woodwork", "Welding & metalwork",
            "Tailoring", "Brick-making",
        ],
        estimated_demand_kwh_day=mfg_demand,
        seasonal_pattern="year-round",
    ))

    # 9. ICT & digital services — universal
    ict_rel, ict_rat, ict_demand = _assess_ict(pop, is_urban, road_ok, ntl)
    sectors.append(ProductiveUseSector(
        sector="ICT & digital services",
        relevance=ict_rel,
        rationale=ict_rat,
        indicative_activities=[
            "Phone/device charging", "Internet cafe/hub",
            "Mobile money agent", "Digital literacy centre",
        ],
        estimated_demand_kwh_day=ict_demand,
        seasonal_pattern="year-round",
    ))

    # 10. Tourism & hospitality
    tour_rel, tour_rat, tour_demand = _assess_tourism(
        pop, province, cluster, is_urban,
    )
    sectors.append(ProductiveUseSector(
        sector="Tourism & hospitality",
        relevance=tour_rel,
        rationale=tour_rat,
        indicative_activities=[
            "Eco-lodge power supply", "Restaurant refrigeration",
            "Guest Wi-Fi & lighting", "Laundry services",
        ],
        estimated_demand_kwh_day=tour_demand,
        seasonal_pattern="seasonal",
    ))

    # 11. Public services as anchors — universal
    pub_rel, pub_rat, pub_demand = _assess_public_services(
        pop, cluster, is_urban,
    )
    sectors.append(ProductiveUseSector(
        sector="Public services as anchors",
        relevance=pub_rel,
        rationale=pub_rat,
        indicative_activities=[
            "Health centre electrification", "School ICT lab",
            "Water pumping station", "Street lighting",
        ],
        estimated_demand_kwh_day=pub_demand,
        seasonal_pattern="year-round",
    ))

    return sectors


# ── Individual sector assessment helpers ───────────────────────────────


def _assess_cereal(
    pop: int, has_ag: bool, ag_area: float, is_urban: int,
) -> tuple[str, str, float]:
    if has_ag and ag_area > 50:
        rel = "high"
        demand = min(ag_area * 0.3, 80.0)
        rat = (
            f"Significant cropland ({ag_area:.0f} ha) supports cereal/tuber "
            "processing demand. Population can sustain multiple mills."
        )
    elif pop > 500 or (has_ag and ag_area > 10):
        rel = "medium"
        demand = max(pop * 0.02, 5.0)
        rat = (
            f"Population of {pop} and available cropland suggest moderate "
            "milling demand."
        )
    elif pop > 200:
        rel = "low"
        demand = max(pop * 0.01, 2.0)
        rat = "Small settlement; limited but non-zero milling demand likely."
    else:
        rel = "none"
        demand = 0.0
        rat = "Settlement too small to support dedicated processing."
    return rel, rat, round(demand, 1)


def _assess_cashew(
    pop: int, province: str, has_ag: bool, ag_area: float, is_urban: int,
) -> tuple[str, str, float]:
    in_zone = province in _CASHEW_PROVINCES
    if not in_zone:
        return (
            "none",
            f"Province ({province or 'unknown'}) outside main oilseed/cashew belt.",
            0.0,
        )
    if has_ag and ag_area > 30 and pop > 500:
        return (
            "high",
            f"Cashew/oilseed belt province with {ag_area:.0f} ha cropland "
            f"and population {pop}.",
            round(min(ag_area * 0.2, 60.0), 1),
        )
    if pop > 300:
        return (
            "medium",
            f"Within cashew belt; population {pop} can support small-scale processing.",
            round(max(pop * 0.015, 4.0), 1),
        )
    return (
        "low",
        "Within cashew belt but small settlement limits processing volumes.",
        2.0,
    )


def _assess_horticulture(
    pop: int, province: str, has_ag: bool, ag_area: float,
    cluster: ClusterInfo,
) -> tuple[str, str, float]:
    in_zone = province in _HORTICULTURE_PROVINCES
    near_water = (
        cluster.closest_distance_water_km is not None
        and cluster.closest_distance_water_km < 5
    )
    if in_zone and (has_ag or near_water) and pop > 300:
        demand = round(min(pop * 0.03, 50.0), 1)
        return (
            "high",
            f"Highland/irrigation province with {'water access and ' if near_water else ''}"
            f"population {pop}; solar pumping and irrigation highly viable.",
            demand,
        )
    if (has_ag and ag_area > 20) or near_water:
        demand = round(max(pop * 0.015, 3.0), 1)
        return (
            "medium",
            "Cropland or water proximity supports small-scale horticulture.",
            demand,
        )
    if pop > 200 and in_zone:
        return ("low", "Horticulture zone but limited water/crop data.", 2.0)
    return ("none", "Outside main horticulture zones or insufficient data.", 0.0)


def _assess_fisheries(
    pop: int, province: str, cluster: ClusterInfo,
) -> tuple[str, str, float]:
    in_zone = province in _FISHERY_PROVINCES
    near_water = (
        cluster.closest_distance_water_km is not None
        and cluster.closest_distance_water_km < 10
    )
    if in_zone and near_water and pop > 300:
        return (
            "high",
            f"Coastal/lacustrine province with water body within "
            f"{cluster.closest_distance_water_km:.1f} km. "
            "Cold storage and ice-making highly viable.",
            round(min(pop * 0.04, 60.0), 1),
        )
    if in_zone and pop > 200:
        return (
            "medium",
            "Fisheries province; moderate potential for fish processing.",
            round(max(pop * 0.015, 3.0), 1),
        )
    if near_water:
        return ("low", "Near water body but outside main fishery provinces.", 2.0)
    return ("none", "No proximity to significant fishery resources.", 0.0)


def _assess_livestock(
    pop: int, province: str, has_ag: bool, is_urban: int,
) -> tuple[str, str, float]:
    in_zone = province in _LIVESTOCK_PROVINCES
    if in_zone and pop > 500:
        return (
            "high",
            f"Livestock belt province (Manica/Tete corridor) with population {pop}.",
            round(min(pop * 0.02, 40.0), 1),
        )
    if in_zone and pop > 200:
        return (
            "medium",
            "Livestock province; milk chilling and poultry feasible at scale.",
            round(max(pop * 0.01, 3.0), 1),
        )
    if has_ag and pop > 400:
        return (
            "low",
            "Agricultural area may support small-scale poultry or dairy.",
            2.0,
        )
    return ("none", "Outside main livestock zones and insufficient scale.", 0.0)


def _assess_cold_chain(
    pop: int, cluster: ClusterInfo, is_urban: int,
) -> tuple[str, str, float]:
    has_health = bool(cluster.has_health_facility)
    if has_health and pop > 300:
        return (
            "high",
            "Health facility present; vaccine cold chain is critical anchor load. "
            "Perishable storage benefits community.",
            round(min(8.0 + pop * 0.005, 25.0), 1),
        )
    if pop > 500 or has_health:
        return (
            "medium",
            f"Population of {pop}{' with health facility' if has_health else ''} "
            "warrants community cold storage.",
            round(max(5.0, pop * 0.003), 1),
        )
    if pop > 200:
        return ("low", "Small settlement; basic vaccine cold chain still relevant.", 3.0)
    return ("low", "Minimal population; vaccine cold chain only.", 2.0)


def _assess_mining(
    pop: int, province: str, cluster: ClusterInfo,
) -> tuple[str, str, float]:
    in_zone = province in _MINING_PROVINCES
    if not in_zone:
        return ("none", f"Province outside artisanal mining corridors.", 0.0)
    # Heuristic: mining areas tend to have higher NTL relative to population
    ntl_pop_ratio = cluster.max_ntl / max(pop, 1) * 1000
    if ntl_pop_ratio > 5 and pop > 300:
        return (
            "high",
            "Mining corridor province with elevated nighttime light activity "
            "relative to population — suggests active mining.",
            round(min(pop * 0.05, 80.0), 1),
        )
    if pop > 200:
        return (
            "medium",
            "Within mining corridor; crushing and water pumping services possible.",
            round(max(pop * 0.02, 5.0), 1),
        )
    return ("low", "Mining corridor but small settlement.", 3.0)


def _assess_manufacturing(
    pop: int, is_urban: int, large_bldg: int, ntl: float, road_ok: bool,
) -> tuple[str, str, float]:
    economic_activity = (
        is_urban >= 1
        or large_bldg >= 3
        or (ntl > 10 and road_ok)
    )
    if economic_activity and pop > 800:
        return (
            "high",
            f"Administrative/commercial centre indicators: "
            f"is_urban={is_urban}, large_buildings={large_bldg}, NTL={ntl:.1f}.",
            round(min(pop * 0.03, 60.0), 1),
        )
    if economic_activity and pop > 300:
        return (
            "medium",
            "Some commercial activity detected; tailoring, welding viable.",
            round(max(pop * 0.015, 5.0), 1),
        )
    if pop > 500 and road_ok:
        return (
            "low",
            "Road access may support basic carpentry and metalwork.",
            3.0,
        )
    return ("none", "Insufficient commercial activity indicators.", 0.0)


def _assess_ict(
    pop: int, is_urban: int, road_ok: bool, ntl: float,
) -> tuple[str, str, float]:
    if pop > 500 or is_urban >= 1:
        demand = round(min(pop * 0.01, 20.0), 1)
        return (
            "high",
            f"Population {pop} supports phone charging hub, mobile money, "
            "and internet services.",
            max(demand, 5.0),
        )
    if pop > 200:
        return (
            "medium",
            "Phone charging and mobile money agent viable.",
            round(max(pop * 0.008, 2.0), 1),
        )
    return ("low", "Basic phone charging demand only.", 1.0)


def _assess_tourism(
    pop: int, province: str, cluster: ClusterInfo, is_urban: int,
) -> tuple[str, str, float]:
    in_zone = province in _TOURISM_PROVINCES
    near_attraction = in_zone and (
        cluster.dist_road_km < 15
        or (cluster.closest_distance_water_km is not None
            and cluster.closest_distance_water_km < 5)
    )
    if near_attraction and pop > 300:
        return (
            "medium",
            "Tourism province with road/water access; eco-lodge potential.",
            round(min(pop * 0.02, 30.0), 1),
        )
    if in_zone:
        return ("low", "Tourism province but limited accessibility.", 2.0)
    return ("none", "Outside main tourism corridors.", 0.0)


def _assess_public_services(
    pop: int, cluster: ClusterInfo, is_urban: int,
) -> tuple[str, str, float]:
    has_edu = bool(cluster.has_education_facility)
    has_health = bool(cluster.has_health_facility)
    near_water = (
        cluster.closest_distance_water_km is not None
        and cluster.closest_distance_water_km < 5
    )

    services_present = sum([has_edu, has_health, near_water])
    base_demand = 0.0
    activities: list[str] = []

    if has_health:
        base_demand += 8.0
    if has_edu:
        base_demand += 5.0
    if near_water:
        base_demand += 6.0
    if pop > 300:
        base_demand += 3.0  # street lighting

    if services_present >= 2 or pop > 500:
        return (
            "high",
            f"Multiple public services present "
            f"({'health, ' if has_health else ''}"
            f"{'education, ' if has_edu else ''}"
            f"{'water' if near_water else ''}) — "
            "strong anchor load potential.",
            round(base_demand, 1),
        )
    if services_present >= 1:
        return (
            "medium",
            "At least one public service facility provides reliable anchor load.",
            round(base_demand, 1),
        )
    if pop > 200:
        return (
            "low",
            "No mapped public facilities but population warrants basic services.",
            3.0,
        )
    return ("low", "Minimal public service infrastructure mapped.", 2.0)


# ── Anchor load identification ─────────────────────────────────────────


def _identify_anchors(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    province: str,
    warnings: list[str],
) -> list[AnchorCustomer]:
    anchors: list[AnchorCustomer] = []

    # Telecom towers — population > 500 with road access
    if cluster.population > 500 and cluster.dist_road_km < 15:
        tower_demand = 24.0  # typical BTS site ~1 kW continuous
        anchors.append(AnchorCustomer(
            type="telecom_tower",
            name="Telecom BTS site",
            estimated_demand_kwh_day=tower_demand,
            estimated_peak_kw=1.5,
            confidence="medium" if cluster.population > 1000 else "low",
            contract_type="take-or-pay",
        ))

    # Agro-processors — based on crop data
    ag_area = cluster.ag_area_ha or 0.0
    if ag_area > 20 or cluster.population > 800:
        proc_demand = round(min(max(ag_area * 0.15, 8.0), 50.0), 1)
        proc_peak = round(proc_demand / 8.0, 1)  # ~8 operating hours
        anchors.append(AnchorCustomer(
            type="agro_processor",
            name="Grain/cassava processing unit",
            estimated_demand_kwh_day=proc_demand,
            estimated_peak_kw=proc_peak,
            confidence="high" if ag_area > 50 else "medium",
            contract_type="minimum-offtake",
        ))

    # Health centre
    if cluster.has_health_facility:
        health_demand = 12.0  # WHO guidance: rural health centre 8-15 kWh/day
        anchors.append(AnchorCustomer(
            type="health_centre",
            name="Health facility",
            estimated_demand_kwh_day=health_demand,
            estimated_peak_kw=2.0,
            confidence="high",
            contract_type="take-or-pay",
        ))

    # School
    if cluster.has_education_facility:
        edu_demand = 6.0  # lighting, ICT lab, admin
        anchors.append(AnchorCustomer(
            type="school",
            name="Education facility",
            estimated_demand_kwh_day=edu_demand,
            estimated_peak_kw=1.5,
            confidence="high",
            contract_type="take-or-pay",
        ))

    # Water pumping — near water source
    if (cluster.closest_distance_water_km is not None
            and cluster.closest_distance_water_km < 5
            and cluster.population > 200):
        pump_demand = round(min(cluster.population * 0.01, 15.0), 1)
        anchors.append(AnchorCustomer(
            type="water_pumping",
            name="Community water pumping station",
            estimated_demand_kwh_day=max(pump_demand, 5.0),
            estimated_peak_kw=2.5,
            confidence="medium",
            contract_type="take-or-pay",
        ))

    # Commercial entities — based on large buildings and NTL
    large_bldg = cluster.large_buildings or 0
    if large_bldg >= 2 or (cluster.max_ntl > 15 and cluster.is_urban >= 1):
        n_commercial = max(large_bldg, 2)
        comm_demand = round(n_commercial * 5.0, 1)
        anchors.append(AnchorCustomer(
            type="commercial",
            name=f"Commercial entities ({n_commercial} est.)",
            estimated_demand_kwh_day=comm_demand,
            estimated_peak_kw=round(comm_demand / 10.0, 1),
            confidence="low" if large_bldg < 3 else "medium",
            contract_type="standard",
        ))

    if not anchors:
        warnings.append(
            "No anchor customers identified. Productive-use demand stimulation "
            "programme will be critical for project viability."
        )

    return anchors


# ── SME demand estimation ──────────────────────────────────────────────


def _estimate_sme_demand(cluster: ClusterInfo, demand: DemandEstimate) -> float:
    """Estimate SME/informal sector demand beyond identified anchors.

    Uses population, urban classification, and wealth index as proxies.
    """
    pop = cluster.population
    is_urban = cluster.is_urban
    rwi = cluster.mean_rwi

    # Base: 1-3% of population as SME operators, each using 2-5 kWh/day
    if is_urban >= 2:
        sme_pct = 0.03
        kwh_per_sme = 5.0
    elif is_urban == 1:
        sme_pct = 0.02
        kwh_per_sme = 3.5
    else:
        sme_pct = 0.01
        kwh_per_sme = 2.0

    # Wealth index adjustment
    if rwi is not None:
        multiplier = 1.0 + max(min(rwi, 1.0), -1.0) * 0.3
        kwh_per_sme *= multiplier

    n_smes = max(int(pop * sme_pct), 1)
    return round(n_smes * kwh_per_sme, 1)


# ── Demand projections ─────────────────────────────────────────────────


def _project_demand(
    productive_kwh_day: float,
    residential_kwh_day: float,
) -> dict:
    """Project total demand at year 1, 5, 10, 20."""
    projections: dict[str, float] = {}
    for year in (1, 5, 10, 20):
        prod = productive_kwh_day * (1 + _PRODUCTIVE_GROWTH_RATE) ** (year - 1)
        resi = residential_kwh_day * (1 + _RESIDENTIAL_GROWTH_RATE) ** (year - 1)
        projections[f"year_{year}"] = round(prod + resi, 1)
    return projections


# ── Equipment recommendations ──────────────────────────────────────────

# Catalogue of productive-use equipment for Mozambique context
_EQUIPMENT_CATALOGUE: dict[str, list[dict]] = {
    "Cereal & tuber processing": [
        {
            "equipment": "5-7 kW maize/cassava hammer mill",
            "power_kw": 6.0, "capex_low": 2500, "capex_high": 5000,
            "ownership": "lease",
        },
        {
            "equipment": "3 kW rice huller",
            "power_kw": 3.0, "capex_low": 1800, "capex_high": 3500,
            "ownership": "lease",
        },
    ],
    "Oilseed & cashew processing": [
        {
            "equipment": "Cashew shelling machine (manual-electric hybrid)",
            "power_kw": 1.5, "capex_low": 1200, "capex_high": 2500,
            "ownership": "purchase",
        },
        {
            "equipment": "2-3 kW oil press (groundnut/sunflower)",
            "power_kw": 2.5, "capex_low": 2000, "capex_high": 4000,
            "ownership": "lease",
        },
    ],
    "Horticulture & irrigation": [
        {
            "equipment": "0.75-2 kW solar irrigation pump",
            "power_kw": 1.5, "capex_low": 800, "capex_high": 2500,
            "ownership": "PAYGO",
        },
        {
            "equipment": "Drip irrigation kit (0.5 ha)",
            "power_kw": 0.0, "capex_low": 300, "capex_high": 800,
            "ownership": "purchase",
        },
    ],
    "Fisheries & aquaculture": [
        {
            "equipment": "Ice-making machine (50 kg/day)",
            "power_kw": 2.0, "capex_low": 3000, "capex_high": 6000,
            "ownership": "lease",
        },
        {
            "equipment": "Fish cold room (1-2 tonnes)",
            "power_kw": 3.0, "capex_low": 5000, "capex_high": 12000,
            "ownership": "lease",
        },
    ],
    "Livestock & dairy": [
        {
            "equipment": "Milk chiller (100-200 litres)",
            "power_kw": 1.0, "capex_low": 2000, "capex_high": 5000,
            "ownership": "lease",
        },
        {
            "equipment": "Poultry incubator (200-500 eggs)",
            "power_kw": 0.5, "capex_low": 500, "capex_high": 1500,
            "ownership": "purchase",
        },
    ],
    "Cold chain": [
        {
            "equipment": "Solar vaccine refrigerator (WHO PQS)",
            "power_kw": 0.15, "capex_low": 2000, "capex_high": 4000,
            "ownership": "purchase",
        },
        {
            "equipment": "Community cold room (2-5 m3)",
            "power_kw": 2.5, "capex_low": 5000, "capex_high": 15000,
            "ownership": "lease",
        },
    ],
    "Artisanal mining services": [
        {
            "equipment": "Electric ore crusher (5-10 kW)",
            "power_kw": 7.5, "capex_low": 4000, "capex_high": 10000,
            "ownership": "lease",
        },
        {
            "equipment": "1.5 kW water pump for sluicing",
            "power_kw": 1.5, "capex_low": 600, "capex_high": 1500,
            "ownership": "purchase",
        },
    ],
    "Light manufacturing & trades": [
        {
            "equipment": "Electric welding machine (3-5 kW)",
            "power_kw": 4.0, "capex_low": 800, "capex_high": 2000,
            "ownership": "purchase",
        },
        {
            "equipment": "Woodworking tools set (1-3 kW)",
            "power_kw": 2.0, "capex_low": 1000, "capex_high": 3000,
            "ownership": "lease",
        },
        {
            "equipment": "Industrial sewing machines (x3)",
            "power_kw": 0.9, "capex_low": 600, "capex_high": 1500,
            "ownership": "purchase",
        },
    ],
    "ICT & digital services": [
        {
            "equipment": "Multi-port phone charging station (20-50 ports)",
            "power_kw": 0.5, "capex_low": 200, "capex_high": 600,
            "ownership": "PAYGO",
        },
        {
            "equipment": "Community Wi-Fi hotspot + router",
            "power_kw": 0.1, "capex_low": 300, "capex_high": 800,
            "ownership": "purchase",
        },
    ],
    "Tourism & hospitality": [
        {
            "equipment": "Commercial refrigerator/freezer",
            "power_kw": 0.8, "capex_low": 800, "capex_high": 2000,
            "ownership": "purchase",
        },
        {
            "equipment": "Washing machine (commercial)",
            "power_kw": 2.0, "capex_low": 500, "capex_high": 1500,
            "ownership": "purchase",
        },
    ],
    "Public services as anchors": [
        {
            "equipment": "Water pumping system (submersible, 1-3 kW)",
            "power_kw": 2.0, "capex_low": 2000, "capex_high": 6000,
            "ownership": "purchase",
        },
        {
            "equipment": "School ICT lab (5 laptops + printer)",
            "power_kw": 0.8, "capex_low": 3000, "capex_high": 6000,
            "ownership": "purchase",
        },
        {
            "equipment": "LED street lighting (10 poles)",
            "power_kw": 0.4, "capex_low": 2000, "capex_high": 5000,
            "ownership": "purchase",
        },
    ],
}


def _recommend_equipment(
    sectors: list[ProductiveUseSector],
) -> list[ProductiveUseEquipment]:
    """Return equipment recommendations for sectors rated medium or high."""
    recs: list[ProductiveUseEquipment] = []
    for sector in sectors:
        if sector.relevance in ("none", "low"):
            continue
        items = _EQUIPMENT_CATALOGUE.get(sector.sector, [])
        for item in items:
            recs.append(ProductiveUseEquipment(
                sector=sector.sector,
                equipment=item["equipment"],
                power_kw=item["power_kw"],
                capex_usd_low=item["capex_low"],
                capex_usd_high=item["capex_high"],
                ownership_model=item["ownership"],
            ))
    return recs


# ── Complementary investment ───────────────────────────────────────────


def _estimate_complementary_investment(
    equipment: list[ProductiveUseEquipment],
    cluster: ClusterInfo,
    demand: DemandEstimate,
    sectors: list[ProductiveUseSector],
) -> dict:
    """Estimate total indicative investment for productive-use enablement."""
    # Equipment CAPEX: midpoint of recommended equipment
    equipment_capex = sum(
        (eq.capex_usd_low + eq.capex_usd_high) / 2 for eq in equipment
    )

    # Working capital: ~20% of equipment capex for raw materials, inventory
    working_capital = equipment_capex * 0.20

    # Market access: road/transport improvements, market linkage
    # Higher if remote
    if cluster.dist_road_km > 20:
        market_access = max(5000.0, equipment_capex * 0.15)
    elif cluster.dist_road_km > 10:
        market_access = max(3000.0, equipment_capex * 0.10)
    else:
        market_access = max(1500.0, equipment_capex * 0.05)

    # Training: business skills, equipment operation, financial literacy
    relevant_sectors = sum(
        1 for s in sectors if s.relevance in ("high", "medium")
    )
    training = max(2000.0, relevant_sectors * 1500.0)

    total = equipment_capex + working_capital + market_access + training

    return {
        "equipment_capex_usd": round(equipment_capex, 0),
        "working_capital_usd": round(working_capital, 0),
        "market_access_usd": round(market_access, 0),
        "training_usd": round(training, 0),
        "total_usd": round(total, 0),
    }


# ── Job & income projections ──────────────────────────────────────────


def _project_jobs(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    sectors: list[ProductiveUseSector],
) -> dict:
    """Estimate direct (mini-grid ops) and indirect (productive-use) jobs."""
    # Direct jobs: mini-grid technician, site manager, meter reader
    # Roughly 2-5 depending on system size
    peak_kw = demand.peak_demand_kw
    if peak_kw < 10:
        direct = 2
    elif peak_kw < 50:
        direct = 3
    else:
        direct = 5

    # Indirect jobs: from productive-use businesses
    # Approximately 2-4 jobs per high-relevance sector, 1-2 per medium
    indirect = 0
    for s in sectors:
        if s.relevance == "high":
            indirect += 3
        elif s.relevance == "medium":
            indirect += 1.5

    indirect = int(math.ceil(indirect))

    return {
        "direct": direct,
        "indirect": indirect,
        "total": direct + indirect,
    }


def _estimate_incremental_income(
    cluster: ClusterInfo,
    productive_demand_kwh_day: float,
    households: int,
) -> float:
    """Estimate per-household incremental annual income from productive use.

    Based on IFC/ESMAP evidence that electrified productive use adds
    USD 150-600 per household per year in sub-Saharan Africa, scaled
    by productive demand intensity.
    """
    if households <= 0:
        return 0.0

    # Base income uplift per household: USD 200/year (conservative Moz estimate)
    base_income = 200.0

    # Scale by productive demand intensity
    demand_per_hh = productive_demand_kwh_day / households
    # Typical range 0.1-1.0 kWh/hh/day → multiplier 0.5-2.0
    intensity_multiplier = min(max(demand_per_hh / 0.5, 0.5), 2.5)

    # Wealth-adjusted: wealthier areas convert energy access to income faster
    rwi = cluster.mean_rwi
    if rwi is not None:
        wealth_factor = 1.0 + max(min(rwi, 1.0), -1.0) * 0.2
    else:
        wealth_factor = 1.0

    return round(base_income * intensity_multiplier * wealth_factor, 0)


# ── Demand stimulation programme ───────────────────────────────────────


def _design_stimulation_programme(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    sectors: list[ProductiveUseSector],
) -> dict:
    """Design uptake targets, finance model, and aggregation strategy."""
    is_urban = cluster.is_urban
    rwi = cluster.mean_rwi
    pop = cluster.population

    # Uptake targets — peri-urban/urban areas adopt faster
    if is_urban >= 2:
        y1, y2, y3, y5 = 25, 40, 55, 75
    elif is_urban == 1:
        y1, y2, y3, y5 = 15, 30, 45, 65
    else:
        y1, y2, y3, y5 = 10, 20, 35, 55

    # Finance model selection
    if rwi is not None and rwi > 0:
        finance = "Operator equipment leasing with microfinance top-up"
    elif pop > 500:
        finance = "PAYGO for small appliances; operator leasing for productive equipment"
    else:
        finance = "PAYGO dominant with community group purchasing"

    # Aggregation strategy
    high_sectors = [s.sector for s in sectors if s.relevance == "high"]
    med_sectors = [s.sector for s in sectors if s.relevance == "medium"]

    if len(high_sectors) >= 2:
        aggregation = (
            f"Multi-sector demand aggregation anchored on "
            f"{', '.join(high_sectors[:3])}. "
            "Form producer cooperatives and bulk purchasing groups."
        )
    elif high_sectors:
        aggregation = (
            f"Single-sector anchor strategy focused on {high_sectors[0]}. "
            "Cross-sell to adjacent sectors "
            f"({', '.join(med_sectors[:2]) if med_sectors else 'ICT, cold chain'})."
        )
    else:
        aggregation = (
            "Broad-based demand stimulation through phone charging hubs, "
            "barber shops, and public service facilities as entry points. "
            "Gradually introduce productive equipment through demonstration."
        )

    return {
        "uptake_target_year_1_pct": y1,
        "uptake_target_year_2_pct": y2,
        "uptake_target_year_3_pct": y3,
        "uptake_target_year_5_pct": y5,
        "finance_model": finance,
        "demand_aggregation_strategy": aggregation,
    }


# ── Utilities ──────────────────────────────────────────────────────────


def _normalise_province(admin_region: Optional[str]) -> str:
    """Normalise province name for lookup."""
    if admin_region is None:
        return ""
    return admin_region.strip().lower()


def _load_config() -> dict:
    """Load productive-use config from JSON if available."""
    config_path = COUNTRY_DIR / "productive_use_config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}
