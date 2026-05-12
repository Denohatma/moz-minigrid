from __future__ import annotations

import json
import math
from pathlib import Path

from app.schemas.site import ClusterInfo
from app.schemas.analysis import DemandEstimate, DistributionDesign, BoQItem

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

TERRAIN_MULTIPLIERS = {
    "flat": 1.10,
    "rolling": 1.25,
    "hilly": 1.40,
    "mountainous": 1.60,
}

CONDUCTORS = {
    "ABC_35mm2": {"resistance_ohm_per_km": 0.87},
    "ABC_16mm2": {"resistance_ohm_per_km": 1.91},
    "ACSR_Rabbit": {"resistance_ohm_per_km": 4.70},
}

POWER_FACTOR = 0.85
SPINE_PCT = 0.25
FEEDER_PCT = 0.45
SERVICE_PCT = 0.30


def _load_dist_defaults() -> dict:
    path = COUNTRY_DIR / "financial_defaults.json"
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("distribution", {})
    return {}


def design_distribution(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    overrides: dict | None = None,
) -> DistributionDesign:
    """Design LV distribution network using radial estimation.

    Estimates total line length, compiles a bill of quantities, and
    calculates voltage drop and technical losses.
    """
    overrides = overrides or {}
    cfg = _load_dist_defaults()
    warnings: list[str] = []

    n_customers = demand.households
    peak_kw = demand.peak_demand_kw
    terrain = overrides.get("terrain", "rolling")
    terrain_mult = TERRAIN_MULTIPLIERS.get(terrain, 1.25)

    pole_cost = cfg.get("pole_cost_usd", 85)
    pole_span = cfg.get("pole_span_m", 40)
    service_drop_cost = cfg.get("service_drop_cost_usd", 175)
    meter_cost = cfg.get("meter_cost_usd", 45)
    protection_pct = cfg.get("protection_pct", 0.06)
    construction_base_pct = cfg.get("construction_labour_base_pct", 0.30)
    soft_cost_pct = cfg.get("soft_cost_pct", 0.12)

    conductor_costs = {
        "ABC_35mm2": cfg.get("conductor_cost_abc35_per_km", 3800),
        "ABC_16mm2": cfg.get("conductor_cost_abc16_per_km", 2200),
        "ACSR_Rabbit": cfg.get("conductor_cost_service_per_km", 1400),
    }

    line_per_customer_m = 25
    spine_overhead = 1.20
    total_line_m = round(n_customers * line_per_customer_m * spine_overhead * terrain_mult, 0)
    warnings.append(
        f"Radial estimation: {n_customers} connections × {line_per_customer_m}m "
        f"× {spine_overhead} overhead × {terrain_mult} terrain"
    )

    spine_m = total_line_m * SPINE_PCT
    feeder_m = total_line_m * FEEDER_PCT
    service_m = total_line_m * SERVICE_PCT

    boq: list[BoQItem] = []

    line_segments = [
        ("ABC_35mm2", spine_m, "Spine conductor"),
        ("ABC_16mm2", feeder_m, "Feeder conductor"),
        ("ACSR_Rabbit", service_m, "Service conductor"),
    ]
    for cond_key, length_m, desc in line_segments:
        cost_per_km = conductor_costs[cond_key]
        cost = length_m / 1000 * cost_per_km
        boq.append(BoQItem(
            category="conductor",
            description=f"{cond_key} — {desc}",
            unit="km",
            quantity=round(length_m / 1000, 2),
            unit_cost_usd=cost_per_km,
            total_cost_usd=round(cost, 0),
        ))

    pole_count = max(1, int(math.ceil(total_line_m / pole_span)))
    boq.append(BoQItem(
        category="pole",
        description="Treated wood pole 8m",
        unit="unit",
        quantity=pole_count,
        unit_cost_usd=pole_cost,
        total_cost_usd=round(pole_count * pole_cost, 0),
    ))

    boq.append(BoQItem(
        category="service_drop",
        description="Service drop + meter",
        unit="connection",
        quantity=n_customers,
        unit_cost_usd=service_drop_cost + meter_cost,
        total_cost_usd=round(n_customers * (service_drop_cost + meter_cost), 0),
    ))

    materials_cost = sum(item.total_cost_usd for item in boq)

    protection_cost = round(materials_cost * protection_pct, 0)
    boq.append(BoQItem(
        category="protection",
        description="Fuses, surge arresters, earthing",
        unit="lump sum",
        quantity=1,
        unit_cost_usd=protection_cost,
        total_cost_usd=protection_cost,
    ))

    subtotal = materials_cost + protection_cost
    construction = round(subtotal * (terrain_mult - 1 + construction_base_pct), 0)
    boq.append(BoQItem(
        category="construction",
        description=f"Labour, transport, supervision ({terrain_mult}x terrain)",
        unit="lump sum",
        quantity=1,
        unit_cost_usd=construction,
        total_cost_usd=construction,
    ))

    hard_cost = subtotal + construction
    soft_cost = round(hard_cost * soft_cost_pct, 0)
    boq.append(BoQItem(
        category="soft_costs",
        description="Permitting, design, owner's engineer",
        unit="lump sum",
        quantity=1,
        unit_cost_usd=soft_cost,
        total_cost_usd=soft_cost,
    ))

    total_cost = hard_cost + soft_cost
    cost_per_conn = round(total_cost / n_customers, 0) if n_customers > 0 else 0

    v_drop_pct = _estimate_voltage_drop(total_line_m, peak_kw, n_customers)
    tech_losses = round((0.04 + 0.02 * (total_line_m / 1000)) * 100, 1)

    return DistributionDesign(
        total_line_length_m=total_line_m,
        pole_count=pole_count,
        bill_of_quantities=boq,
        total_network_cost_usd=round(total_cost, 0),
        cost_per_connection_usd=cost_per_conn,
        voltage_drop_max_pct=round(v_drop_pct, 1),
        technical_losses_pct=tech_losses,
        method_used="radial_estimate",
        customers_connected=n_customers,
        construction_multiplier=terrain_mult,
        warnings=warnings,
    )


def _estimate_voltage_drop(
    total_line_m: float, peak_kw: float, n_customers: int
) -> float:
    feeders = max(1, n_customers // 80)
    avg_feeder_km = (total_line_m * FEEDER_PCT / feeders) / 1000
    current = peak_kw / (math.sqrt(3) * 0.4 * POWER_FACTOR) / feeders
    resistance = CONDUCTORS["ABC_16mm2"]["resistance_ohm_per_km"]
    v_drop_v = current * resistance * avg_feeder_km
    v_drop_pct = v_drop_v / 400 * 100
    return min(v_drop_pct, 15.0)
