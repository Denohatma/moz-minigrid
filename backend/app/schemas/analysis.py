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


# ── Productive Use ─────────────────────────────────────────────────

class ProductiveUseSector(BaseModel):
    sector: str
    relevance: str = Field(description="high, medium, low, none")
    rationale: str
    indicative_activities: list[str] = Field(default_factory=list)
    estimated_demand_kwh_day: float = 0.0
    seasonal_pattern: str = "year-round"


class AnchorCustomer(BaseModel):
    type: str
    name: str
    estimated_demand_kwh_day: float
    estimated_peak_kw: float
    confidence: str = Field(description="high, medium, low")
    contract_type: str = "standard"


class ProductiveUseEquipment(BaseModel):
    sector: str
    equipment: str
    power_kw: float
    capex_usd_low: float
    capex_usd_high: float
    ownership_model: str


class ProductiveUseAssessment(BaseModel):
    sectors: list[ProductiveUseSector] = Field(default_factory=list)
    anchors: list[AnchorCustomer] = Field(default_factory=list)
    total_productive_demand_kwh_day: float = 0.0
    productive_demand_pct: float = 0.0
    demand_projections: dict = Field(default_factory=dict)
    equipment_recommendations: list[ProductiveUseEquipment] = Field(default_factory=list)
    complementary_investment_usd: dict = Field(default_factory=dict)
    jobs: dict = Field(default_factory=dict)
    incremental_income_usd_year: float = 0.0
    demand_stimulation: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# ── ESS Screening ─────────────────────────────────────────────────

class ProtectedAreaCheck(BaseModel):
    area_name: str
    distance_km: float
    buffer_zone: bool
    sensitivity: str = Field(description="high, moderate, low")


class ESSScreening(BaseModel):
    esia_category: str = Field(description="A, B+, B, C")
    esia_rationale: str
    esia_requirements: list[str] = Field(default_factory=list)

    biodiversity_sensitivity: str
    protected_area_checks: list[ProtectedAreaCheck] = Field(default_factory=list)
    biodiversity_notes: str = ""

    resettlement_risk: str
    physical_displacement_risk: str = ""
    economic_displacement_risk: str = ""
    resettlement_notes: str = ""
    estimated_land_requirement_ha: float = 0.0

    labour_safety_risks: list[str] = Field(default_factory=list)
    community_safety_risks: list[str] = Field(default_factory=list)

    stakeholder_groups: list[str] = Field(default_factory=list)
    consultation_requirements: list[str] = Field(default_factory=list)

    grievance_mechanism: dict = Field(default_factory=dict)

    gesi_considerations: list[str] = Field(default_factory=list)
    womens_empowerment_opportunities: list[str] = Field(default_factory=list)
    inclusion_measures: list[str] = Field(default_factory=list)

    overall_ess_risk: str = Field(description="high, substantial, moderate, low")
    recommended_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Risk Analysis ─────────────────────────────────────────────────

class RiskItem(BaseModel):
    category: str = Field(description="technical, commercial, regulatory, security, social, climate, currency, political")
    sub_risk: str
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    risk_score: int
    risk_level: str = Field(description="critical, high, medium, low")
    description: str
    mitigation: list[str] = Field(default_factory=list)
    allocation: str = "shared"


class RiskAnalysis(BaseModel):
    risks: list[RiskItem] = Field(default_factory=list)
    overall_risk_score: float = 0.0
    overall_risk_level: str = "medium"
    top_risks: list[str] = Field(default_factory=list)
    risk_allocation_summary: dict = Field(default_factory=dict)
    mitigation_investment_usd: float = 0.0
    warnings: list[str] = Field(default_factory=list)


# ── Confidence Scoring ────────────────────────────────────────────

class ConfidenceDimension(BaseModel):
    dimension: str
    confidence_score: int = Field(ge=0, le=100)
    margin_of_error_pct: float
    data_quality: str = Field(description="high, medium, low")
    key_assumptions: list[str] = Field(default_factory=list)
    calibration_status: str = "uncalibrated"


class ConfidenceAssessment(BaseModel):
    dimensions: list[ConfidenceDimension] = Field(default_factory=list)
    overall_confidence_score: int = 0
    overall_confidence_level: str = "medium"
    data_completeness_pct: float = 0.0
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Concession Data Sheet ─────────────────────────────────────────

class ConcessionSection(BaseModel):
    section_number: int
    title: str
    data: dict


class ConcessionDataSheet(BaseModel):
    site_name: str
    province: str
    district: str
    generation_date: str
    sections: list[ConcessionSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Climate Rationale ──────────────────────────────────────────────

class ClimateHazard(BaseModel):
    hazard: str = Field(description="cyclone, flood, drought, sea_level_rise, heat_stress")
    level: str = Field(description="very_high, high, moderate, low, negligible")
    description: str
    design_measures: list[str] = Field(default_factory=list)


class ClimateFinanceEligibility(BaseModel):
    instrument: str = Field(description="GCF, Adaptation Fund, Carbon Market, etc.")
    eligible: bool
    rationale: str
    estimated_value_usd: float = Field(default=0.0, description="0 if not estimable")


class ClimateRationale(BaseModel):
    # Mitigation
    lifetime_avoided_tco2e: float
    per_capita_reduction_tco2e: float
    ndc_alignment: str = Field(description="NDC alignment narrative")

    # Adaptation
    adaptation_narrative: str
    climate_resilient_livelihoods: list[str] = Field(default_factory=list)
    water_security_contribution: str
    food_security_contribution: str
    energy_access_adaptation: str

    # Hazards
    hazards: list[ClimateHazard] = Field(default_factory=list)
    overall_hazard_level: str
    design_resilience_measures: list[str] = Field(default_factory=list)

    # Finance
    climate_finance: list[ClimateFinanceEligibility] = Field(default_factory=list)
    climate_finance_score: str = Field(description="high, medium, low")
    total_climate_finance_potential_usd: float

    warnings: list[str] = Field(default_factory=list)


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
    climate: Optional[ClimateRationale] = None
    productive_use: Optional[ProductiveUseAssessment] = None
    ess: Optional[ESSScreening] = None
    risk_analysis: Optional[RiskAnalysis] = None
    confidence: Optional[ConfidenceAssessment] = None
    concession: Optional[ConcessionDataSheet] = None
