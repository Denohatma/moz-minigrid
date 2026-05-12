from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from app.schemas.site import ClusterInfo
from app.schemas.analysis import DemandEstimate, SolarResource, SystemSizing

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

PV_MULTIPLIERS = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]

SOC_MIN = 0.20
SOC_MAX = 1.00
SOC_INITIAL = 0.50
C_RATE = 0.50
RT_EFFICIENCY = 0.92
AUTONOMY_HOURS = 3.5
DOD = 0.80


def size_system(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    solar: SolarResource,
    hourly_demand: list[float],
    hourly_solar: list[float],
    overrides: Optional[dict] = None,
) -> SystemSizing:
    """Size solar + battery system using 8,760-hour dispatch simulation.

    Sweeps PV candidates from 0.8x to 2.0x the peak load, simulates
    each with hourly dispatch, and selects the candidate that minimises
    a weighted score of unmet demand, curtailment, and PV size.
    """
    defaults = _load_defaults()
    overrides = overrides or {}
    pr = solar.performance_ratio

    peak_load = demand.peak_demand_kw
    if peak_load <= 0:
        return _fallback_sizing(cluster, demand)

    non_solar_kwh = _non_solar_energy(demand.load_profile_kw)
    battery_kwh_usable = round(non_solar_kwh * 1.15, 1)
    battery_kwh_nominal = round(battery_kwh_usable / DOD, 1)

    if battery_kwh_nominal < 2:
        battery_kwh_nominal = max(demand.daily_energy_kwh * 0.4, 2.0)
        battery_kwh_usable = round(battery_kwh_nominal * DOD, 1)

    psh = solar.annual_ghi_kwh_m2 / 365 * pr if solar.annual_ghi_kwh_m2 > 0 else 4.0
    energy_balance_pv = demand.daily_energy_kwh * 1.3 / psh
    pv_base = max(peak_load, energy_balance_pv)
    candidates = [round(pv_base * m, 1) for m in PV_MULTIPLIERS]

    best_pv = candidates[2]
    best_score = float("inf")
    best_result: Optional[dict] = None

    for pv_kwp in candidates:
        result = _dispatch_8760(
            pv_kwp, battery_kwh_nominal, pr, hourly_solar, hourly_demand
        )
        score = result["unmet_pct"] * 10 + result["curtailment_pct"] * 2 + pv_kwp * 0.1

        if result["unmet_pct"] <= 5.0 and score < best_score:
            best_score = score
            best_pv = pv_kwp
            best_result = result

    if best_result is None:
        best_pv = candidates[-1]
        best_result = _dispatch_8760(
            best_pv, battery_kwh_nominal, pr, hourly_solar, hourly_demand
        )

    inverter_kva = round(max(peak_load, best_pv * 0.83), 1)

    area_km2 = cluster.area_km2 if cluster.area_km2 > 0 else 0.5
    hh_count = demand.households
    lv_line_km = math.sqrt(area_km2) * 2 * math.ceil(hh_count / 300)
    service_transformers = max(1, math.ceil(peak_load / 50))
    meters = hh_count

    dc_ac_ratio = round(best_pv / inverter_kva, 2) if inverter_kva > 0 else 1.0
    annual_gen = best_result["total_generation_kwh"]
    annual_served = best_result["total_served_kwh"]
    cap_factor = round(annual_gen / (best_pv * 8760) * 100, 1) if best_pv > 0 else 0

    return SystemSizing(
        pv_kwp=round(best_pv, 2),
        battery_kwh_nominal=round(battery_kwh_nominal, 2),
        battery_kwh_usable=round(battery_kwh_usable, 2),
        inverter_kva=round(inverter_kva, 2),
        lv_line_km=round(lv_line_km, 2),
        service_transformers=service_transformers,
        meters=meters,
        dc_ac_ratio=dc_ac_ratio,
        annual_generation_kwh=round(annual_gen, 0),
        annual_energy_served_kwh=round(annual_served, 0),
        unmet_energy_pct=round(best_result["unmet_pct"], 1),
        curtailment_pct=round(best_result["curtailment_pct"], 1),
        capacity_factor_pct=cap_factor,
        battery_cycles_per_year=round(best_result["battery_cycles"], 0),
    )


def _dispatch_8760(
    pv_kwp: float,
    battery_kwh: float,
    pr: float,
    hourly_solar: list[float],
    hourly_demand: list[float],
) -> dict:
    """Run 8,760-hour dispatch simulation for a given PV + battery configuration."""
    soc = SOC_INITIAL
    max_charge_kw = battery_kwh * C_RATE
    max_discharge_kw = battery_kwh * C_RATE

    total_demand = 0.0
    total_generation = 0.0
    total_served = 0.0
    total_unmet = 0.0
    total_curtailment = 0.0
    charge_cycles = 0.0

    hours = min(len(hourly_solar), len(hourly_demand), 8760)

    for i in range(hours):
        solar_gen = pv_kwp * hourly_solar[i] * pr
        demand_kw = hourly_demand[i]
        total_demand += demand_kw
        total_generation += solar_gen

        net = solar_gen - demand_kw

        if net >= 0:
            headroom = (SOC_MAX - soc) * battery_kwh
            charge_kw = min(net, max_charge_kw, headroom)
            soc += charge_kw / battery_kwh if battery_kwh > 0 else 0
            charge_cycles += charge_kw / battery_kwh if battery_kwh > 0 else 0
            curtailed = net - charge_kw
            total_curtailment += curtailed
            total_served += demand_kw
        else:
            deficit = -net
            available = (soc - SOC_MIN) * battery_kwh * RT_EFFICIENCY
            discharge_kw = min(deficit, max_discharge_kw, available)
            if battery_kwh > 0:
                soc -= discharge_kw / (battery_kwh * RT_EFFICIENCY)
            served = solar_gen + discharge_kw
            unmet = max(0, demand_kw - served)
            total_served += served
            total_unmet += unmet

        soc = max(SOC_MIN, min(SOC_MAX, soc))

    unmet_pct = (total_unmet / total_demand * 100) if total_demand > 0 else 0
    curtailment_pct = (total_curtailment / total_generation * 100) if total_generation > 0 else 0

    return {
        "total_demand_kwh": total_demand,
        "total_generation_kwh": total_generation,
        "total_served_kwh": total_served,
        "unmet_pct": unmet_pct,
        "curtailment_pct": curtailment_pct,
        "battery_cycles": charge_cycles,
    }


def _non_solar_energy(load_profile_kw: list[float]) -> float:
    """Total energy demand during non-solar hours (18:00-05:00)."""
    if len(load_profile_kw) < 24:
        return sum(load_profile_kw) * 0.45
    return sum(load_profile_kw[18:24]) + sum(load_profile_kw[0:6])


def _fallback_sizing(cluster: ClusterInfo, demand: DemandEstimate) -> SystemSizing:
    """Simple sizing when dispatch simulation inputs are unavailable."""
    psh = (cluster.pv_kwh_kwp_year or cluster.ghi_kwh_m2_year or 1800) / 365
    pv_kwp = demand.daily_energy_kwh * 1.3 / (psh * 0.77)
    evening_frac = 0.4
    battery_kwh_nominal = demand.daily_energy_kwh * evening_frac * 1.5 / 0.80
    battery_kwh_usable = battery_kwh_nominal * 0.80
    inverter_kva = demand.peak_demand_kw / 0.85 * 1.25
    area_km2 = cluster.area_km2 if cluster.area_km2 > 0 else 0.5
    lv_line_km = math.sqrt(area_km2) * 2 * math.ceil(demand.households / 300)

    return SystemSizing(
        pv_kwp=round(pv_kwp, 2),
        battery_kwh_nominal=round(battery_kwh_nominal, 2),
        battery_kwh_usable=round(battery_kwh_usable, 2),
        inverter_kva=round(inverter_kva, 2),
        lv_line_km=round(lv_line_km, 2),
        service_transformers=max(1, math.ceil(demand.peak_demand_kw / 50)),
        meters=demand.households,
    )


def _load_defaults() -> dict:
    path = COUNTRY_DIR / "financial_defaults.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
