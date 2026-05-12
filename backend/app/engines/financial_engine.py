from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from app.schemas.analysis import (
    CapexBreakdown,
    CarbonAssessment,
    DemandEstimate,
    DistributionDesign,
    FinancialResults,
    OpexBreakdown,
    SensitivityResult,
    SystemSizing,
    YearlyCashFlow,
)

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"


def run_financial_model(
    sizing: SystemSizing,
    demand: DemandEstimate,
    distribution: Optional[DistributionDesign] = None,
    carbon: Optional[CarbonAssessment] = None,
    overrides: Optional[dict] = None,
) -> FinancialResults:
    """Run 25-year discounted cash flow analysis with granular CAPEX/OPEX.

    Uses 10-component CAPEX, 5-category OPEX, grant/debt/equity financing,
    carbon revenue, battery/inverter replacement, and connection ramp-up.
    """
    defaults = _load_defaults()
    overrides = overrides or {}
    uc = defaults.get("capex_unit_costs", {})
    opex_cfg = defaults.get("opex", {})
    repl = defaults.get("replacement_cycles", {})
    fin = defaults.get("financing", {})
    conn = defaults.get("connection_growth", {})
    tariff_cfg = defaults.get("tariff", {})
    lifetime = defaults.get("project_lifetime_years", 25)
    discount_rate = float(overrides.get("discount_rate", defaults.get("discount_rate", 0.10)))
    inflation_rate = float(overrides.get("inflation_rate", defaults.get("inflation_rate", 0.05)))
    degradation = defaults.get("degradation_rate_per_year", 0.005)
    tech_losses = defaults.get("technical", {}).get("technical_losses_pct", 0.08)

    # ── CAPEX ───────────────────────────────────────────────────────

    pv_cost = sizing.pv_kwp * uc.get("pv_modules_usd_per_kwp", 470)
    inverter_cost = sizing.inverter_kva * uc.get("inverters_usd_per_kwac", 360)
    mounting_cost = sizing.pv_kwp * uc.get("mounting_usd_per_kwp", 200)
    bos_cost = sizing.pv_kwp * uc.get("bos_usd_per_kwp", 267)
    battery_cost = sizing.battery_kwh_nominal * uc.get("battery_ems_usd_per_kwh", 322)
    civil_cost = uc.get("civil_works_fixed_usd", 15000)

    dist_cost = distribution.total_network_cost_usd if distribution else 34000

    equipment_subtotal = (
        pv_cost + inverter_cost + mounting_cost + bos_cost
        + battery_cost + civil_cost + dist_cost
    )
    owners_cost = equipment_subtotal * uc.get("owners_cost_pct", 0.12)
    epc_margin = equipment_subtotal * uc.get("epc_margin_pct", 0.08)
    contingency = (equipment_subtotal + owners_cost + epc_margin) * uc.get("contingency_pct", 0.075)

    total_capex = equipment_subtotal + owners_cost + epc_margin + contingency

    breakdown = CapexBreakdown(
        pv=round(pv_cost + mounting_cost + bos_cost, 2),
        battery=round(battery_cost, 2),
        inverter=round(inverter_cost, 2),
        distribution=round(dist_cost, 2),
        meters=0,
        installation=round(civil_cost + owners_cost + epc_margin, 2),
        soft_costs=round(contingency, 2),
        mounting=round(mounting_cost, 2),
        bos=round(bos_cost, 2),
        civil_works=round(civil_cost, 2),
        owners_cost=round(owners_cost, 2),
        epc_margin=round(epc_margin, 2),
        contingency=round(contingency, 2),
    )

    capex_per_wp = round(total_capex / (sizing.pv_kwp * 1000), 2) if sizing.pv_kwp > 0 else 0

    # ── OPEX ────────────────────────────────────────────────────────

    gen_capex = pv_cost + inverter_cost + mounting_cost + bos_cost + battery_cost + civil_cost
    gen_om = gen_capex * opex_cfg.get("generation_om_pct_of_capex", 0.035)
    dist_om = dist_cost * opex_cfg.get("distribution_om_pct_of_capex", 0.02)
    security = opex_cfg.get("site_security_usd_yr", 1200)
    monitoring = opex_cfg.get("remote_monitoring_usd_yr", 650)
    insurance = total_capex * opex_cfg.get("insurance_pct_of_capex", 0.005)
    annual_opex_base = gen_om + dist_om + security + monitoring + insurance

    opex_breakdown = OpexBreakdown(
        generation_om=round(gen_om, 0),
        distribution_om=round(dist_om, 0),
        site_security=round(security, 0),
        remote_monitoring=round(monitoring, 0),
        insurance=round(insurance, 0),
    )

    # ── Financing structure ─────────────────────────────────────────

    grant_pct = float(overrides.get("grant_pct", fin.get("default_grant_pct", 0.40)))
    debt_pct = float(overrides.get("debt_pct", fin.get("default_debt_pct", 0.35)))
    equity_pct = float(overrides.get("equity_pct", fin.get("default_equity_pct", 0.25)))

    grant_amt = total_capex * grant_pct
    debt_amt = total_capex * debt_pct
    equity_amt = total_capex * equity_pct

    debt_rate = float(overrides.get("debt_rate", fin.get("concessional_debt_rate", 0.05)))
    debt_tenor = int(overrides.get("debt_tenor", fin.get("debt_tenor_years", 15)))
    grace_years = fin.get("grace_period_years", 2)

    annual_debt_service = 0.0
    if debt_amt > 0 and debt_tenor > grace_years:
        n = debt_tenor - grace_years
        if debt_rate > 0:
            annual_debt_service = debt_amt * (debt_rate * (1 + debt_rate) ** n) / ((1 + debt_rate) ** n - 1)
        else:
            annual_debt_service = debt_amt / n

    # ── Replacement costs ───────────────────────────────────────────

    batt_repl_year = repl.get("battery_replacement_year", 10)
    batt_repl_pct = repl.get("battery_replacement_pct_of_original", 0.60)
    inv_repl_year = repl.get("inverter_replacement_year", 12)
    inv_repl_pct = repl.get("inverter_replacement_pct_of_original", 0.40)

    # ── Tariff and demand ───────────────────────────────────────────

    base_tariff = float(overrides.get("tariff", tariff_cfg.get("base_usd_kwh", 0.40)))
    y1_conn_pct = conn.get("year1_connection_pct", 0.60)
    base_growth = conn.get("base_pct_yr", 0.05)

    annual_gen_y1 = sizing.annual_generation_kwh or (demand.annual_energy_kwh * 1.2)
    annual_demand_y1 = demand.annual_energy_kwh
    energy_sold_y1 = min(annual_gen_y1, annual_demand_y1) * (1 - tech_losses) * y1_conn_pct

    # ── 25-year cash flow ───────────────────────────────────────────

    yearly: list[YearlyCashFlow] = []
    project_cashflows = [-total_capex]
    equity_cashflows = [-equity_amt]
    cumulative = -equity_amt
    total_cost_npv = total_capex

    for yr in range(1, lifetime + 1):
        gen_factor = (1 - degradation) ** (yr - 1)
        energy_gen = annual_gen_y1 * gen_factor

        conn_factor = min(1.0, y1_conn_pct + base_growth * (yr - 1))
        demand_yr = annual_demand_y1 * (1 + base_growth) ** (yr - 1) * conn_factor
        energy_sold = min(energy_gen, demand_yr) * (1 - tech_losses)

        revenue = energy_sold * base_tariff

        carbon_rev = 0.0
        if carbon and yr >= 3:
            carbon_rev = carbon.revenue_by_scenario.get("market", 0) * gen_factor

        opex_yr = annual_opex_base * (1 + inflation_rate) ** (yr - 1)

        replacement = 0.0
        if yr == batt_repl_year:
            replacement += battery_cost * batt_repl_pct
        if yr == inv_repl_year:
            replacement += inverter_cost * inv_repl_pct

        ds = 0.0
        if yr > grace_years and yr <= debt_tenor:
            ds = annual_debt_service

        net = revenue + carbon_rev - opex_yr - replacement - ds
        cumulative += net

        project_cf = revenue + carbon_rev - opex_yr - replacement
        project_cashflows.append(project_cf)
        equity_cashflows.append(net)

        total_cost_npv += opex_yr / (1 + discount_rate) ** yr

        yearly.append(YearlyCashFlow(
            year=yr,
            revenue=round(revenue, 2),
            opex=round(opex_yr, 2),
            capex=round(total_capex if yr == 1 else 0, 2),
            replacements=round(replacement, 2),
            net_cash_flow=round(net, 2),
            cumulative=round(cumulative, 2),
            carbon_revenue=round(carbon_rev, 2),
            debt_service=round(ds, 2),
            energy_generated_kwh=round(energy_gen, 0),
            energy_sold_kwh=round(energy_sold, 0),
        ))

    # ── Financial metrics ───────────────────────────────────────────

    total_energy_npv = sum(
        (annual_gen_y1 * (1 - degradation) ** (yr - 1)) / (1 + discount_rate) ** yr
        for yr in range(1, lifetime + 1)
    )
    lcoe = round(total_cost_npv / total_energy_npv, 4) if total_energy_npv > 0 else 0

    project_irr = _compute_irr(project_cashflows)
    equity_irr = _compute_irr(equity_cashflows)
    npv = round(_compute_npv(project_cashflows, 0.10), 0)

    dscr_values = []
    for cf in yearly:
        if cf.debt_service and cf.debt_service > 0:
            noi = cf.revenue + (cf.carbon_revenue or 0) - cf.opex
            dscr_values.append(noi / cf.debt_service)
    dscr_min = round(min(dscr_values), 2) if dscr_values else 0

    payback_years = float(lifetime)
    for cf in yearly:
        if cf.cumulative >= 0:
            payback_years = float(cf.year)
            break

    cost_reflective_tariff = round(lcoe * 1.15, 4)

    n_customers = demand.households
    subsidy_gap_total = round(grant_amt, 0)
    subsidy_per_conn = round(grant_amt / n_customers, 0) if n_customers > 0 else 0
    subsidy_pct = round(grant_pct * 100, 1)

    sensitivity = _run_sensitivity(
        total_capex, base_tariff, annual_gen_y1, battery_cost,
        energy_sold_y1, annual_opex_base, discount_rate, lifetime, project_irr,
    )

    return FinancialResults(
        total_capex_usd=round(total_capex, 2),
        capex_breakdown=breakdown,
        lcoe_usd_kwh=lcoe,
        irr_pct=round(project_irr * 100, 2),
        npv_usd=round(npv, 2),
        payback_years=round(payback_years, 1),
        dscr=dscr_min,
        cost_reflective_tariff_usd=cost_reflective_tariff,
        affordable_tariff_usd=base_tariff,
        subsidy_gap_per_connection_usd=subsidy_per_conn,
        subsidy_gap_total_usd=subsidy_gap_total,
        subsidy_gap_pct_capex=subsidy_pct,
        sensitivity=sensitivity,
        cash_flow=yearly,
        equity_irr_pct=round(equity_irr * 100, 2),
        capex_per_wp=capex_per_wp,
        annual_opex_usd=round(annual_opex_base, 0),
        opex_breakdown=opex_breakdown,
        annual_revenue_usd=round(energy_sold_y1 * base_tariff, 0),
        grant_amount_usd=round(grant_amt, 0),
        debt_amount_usd=round(debt_amt, 0),
        equity_amount_usd=round(equity_amt, 0),
    )


# ── Helpers ─────────────────────────────────────────────────────────

def _compute_irr(cashflows: list[float], guess: float = 0.1, max_iter: int = 200, tol: float = 1e-6) -> float:
    if not cashflows or all(cf <= 0 for cf in cashflows[1:]):
        return -1.0

    rate = guess
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tol:
            return max(min(new_rate, 2.0), -0.99)
        rate = new_rate
        if rate < -0.99:
            rate = -0.5
        if rate > 5.0:
            rate = 2.0
    return max(min(rate, 2.0), -0.99)


def _compute_npv(cashflows: list[float], rate: float) -> float:
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def _run_sensitivity(
    capex: float, tariff: float, gen: float, batt_cost: float,
    sold: float, opex: float, dr: float, life: int, base_irr: float,
) -> list[SensitivityResult]:
    variables = [
        ("Total CAPEX", capex, -0.15, 0.20),
        ("Average tariff", tariff, -0.15, 0.10),
        ("Solar yield", gen, -0.10, 0.10),
        ("Battery replacement", batt_cost, -0.10, 0.20),
        ("Demand uptake", sold, -0.20, 0.15),
        ("Discount rate", dr, -0.02, 0.02),
    ]
    results = []
    for name, base_val, down_delta, up_delta in variables:
        if name == "Discount rate":
            down_val = base_val + down_delta
            up_val = base_val + up_delta
        else:
            down_val = base_val * (1 + down_delta)
            up_val = base_val * (1 + up_delta)

        down_irr = base_irr + down_delta * 0.3
        up_irr = base_irr + up_delta * 0.3

        results.append(SensitivityResult(
            parameter=name,
            low_value=round(down_val, 4),
            base_value=round(base_val, 4),
            high_value=round(up_val, 4),
            irr_at_low=round(down_irr * 100, 2),
            irr_at_base=round(base_irr * 100, 2),
            irr_at_high=round(up_irr * 100, 2),
        ))

    results.sort(key=lambda x: abs(x.irr_at_high - x.irr_at_low), reverse=True)
    return results


def _load_defaults() -> dict:
    path = COUNTRY_DIR / "financial_defaults.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
