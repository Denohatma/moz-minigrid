from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class SiteCoordinates(BaseModel):
    latitude: float = Field(..., ge=-27, le=-10, description="Latitude (decimal degrees)")
    longitude: float = Field(..., ge=29, le=42, description="Longitude (decimal degrees)")
    name: Optional[str] = None


class ClusterInfo(BaseModel):
    id: str = Field(description="Settlement geohash identifier")
    village_name: Optional[str] = None
    admin_region: Optional[str] = None
    admin_district: Optional[str] = None
    population: int
    area_km2: float
    is_urban: int = Field(description="0=rural, 1=peri-urban, 2=urban")

    # Building data (DRE Atlas)
    num_buildings: Optional[int] = None
    building_density_pct: Optional[float] = None
    large_buildings: Optional[int] = None
    medium_buildings: Optional[int] = None
    small_buildings: Optional[int] = None

    # Electrification indicators
    max_ntl: float = 0.0
    electrified_pop: float = 0.0
    has_nightlight: Optional[bool] = None
    nightlight_overlap_pct: Optional[float] = None

    # Solar & wind resource
    ghi_kwh_m2_year: float
    pv_kwh_kwp_year: Optional[float] = Field(None, description="PV production potential (kWh/kWp/yr)")
    wind_speed_ms: Optional[float] = None
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None

    # Infrastructure proximity
    dist_grid_mv_km: float
    dist_grid_hv_km: Optional[float] = None
    dist_grid_planned_km: Optional[float] = None
    dist_road_km: float
    travel_time_hrs: Optional[float] = None

    # DRE Atlas demand estimates
    dre_demand_kwh_day: Optional[float] = Field(None, description="DRE Atlas total settlement demand (kWh/day)")
    dre_demand_per_conn_kwh_day: Optional[float] = Field(None, description="DRE Atlas demand per connection (kWh/day)")
    dre_num_connections: Optional[int] = Field(None, description="DRE Atlas estimated connections (buildings >= 15m²)")

    # Accessibility & infrastructure
    main_road_access: Optional[bool] = None
    nearest_hub_name: Optional[str] = None
    dist_nearest_hub_km: Optional[float] = None
    closest_distance_water_km: Optional[float] = None

    # Social infrastructure
    num_education_facilities: Optional[int] = None
    has_education_facility: Optional[bool] = None
    num_health_facilities: Optional[int] = None
    has_health_facility: Optional[bool] = None

    # Socioeconomic
    mean_rwi: Optional[float] = Field(None, description="Meta Relative Wealth Index")

    # Agriculture
    crop_types: Optional[str] = None
    ag_area_ha: Optional[float] = None
    ag_value_usd: Optional[float] = None

    # Security (ACLED)
    security_risk: Optional[str] = Field(None, description="low, medium, or high")
    fatalities_25km: Optional[str] = None
    fatalities_50km: Optional[str] = None
    total_incidents_50km: Optional[int] = None


class SuitabilityWarning(BaseModel):
    type: str
    message: str
    severity: str = Field(description="info, warning, or error")


class SuitabilityScreening(BaseModel):
    is_suitable: bool
    warnings: list[SuitabilityWarning]
