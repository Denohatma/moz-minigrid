const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://amiable-spontaneity-production.up.railway.app";

export interface SiteCoordinates {
  latitude: number;
  longitude: number;
  name?: string;
}

export interface ClusterInfo {
  id: string;
  village_name?: string;
  admin_region?: string;
  admin_district?: string;
  population: number;
  area_km2: number;
  is_urban: number;

  num_buildings?: number;
  building_density_pct?: number;
  large_buildings?: number;
  medium_buildings?: number;
  small_buildings?: number;

  max_ntl: number;
  electrified_pop: number;
  has_nightlight?: boolean;
  nightlight_overlap_pct?: number;

  ghi_kwh_m2_year: number;
  pv_kwh_kwp_year?: number;
  wind_speed_ms?: number;
  elevation_m?: number;
  slope_deg?: number;

  dist_grid_mv_km: number;
  dist_grid_hv_km?: number;
  dist_grid_planned_km?: number;
  dist_road_km: number;
  travel_time_hrs?: number;

  dre_demand_kwh_day?: number;
  dre_demand_per_conn_kwh_day?: number;
  dre_num_connections?: number;

  main_road_access?: boolean;
  nearest_hub_name?: string;
  dist_nearest_hub_km?: number;
  closest_distance_water_km?: number;

  num_education_facilities?: number;
  has_education_facility?: boolean;
  num_health_facilities?: number;
  has_health_facility?: boolean;

  mean_rwi?: number;

  crop_types?: string;
  ag_area_ha?: number;
  ag_value_usd?: number;

  security_risk?: string;
  fatalities_25km?: string;
  fatalities_50km?: string;
  total_incidents_50km?: number;
}

export interface DemandEstimate {
  households: number;
  total_settlement_households: number;
  coverage_pct: number;
  demand_tier: number;
  daily_energy_kwh: number;
  peak_demand_kw: number;
  annual_energy_kwh: number;
  productive_use_kwh_day: number;
  load_profile_kw: number[];
  persons_per_hh: number;
}

export interface SolarResource {
  monthly_ghi_kwh_m2: number[];
  monthly_dni_kwh_m2: number[];
  monthly_temp_c: number[];
  annual_ghi_kwh_m2: number;
  optimal_tilt_deg: number;
  specific_yield_kwh_per_kwp: number;
  performance_ratio: number;
  loss_breakdown: Record<string, number>;
  data_source: string;
}

export interface SystemSizing {
  pv_kwp: number;
  battery_kwh_nominal: number;
  battery_kwh_usable: number;
  inverter_kva: number;
  lv_line_km: number;
  service_transformers: number;
  meters: number;
  dc_ac_ratio?: number;
  annual_generation_kwh?: number;
  annual_energy_served_kwh?: number;
  unmet_energy_pct?: number;
  curtailment_pct?: number;
  capacity_factor_pct?: number;
  battery_cycles_per_year?: number;
}

export interface BoQItem {
  category: string;
  description: string;
  unit: string;
  quantity: number;
  unit_cost_usd: number;
  total_cost_usd: number;
}

export interface DistributionDesign {
  total_line_length_m: number;
  pole_count: number;
  bill_of_quantities: BoQItem[];
  total_network_cost_usd: number;
  cost_per_connection_usd: number;
  voltage_drop_max_pct: number;
  technical_losses_pct: number;
  method_used: string;
  customers_connected: number;
  construction_multiplier: number;
  warnings: string[];
}

export interface CarbonAssessment {
  annual_emission_reductions_tco2e: number;
  diesel_displaced_litres_yr: number;
  crediting_period_years: number;
  total_eligible_tco2e: number;
  revenue_by_scenario: Record<string, number>;
  npv_carbon_revenue: Record<string, number>;
  recommended_methodology: string;
  methodology_rationale: string;
  alternative_methodology: string;
  validation_cost_estimate_usd: number;
  annual_verification_cost_usd: number;
  warnings: string[];
}

export interface OpexBreakdown {
  generation_om: number;
  distribution_om: number;
  site_security: number;
  remote_monitoring: number;
  insurance: number;
}

export interface FinancialResults {
  total_capex_usd: number;
  capex_breakdown: {
    pv: number;
    battery: number;
    inverter: number;
    distribution: number;
    meters: number;
    installation: number;
    soft_costs: number;
    mounting?: number;
    bos?: number;
    civil_works?: number;
    owners_cost?: number;
    epc_margin?: number;
    contingency?: number;
  };
  lcoe_usd_kwh: number;
  irr_pct: number;
  npv_usd: number;
  payback_years: number;
  dscr: number;
  cost_reflective_tariff_usd: number;
  affordable_tariff_usd: number;
  subsidy_gap_per_connection_usd: number;
  subsidy_gap_total_usd: number;
  subsidy_gap_pct_capex: number;
  sensitivity: SensitivityResult[];
  cash_flow: YearlyCashFlow[];
  equity_irr_pct?: number;
  capex_per_wp?: number;
  annual_opex_usd?: number;
  opex_breakdown?: OpexBreakdown;
  annual_revenue_usd?: number;
  grant_amount_usd?: number;
  debt_amount_usd?: number;
  equity_amount_usd?: number;
}

export interface SensitivityResult {
  parameter: string;
  low_value: number;
  base_value: number;
  high_value: number;
  irr_at_low: number;
  irr_at_base: number;
  irr_at_high: number;
}

export interface YearlyCashFlow {
  year: number;
  revenue: number;
  opex: number;
  capex: number;
  replacements: number;
  net_cash_flow: number;
  cumulative: number;
  carbon_revenue?: number;
  debt_service?: number;
  energy_generated_kwh?: number;
  energy_sold_kwh?: number;
}

export interface EsmapScenario {
  scenario: string;
  label: string;
  weighted_score: number;
  timeline_certainty: number;
  financial_viability: number;
  regulatory_alignment: number;
  implementation_complexity: number;
  stakeholder_acceptability: number;
}

export interface GridRiskAssessment {
  dist_mv_km: number;
  dist_hv_km: number;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_label: string;
  scenarios?: GridArrivalScenario[];
  esmap_recommended?: string;
  esmap_scores?: EsmapScenario[];
  design_implications?: string;
}

export interface GridArrivalScenario {
  arrival_year: number;
  adjusted_irr: number;
  adjusted_npv: number;
  investment_recovered_pct: number;
}

export interface SuitabilityScreening {
  is_suitable: boolean;
  warnings: { type: string; message: string; severity: "info" | "warning" | "error" }[];
}

// ── Productive Use ──────────────────────────────────────────────

export interface ProductiveUseSector {
  sector: string;
  relevance: "high" | "medium" | "low" | "none";
  rationale: string;
  indicative_activities: string[];
  estimated_demand_kwh_day: number;
  seasonal_pattern: string;
}

export interface AnchorCustomer {
  type: string;
  name: string;
  estimated_demand_kwh_day: number;
  estimated_peak_kw: number;
  confidence: "high" | "medium" | "low";
  contract_type: string;
}

export interface ProductiveUseEquipment {
  sector: string;
  equipment: string;
  power_kw: number;
  capex_usd_low: number;
  capex_usd_high: number;
  ownership_model: string;
}

export interface ProductiveUseAssessment {
  sectors: ProductiveUseSector[];
  anchors: AnchorCustomer[];
  total_productive_demand_kwh_day: number;
  productive_demand_pct: number;
  demand_projections: Record<string, number>;
  equipment_recommendations: ProductiveUseEquipment[];
  complementary_investment_usd: Record<string, number>;
  jobs: Record<string, number>;
  incremental_income_usd_year: number;
  demand_stimulation: Record<string, unknown>;
  warnings: string[];
}

// ── ESS Screening ───────────────────────────────────────────────

export interface ProtectedAreaCheck {
  area_name: string;
  distance_km: number;
  buffer_zone: boolean;
  sensitivity: string;
}

export interface ESSScreening {
  esia_category: string;
  esia_rationale: string;
  esia_requirements: string[];
  biodiversity_sensitivity: string;
  protected_area_checks: ProtectedAreaCheck[];
  biodiversity_notes: string;
  resettlement_risk: string;
  physical_displacement_risk: string;
  economic_displacement_risk: string;
  resettlement_notes: string;
  estimated_land_requirement_ha: number;
  labour_safety_risks: string[];
  community_safety_risks: string[];
  stakeholder_groups: string[];
  consultation_requirements: string[];
  grievance_mechanism: Record<string, unknown>;
  gesi_considerations: string[];
  womens_empowerment_opportunities: string[];
  inclusion_measures: string[];
  overall_ess_risk: string;
  recommended_actions: string[];
  warnings: string[];
}

// ── Climate Rationale ───────────────────────────────────────────

export interface ClimateHazard {
  hazard: string;
  level: string;
  description: string;
  design_measures: string[];
}

export interface ClimateFinanceEligibility {
  instrument: string;
  eligible: boolean;
  rationale: string;
  estimated_value_usd: number;
}

export interface ClimateRationale {
  lifetime_avoided_tco2e: number;
  per_capita_reduction_tco2e: number;
  ndc_alignment: string;
  adaptation_narrative: string;
  climate_resilient_livelihoods: string[];
  water_security_contribution: string;
  food_security_contribution: string;
  energy_access_adaptation: string;
  hazards: ClimateHazard[];
  overall_hazard_level: string;
  design_resilience_measures: string[];
  climate_finance: ClimateFinanceEligibility[];
  climate_finance_score: string;
  total_climate_finance_potential_usd: number;
  warnings: string[];
}

// ── Risk Analysis ───────────────────────────────────────────────

export interface RiskItem {
  category: string;
  sub_risk: string;
  likelihood: number;
  impact: number;
  risk_score: number;
  risk_level: string;
  description: string;
  mitigation: string[];
  allocation: string;
}

export interface RiskAnalysis {
  risks: RiskItem[];
  overall_risk_score: number;
  overall_risk_level: string;
  top_risks: string[];
  risk_allocation_summary: Record<string, string[]>;
  mitigation_investment_usd: number;
  warnings: string[];
}

// ── Confidence Scoring ──────────────────────────────────────────

export interface ConfidenceDimension {
  dimension: string;
  confidence_score: number;
  margin_of_error_pct: number;
  data_quality: string;
  key_assumptions: string[];
  calibration_status: string;
}

export interface ConfidenceAssessment {
  dimensions: ConfidenceDimension[];
  overall_confidence_score: number;
  overall_confidence_level: string;
  data_completeness_pct: number;
  recommendations: string[];
  warnings: string[];
}

// ── Concession Data Sheet ───────────────────────────────────────

export interface ConcessionSection {
  section_number: number;
  title: string;
  data: Record<string, unknown>;
}

export interface ConcessionDataSheet {
  site_name: string;
  province: string;
  district: string;
  generation_date: string;
  sections: ConcessionSection[];
  warnings: string[];
}

// ── Analysis Result ─────────────────────────────────────────────

export interface AnalysisResult {
  site: SiteCoordinates;
  cluster: ClusterInfo;
  screening: SuitabilityScreening;
  demand: DemandEstimate;
  sizing: SystemSizing;
  financial: FinancialResults;
  grid_risk: GridRiskAssessment;
  solar_resource?: SolarResource;
  distribution?: DistributionDesign;
  carbon?: CarbonAssessment;
  climate?: ClimateRationale;
  productive_use?: ProductiveUseAssessment;
  ess?: ESSScreening;
  risk_analysis?: RiskAnalysis;
  confidence?: ConfidenceAssessment;
  concession?: ConcessionDataSheet;
}

// ── Priority Sites ──────────────────────────────────────────────

export interface PrioritySite {
  id: string;
  name: string;
  province: string;
  district: string;
  latitude: number;
  longitude: number;
  population: number;
  num_buildings: number;
  num_connections: number;
  demand_kwh_day: number;
  dist_grid_km: number;
  dist_road_km: number;
  has_education: boolean;
  has_health: boolean;
  pv_potential: number;
  security_risk: string;
  ag_area_ha: number;
  mean_rwi: number;
  score: number;
  is_priority_province: boolean;
}

export interface PrioritySitesResponse {
  total: number;
  sites: PrioritySite[];
  provinces: string[];
}

export async function fetchPrioritySites(
  province?: string,
  minScore?: number
): Promise<PrioritySitesResponse> {
  const params = new URLSearchParams();
  if (province) params.set("province", province);
  if (minScore) params.set("min_score", String(minScore));
  const res = await fetch(`${API_BASE}/api/sites/priority?${params}`);
  if (!res.ok) throw new Error("Failed to load priority sites");
  return res.json();
}

export async function analyzeSite(
  coords: SiteCoordinates,
  overrides?: Record<string, unknown>
): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/analyze-site`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...coords, overrides }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

export async function lookupCluster(
  latitude: number,
  longitude: number
): Promise<ClusterInfo> {
  const res = await fetch(
    `${API_BASE}/api/sites/lookup?lat=${latitude}&lon=${longitude}`
  );
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Cluster lookup failed");
  }
  return res.json();
}

export async function downloadReport(
  coords: SiteCoordinates,
  format: "pdf" | "excel" | "pfs" | "pfs-summary" | "concession",
  overrides?: Record<string, unknown>
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/reports/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...coords, overrides }),
  });
  if (!res.ok) throw new Error("Report generation failed");
  return res.blob();
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function streamChat(
  message: string,
  history: ChatMessage[],
  analysisResult?: AnalysisResult | null,
  cluster?: ClusterInfo | null,
  onChunk: (text: string) => void = () => {},
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history: history.slice(-20),
      analysis_result: analysisResult ?? undefined,
      cluster: cluster ?? undefined,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Chat failed" }));
    throw new Error(err.detail || "Chat failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response stream");

  const decoder = new TextDecoder();
  let fullText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ") && line !== "data: [DONE]") {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.text) {
            fullText += data.text;
            onChunk(fullText);
          }
        } catch { /* skip malformed */ }
      }
    }
  }
  return fullText;
}
