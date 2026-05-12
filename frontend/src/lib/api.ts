const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

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
  demand_tier: number;
  daily_energy_kwh: number;
  peak_demand_kw: number;
  annual_energy_kwh: number;
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
  format: "pdf" | "excel" | "pfs",
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
