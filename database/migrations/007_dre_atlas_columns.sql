-- Add World Bank DRE Atlas fields to settlement_clusters

ALTER TABLE settlement_clusters
    ADD COLUMN IF NOT EXISTS geohash VARCHAR(20),
    ADD COLUMN IF NOT EXISTS village_name VARCHAR(200),

    -- Building data
    ADD COLUMN IF NOT EXISTS num_buildings INTEGER,
    ADD COLUMN IF NOT EXISTS building_density_pct DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS large_buildings INTEGER,
    ADD COLUMN IF NOT EXISTS medium_buildings INTEGER,
    ADD COLUMN IF NOT EXISTS small_buildings INTEGER,
    ADD COLUMN IF NOT EXISTS very_small_structures INTEGER,

    -- Nightlight (DRE Atlas uses binary + overlap instead of NTL radiance)
    ADD COLUMN IF NOT EXISTS has_nightlight BOOLEAN,
    ADD COLUMN IF NOT EXISTS nightlight_overlap_pct DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS dist_nightlight_km DOUBLE PRECISION,

    -- DRE Atlas demand estimates
    ADD COLUMN IF NOT EXISTS dre_num_connections INTEGER,
    ADD COLUMN IF NOT EXISTS dre_demand_kwh_day DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS dre_demand_per_conn_kwh_day DOUBLE PRECISION,

    -- PV production potential (kWh/kWp/yr from Solargis)
    ADD COLUMN IF NOT EXISTS pv_kwh_kwp_year DOUBLE PRECISION,

    -- Planned grid
    ADD COLUMN IF NOT EXISTS dist_grid_planned_km DOUBLE PRECISION,

    -- Water
    ADD COLUMN IF NOT EXISTS closest_distance_water_km DOUBLE PRECISION,

    -- Road access
    ADD COLUMN IF NOT EXISTS main_road_access BOOLEAN,
    ADD COLUMN IF NOT EXISTS nearest_hub_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS dist_nearest_hub_km DOUBLE PRECISION,

    -- Social infrastructure
    ADD COLUMN IF NOT EXISTS num_education_facilities INTEGER,
    ADD COLUMN IF NOT EXISTS has_education_facility BOOLEAN,
    ADD COLUMN IF NOT EXISTS num_health_facilities INTEGER,
    ADD COLUMN IF NOT EXISTS has_health_facility BOOLEAN,

    -- Socioeconomic
    ADD COLUMN IF NOT EXISTS mean_rwi DOUBLE PRECISION,

    -- Agriculture (MapSPAM, district-level)
    ADD COLUMN IF NOT EXISTS crop_types TEXT,
    ADD COLUMN IF NOT EXISTS ag_area_ha DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ag_value_usd DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ag_yield_kg_ha DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ag_value_per_ha DOUBLE PRECISION,

    -- Security (ACLED)
    ADD COLUMN IF NOT EXISTS security_risk VARCHAR(20),
    ADD COLUMN IF NOT EXISTS fatalities_25km VARCHAR(50),
    ADD COLUMN IF NOT EXISTS fatalities_50km VARCHAR(50),
    ADD COLUMN IF NOT EXISTS total_incidents_50km INTEGER;

CREATE INDEX IF NOT EXISTS idx_clusters_geohash ON settlement_clusters (geohash);
CREATE INDEX IF NOT EXISTS idx_clusters_security ON settlement_clusters (security_risk);
CREATE INDEX IF NOT EXISTS idx_clusters_nightlight ON settlement_clusters (has_nightlight);
