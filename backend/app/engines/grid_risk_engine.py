from __future__ import annotations

from typing import Optional

from app.schemas.site import ClusterInfo
from app.schemas.analysis import (
    EsmapScenario,
    FinancialResults,
    GridArrivalScenario,
    GridRiskAssessment,
)

ESMAP_SCENARIOS = [
    ("no_arrival", "No Arrival — Full standalone minigrid"),
    ("overlap_risk", "Overlap Risk — Transitional minigrid with timeline"),
    ("compensation_exit", "Compensation & Exit — Negotiated buyout terms"),
    ("side_by_side", "Side-by-Side — Embedded generation post-grid"),
    ("distributor_conversion", "Distributor Conversion — Local distribution licence"),
    ("producer_conversion", "Producer Conversion — Wholesale generator to utility"),
    ("hybrid_interconnection", "Hybrid Interconnection — Grid-tied from day one"),
]

WEIGHTS = {
    "timeline_certainty": 0.30,
    "financial_viability": 0.25,
    "regulatory_alignment": 0.20,
    "implementation_complexity": 0.15,
    "stakeholder_acceptability": 0.10,
}


def assess_grid_risk(
    cluster: ClusterInfo,
    financial: FinancialResults,
) -> GridRiskAssessment:
    """Assess grid arrival risk with distance-based classification and ESMAP scenario scoring."""
    dist_mv = cluster.dist_grid_mv_km
    dist_hv = cluster.dist_grid_hv_km or (dist_mv + 20.0)
    dist_planned = cluster.dist_grid_planned_km

    risk_level, risk_label = _classify_risk(dist_mv, dist_hv, dist_planned)

    scenarios = None
    if risk_level in ("critical", "high"):
        scenarios = _model_grid_arrival_scenarios(financial)

    esmap_scores = _score_esmap_scenarios(dist_mv, dist_hv, dist_planned)
    best = esmap_scores[0] if esmap_scores else None

    design_implications = _derive_design_implications(risk_level, dist_planned)

    return GridRiskAssessment(
        dist_mv_km=dist_mv,
        dist_hv_km=dist_hv,
        risk_level=risk_level,
        risk_label=risk_label,
        scenarios=scenarios,
        esmap_recommended=best.scenario if best else None,
        esmap_scores=esmap_scores,
        design_implications=design_implications,
    )


def _classify_risk(
    dist_mv: float, dist_hv: float, dist_planned: Optional[float] = None
) -> tuple[str, str]:
    if dist_mv < 5:
        return "critical", "Grid extension likely cheaper"
    if dist_planned and dist_planned < 5:
        return "high", "Planned transmission line within 5 km"
    if dist_mv < 15 and dist_hv < 30:
        return "high", "Grid may arrive within 10 years"
    if dist_planned and dist_planned < 15:
        return "medium", "Planned grid line within 15 km"
    if dist_mv < 30 and dist_hv < 50:
        return "medium", "Grid possible within 20 years"
    return "low", "Outside EDM 30km mandate"


def _score_esmap_scenarios(
    dist_mv: float, dist_hv: float, dist_planned: Optional[float]
) -> list[EsmapScenario]:
    """Score 7 ESMAP grid-arrival scenarios using distance-derived evidence.

    Since DRE Atlas doesn't have funding/contractor data, we infer grid
    arrival likelihood from MV/HV/planned distances.
    """
    grid_imminent = dist_mv < 5
    grid_likely = dist_mv < 15 or (dist_planned is not None and dist_planned < 10)
    grid_aspirational = dist_planned is not None and dist_planned < 30 and not grid_likely
    no_evidence = not grid_imminent and not grid_likely and not grid_aspirational

    base_scores = {
        "no_arrival": {
            "tc": 8 if (grid_aspirational or no_evidence) else (4 if grid_likely else 2),
            "fv": 8, "ra": 7, "ic": 9,
            "sa": 4 if grid_imminent else 7,
        },
        "overlap_risk": {
            "tc": 6 if grid_aspirational else (7 if grid_likely else 3),
            "fv": 6, "ra": 7, "ic": 7, "sa": 7,
        },
        "compensation_exit": {
            "tc": 5, "fv": 5, "ra": 6, "ic": 5, "sa": 6,
        },
        "side_by_side": {
            "tc": 5, "fv": 6, "ra": 6, "ic": 5, "sa": 7,
        },
        "distributor_conversion": {
            "tc": 4, "fv": 5, "ra": 5, "ic": 4, "sa": 6,
        },
        "producer_conversion": {
            "tc": 4, "fv": 4, "ra": 4, "ic": 4, "sa": 5,
        },
        "hybrid_interconnection": {
            "tc": 8 if grid_imminent else 3,
            "fv": 7 if grid_imminent else 4,
            "ra": 5,
            "ic": 3,
            "sa": 7 if grid_imminent else 5,
        },
    }

    results: list[EsmapScenario] = []
    for key, label in ESMAP_SCENARIOS:
        s = base_scores[key]
        tc = s["tc"]
        fv = s["fv"]
        ra = s["ra"]
        ic = s["ic"]
        sa = s["sa"]

        weighted = (
            tc * WEIGHTS["timeline_certainty"]
            + fv * WEIGHTS["financial_viability"]
            + ra * WEIGHTS["regulatory_alignment"]
            + ic * WEIGHTS["implementation_complexity"]
            + sa * WEIGHTS["stakeholder_acceptability"]
        )
        results.append(EsmapScenario(
            scenario=key,
            label=label,
            weighted_score=round(weighted, 2),
            timeline_certainty=tc,
            financial_viability=fv,
            regulatory_alignment=ra,
            implementation_complexity=ic,
            stakeholder_acceptability=sa,
        ))

    results.sort(key=lambda x: x.weighted_score, reverse=True)
    return results


def _derive_design_implications(risk_level: str, dist_planned: Optional[float]) -> str:
    if risk_level == "critical":
        return (
            "Grid extension may be more cost-effective. If proceeding with minigrid, "
            "design for grid-tied operation from day one. Size to complement grid supply."
        )
    if risk_level == "high":
        return (
            "Design primarily as standalone with grid-forming inverter capable of "
            "future interconnection. Monitor EDM grid extension progress quarterly."
        )
    if risk_level == "medium":
        return (
            "Full standalone system recommended. Include grid-ready provisions in "
            "inverter specification. Review grid extension status annually."
        )
    return (
        "Full standalone minigrid. Grid arrival unlikely within project lifetime. "
        "No grid-interconnection provisions needed."
    )


def _model_grid_arrival_scenarios(
    financial: FinancialResults,
) -> list[GridArrivalScenario]:
    capex = financial.total_capex_usd
    cash_flows_full = financial.cash_flow

    scenarios = []
    for arrival_year in [5, 10]:
        truncated = [cf for cf in cash_flows_full if cf.year <= arrival_year]
        if not truncated:
            continue

        cumulative_at_arrival = truncated[-1].cumulative
        investment_recovered = (capex + cumulative_at_arrival) / capex if capex > 0 else 0

        flows = [-capex] + [cf.net_cash_flow for cf in truncated]
        adjusted_irr = _irr(flows) * 100

        adjusted_npv = -capex
        for i, cf in enumerate(truncated, 1):
            adjusted_npv += cf.net_cash_flow / (1.10 ** i)

        scenarios.append(GridArrivalScenario(
            arrival_year=arrival_year,
            adjusted_irr=round(adjusted_irr, 2),
            adjusted_npv=round(adjusted_npv, 2),
            investment_recovered_pct=round(investment_recovered * 100, 1),
        ))

    return scenarios


def _irr(cash_flows: list[float], max_iter: int = 200, tol: float = 1e-6) -> float:
    rate = 0.10
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        d_npv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(d_npv) < 1e-12:
            break
        new_rate = rate - npv / d_npv
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
        rate = max(min(rate, 2.0), -0.99)
    return rate
