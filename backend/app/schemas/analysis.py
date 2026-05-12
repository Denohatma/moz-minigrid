from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from app.schemas.site import SiteCoordinates, ClusterInfo, SuitabilityScreening


# ── Demand ──────────────────────────────────────────────────────────

class DemandEstimate(BaseModel):
    households: int
    demand_tier: int = Field(ge=1, le=5)
    daily_energy_kwh: float
    peak_demand_kw: float
    annual_energy_kwh: float
    load_profile_kw: list[float] = Field(description="24-hour load profile (kW per hour)")
    persons_per_hh: float


# ── Solar Resource ──────────────────────────────────────────────────

class SolarResource(BaseModel):
    monthly_ghi_kwh_m2: list[float] = Field(description="12 monthly GHI values")
    monthly_dni_kwh_m2: list[float] = Field(default_factory=list)
    monthly_temp_c: list[float] = Field(default_factory=list)
    annual_ghi_kwh_m2: float
    optimal_tilt_deg: float = 0.0
    specific_yield_kwh_per_kwp: float = 0.0
    performance_ratio: float = 0.77
    loss_breakdown: dict = Field(default_factory=dict)
    data_source: str = ""


# ── System Sizing ───────────────────────────────────────────────────

class SystemSizing(BaseModel):
    pv_kwp: float
    battery_kwh_nominal: float
    battery_kwh_usable: float
    inverter_kva: float
    lv_line_km: float
    service_transformers: int
    meters: int
    dc_ac_ratio: Optional[float] = None
    annual_generation_kwh: Optional[float] = None
    annual_energy_served_kwh: Optional[float] = None
    unmet_energy_pct: Optional[float] = None
    curtailment_pct: Optional[float] = None
    capacity_factor_pct: Optional[float] = None
    battery_cycles_per_year: Optional[float] = None


# ── Distribution ────────────────────────────────────────────────────

class BoQItem(BaseModel):
    category: str
    description: str
    unit: str
    quantity: float
    unit_cost_usd: float
    total_cost_usd: float


class DistributionDesign(BaseModel):
    total_line_length_m: float
    pole_count: int
    bill_of_quantities: list[BoQItem]
    total_network_cost_usd: float
    cost_per_connection_usd: float
    voltage_drop_max_pct: float
    technical_losses_pct: float
    method_used: str
    customers_connected: int
    construction_multiplier: float
    warnings: list[str] = Field(default_factory=list)


# ── Carbon Assessment ───────────────────────────────────────────────

class CarbonAssessment(BaseModel):
    annual_emission_reductions_tco2e: float
    diesel_displaced_litres_yr: float
    crediting_period_years: int = 7
    total_eligible_tco2e: float
    revenue_by_scenario: dict
    npv_carbon_revenue: dict
    recommended_methodology: str
    methodology_rationale: str
    alternative_methodology: str
    validation_cost_estimate_usd: float
    annual_verification_cost_usd: float
    warnings: list[str] = Field(default_factory=list)


# ── CAPEX / OPEX ────────────────────────────────────────────────────

class CapexBreakdown(BaseModel):
    pv: float
    battery: float
    inverter: float
    distribution: float
    meters: float
    installation: float
    soft_costs: float
    mounting: Optional[float] = None
    bos: Optional[float] = None
    civil_works: Optional[float] = None
    owners_cost: Optional[float] = None
    epc_margin: Optional[float] = None
    contingency: Optional[float] = None


class OpexBreakdown(BaseModel):
    generation_om: float
    distribution_om: float
    site_security: float
    remote_monitoring: float
    insurance: float


# ── Sensitivity / Cash Flow ─────────────────────────────────────────

class SensitivityResult(BaseModel):
    parameter: str
    low_value: float
    base_value: float
    high_value: float
    irr_at_low: float
    irr_at_base: float
    irr_at_high: float


class YearlyCashFlow(BaseModel):
    year: int
    revenue: float
    opex: float
    capex: float
    replacements: float
    net_cash_flow: float
    cumulative: float
    carbon_revenue: Optional[float] = None
    debt_service: Optional[float] = None
    energy_generated_kwh: Optional[float] = None
    energy_sold_kwh: Optional[float] = None


# ── Financial Results ───────────────────────────────────────────────

class FinancialResults(BaseModel):
    total_capex_usd: float
    capex_breakdown: CapexBreakdown
    lcoe_usd_kwh: float
    irr_pct: float
    npv_usd: float
    payback_years: float
    dscr: float
    cost_reflective_tariff_usd: float
    affordable_tariff_usd: float
    subsidy_gap_per_connection_usd: float
    subsidy_gap_total_usd: float
    subsidy_gap_pct_capex: float
    sensitivity: list[SensitivityResult]
    cash_flow: list[YearlyCashFlow]
    equity_irr_pct: Optional[float] = None
    capex_per_wp: Optional[float] = None
    annual_opex_usd: Optional[float] = None
    opex_breakdown: Optional[OpexBreakdown] = None
    annual_revenue_usd: Optional[float] = None
    grant_amount_usd: Optional[float] = None
    debt_amount_usd: Optional[float] = None
    equity_amount_usd: Optional[float] = None


# ── Grid Risk ───────────────────────────────────────────────────────

class GridArrivalScenario(BaseModel):
    arrival_year: int
    adjusted_irr: float
    adjusted_npv: float
    investment_recovered_pct: float


class EsmapScenario(BaseModel):
    scenario: str
    label: str
    weighted_score: float
    timeline_certainty: float
    financial_viability: float
    regulatory_alignment: float
    implementation_complexity: float
    stakeholder_acceptability: float


class GridRiskAssessment(BaseModel):
    dist_mv_km: float
    dist_hv_km: float
    risk_level: str = Field(description="low, medium, high, or critical")
    risk_label: str
    scenarios: Optional[list[GridArrivalScenario]] = None
    esmap_recommended: Optional[str] = None
    esmap_scores: Optional[list[EsmapScenario]] = None
    design_implications: Optional[str] = None


# ── Request / Response ──────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-27, le=-10)
    longitude: float = Field(..., ge=29, le=42)
    name: Optional[str] = None
    overrides: Optional[dict] = None


class AnalysisResult(BaseModel):
    site: SiteCoordinates
    cluster: ClusterInfo
    screening: SuitabilityScreening
    demand: DemandEstimate
    sizing: SystemSizing
    financial: FinancialResults
    grid_risk: GridRiskAssessment
    solar_resource: Optional[SolarResource] = None
    distribution: Optional[DistributionDesign] = None
    carbon: Optional[CarbonAssessment] = None
