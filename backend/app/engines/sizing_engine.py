from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from app.schemas.site import ClusterInfo
from app.schemas.analysis import DemandEstimate, SolarResource, SystemSizing

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"

# ── 2-D sweep grid ──────────────────────────────────────────────────
PV_FACTORS = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]
BATT_FACTORS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
ILR = 1.20  # inverter loading ratio

# ── Battery dispatch parameters ─────────────────────────────────────
SOC_MIN = 0.20
SOC_MAX = 1.00
SOC_INIT = 0.50
C_RATE = 0.50
RT_EFFICIENCY = 0.92
DOD = 0.80

# ── LPSP thresholds by MTF tier ─────────────────────────────────────
LPSP_TARGETS = {1: 0.10, 2: 0.07, 3: 0.05, 4: 0.03, 5: 0.02}


# ── Public entry point ──────────────────────────────────────────────

def size_system(
    cluster: ClusterInfo,
    demand: DemandEstimate,
    solar: SolarResource,
    hourly_demand: list[float],
    hourly_solar: list[float],
    overrides: Optional[dict] = None,
) -> SystemSizing:
    """Size solar + battery system using HOMER-style 2-D enumeration.

    Sweeps 12 PV × 7 battery candidates, runs 8,760-hour dispatch for
    each, computes NPC/LCOE, and selects the candidate with the lowest
    LCOE that meets the LPSP threshold for the demand tier.
    """
    defaults = _load_defaults()
    overrides = overrides or {}
    costs = {**defaults, **overrides}
    pr = solar.performance_ratio

    peak_load = demand.peak_demand_kw
    if peak_load <= 0:
        return _fallback_sizing(cluster, demand)

    # ── Baselines ────────────────────────────────────────────────────
    psh = solar.annual_ghi_kwh_m2 / 365 * pr if solar.annual_ghi_kwh_m2 > 0 else 4.0
    pv_baseline = max(peak_load, demand.daily_energy_kwh * 1.12 / (psh * 0.78))

    evening_energy = _evening_energy(demand.load_profile_kw)
    batt_baseline = max(evening_energy / DOD, demand.daily_energy_kwh * 0.4)

    # ── LPSP target for the cluster's demand tier ────────────────────
    lpsp_target = LPSP_TARGETS.get(demand.demand_tier, 0.05)

    # ── 2-D enumeration ─────────────────────────────────────────────
    best_candidate = None
    best_lcoe = float("inf")
    best_fallback = None       # lowest LPSP if nothing meets target
    lowest_lpsp = float("inf")

    r = costs.get("discount_rate", 0.08)
    horizon = costs.get("project_lifetime_years", 20)

    for pvf in PV_FACTORS:
        for bf in BATT_FACTORS:
            pv_kwp = round(pv_baseline * pvf, 2)
            batt_kwh_nominal = round(batt_baseline * bf, 2)
            batt_kwh_usable = round(batt_kwh_nominal * DOD, 2)
            batt_kw = batt_kwh_nominal * C_RATE
            inv_kw = max(peak_load, pv_kwp / ILR, batt_kw + 0.3 * pv_kwp)

            result = _dispatch_8760(
                pv_kwp, batt_kwh_nominal, batt_kw, inv_kw,
                pr, hourly_solar, hourly_demand,
            )

            npc = _compute_npc(
                pv_kwp, batt_kwh_nominal, inv_kw,
                result["battery_cycles"], costs,
            )
            lcoe = _compute_lcoe(npc, result["total_served_kwh"], r, horizon)

            entry = {
                "pv_kwp": pv_kwp,
                "batt_kwh_nominal": batt_kwh_nominal,
                "batt_kwh_usable": batt_kwh_usable,
                "inv_kw": inv_kw,
                "result": result,
                "npc": npc,
                "lcoe": lcoe,
            }

            # Track best within LPSP constraint
            if result["lpsp"] <= lpsp_target and lcoe < best_lcoe:
                best_lcoe = lcoe
                best_candidate = entry

            # Track absolute lowest LPSP as fallback
            if result["lpsp"] < lowest_lpsp:
                lowest_lpsp = result["lpsp"]
                best_fallback = entry

    # ── Selection ────────────────────────────────────────────────────
    chosen = best_candidate if best_candidate is not None else best_fallback

    pv_kwp = chosen["pv_kwp"]
    batt_kwh_nominal = chosen["batt_kwh_nominal"]
    batt_kwh_usable = chosen["batt_kwh_usable"]
    inv_kw = chosen["inv_kw"]
    res = chosen["result"]

    # ── Distribution infra ───────────────────────────────────────────
    area_km2 = cluster.area_km2 if cluster.area_km2 > 0 else 0.5
    hh_count = demand.households
    lv_line_km = math.sqrt(area_km2) * 2 * math.ceil(hh_count / 300)
    service_transformers = max(1, math.ceil(peak_load / 50))
    meters = hh_count

    dc_ac_ratio = round(pv_kwp / inv_kw, 2) if inv_kw > 0 else 1.0
    annual_gen = res["total_generation_kwh"]
    annual_served = res["total_served_kwh"]
    cap_factor = round(annual_gen / (pv_kwp * 8760) * 100, 1) if pv_kwp > 0 else 0

    return SystemSizing(
        pv_kwp=round(pv_kwp, 2),
        battery_kwh_nominal=round(batt_kwh_nominal, 2),
        battery_kwh_usable=round(batt_kwh_usable, 2),
        inverter_kva=round(inv_kw, 2),
        lv_line_km=round(lv_line_km, 2),
        service_transformers=service_transformers,
        meters=meters,
        dc_ac_ratio=dc_ac_ratio,
        annual_generation_kwh=round(annual_gen, 0),
        annual_energy_served_kwh=round(annual_served, 0),
        unmet_energy_pct=round(res["unmet_pct"], 1),
        curtailment_pct=round(res["curtailment_pct"], 1),
        capacity_factor_pct=cap_factor,
        battery_cycles_per_year=round(res["battery_cycles"], 0),
    )


# ── Dispatch simulation ─────────────────────────────────────────────

def _dispatch_8760(
    pv_kwp: float,
    batt_kwh: float,
    batt_kw: float,
    inv_kw: float,
    pr: float,
    hourly_solar: list[float],
    hourly_demand: list[float],
) -> dict:
    """Run 8,760-hour dispatch for a PV + battery + inverter configuration."""
    eta_one_way = math.sqrt(RT_EFFICIENCY)
    soc = SOC_INIT * batt_kwh
    soc_low = SOC_MIN * batt_kwh
    soc_high = SOC_MAX * batt_kwh

    total_demand = 0.0
    total_generation = 0.0
    total_served = 0.0
    total_unmet = 0.0
    total_curtailment = 0.0
    energy_throughput = 0.0

    hours = min(len(hourly_solar), len(hourly_demand), 8760)

    for i in range(hours):
        pv_gen = pv_kwp * hourly_solar[i] * pr
        load_t = hourly_demand[i]
        total_demand += load_t
        total_generation += pv_gen

        # PV serves load directly, capped by inverter
        pv_to_load = min(pv_gen, inv_kw, load_t)
        residual_load = load_t - pv_to_load
        surplus_pv = pv_gen - pv_to_load

        # Battery discharge to cover residual load
        max_dis = min(batt_kw, (soc - soc_low) * eta_one_way, residual_load)
        batt_to_load = max(0.0, max_dis)
        soc -= batt_to_load / eta_one_way
        residual_load -= batt_to_load
        total_unmet += max(0.0, residual_load)

        # Surplus PV charges battery
        max_chg = min(batt_kw, (soc_high - soc) / eta_one_way, surplus_pv)
        batt_charge = max(0.0, max_chg)
        soc += batt_charge * eta_one_way
        surplus_pv -= batt_charge
        total_curtailment += max(0.0, surplus_pv)

        energy_throughput += batt_to_load + batt_charge
        total_served += load_t - max(0.0, residual_load)

        soc = max(soc_low, min(soc_high, soc))

    cycles = energy_throughput / (2 * batt_kwh) if batt_kwh > 0 else 0.0
    lpsp = total_unmet / total_demand if total_demand > 0 else 0.0
    curtailment_pct = total_curtailment / total_generation * 100 if total_generation > 0 else 0.0

    return {
        "total_demand_kwh": total_demand,
        "total_generation_kwh": total_generation,
        "total_served_kwh": total_served,
        "lpsp": lpsp,
        "unmet_pct": lpsp * 100,
        "curtailment_pct": curtailment_pct,
        "battery_cycles": cycles,
    }


# ── Economics ────────────────────────────────────────────────────────

def _compute_npc(
    pv_kwp: float,
    batt_kwh: float,
    inv_kw: float,
    annual_cycles: float,
    costs: dict,
) -> float:
    """Net present cost over project lifetime."""
    horizon = costs.get("project_lifetime_years", 20)
    r = costs.get("discount_rate", 0.08)

    capex = (
        pv_kwp * costs.get("pv_capex_per_kwp", 800)
        + batt_kwh * costs.get("batt_capex_per_kwh", 350)
        + inv_kw * costs.get("inv_capex_per_kw", 250)
    )

    annual_opex = capex * costs.get("opex_pct_of_capex", 0.025)
    opex_npv = sum(annual_opex / (1 + r) ** y for y in range(1, horizon + 1))

    cycle_life = costs.get("batt_cycle_life", 4000)
    total_cycles = annual_cycles * horizon
    replacements = total_cycles / cycle_life if cycle_life > 0 else 0
    replacement_cost = replacements * batt_kwh * costs.get("batt_capex_per_kwh", 350) * 0.6
    repl_npv = replacement_cost / (1 + r) ** (horizon / 2)

    salvage = (capex * 0.10) / (1 + r) ** horizon

    return capex + opex_npv + repl_npv - salvage


def _crf(rate: float, n_years: int) -> float:
    """Capital recovery factor."""
    if rate <= 0:
        return 1.0 / n_years
    return rate * (1 + rate) ** n_years / ((1 + rate) ** n_years - 1)


def _compute_lcoe(
    npc: float,
    annual_energy_served_kwh: float,
    r: float,
    horizon: int,
) -> float:
    """Levelised cost of energy (USD/kWh)."""
    if annual_energy_served_kwh <= 0:
        return 999.0
    return npc * _crf(r, horizon) / annual_energy_served_kwh


# ── Helpers ──────────────────────────────────────────────────────────

def _evening_energy(load_profile_kw: list[float]) -> float:
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
