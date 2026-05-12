CREATE TABLE settlement_clusters (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER UNIQUE NOT NULL,

    -- Location & geometry
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    centroid GEOMETRY(Point, 4326),
    adm1_name VARCHAR(100),
    adm2_name VARCHAR(100),

    -- Population & classification
    population INTEGER NOT NULL,
    area_km2 DOUBLE PRECISION NOT NULL,
    is_urban SMALLINT NOT NULL DEFAULT 0,  -- 0=rural, 1=peri-urban, 2=urban

    -- Electrification indicators
    max_ntl DOUBLE PRECISION,              -- Max nighttime light radiance (nW/cm²/sr)
    electrified_pop INTEGER DEFAULT 0,
    electrification_rate DOUBLE PRECISION,

    -- Solar resource
    ghi_kwh_m2_year DOUBLE PRECISION,      -- Global Horizontal Irradiance
    dni_kwh_m2_year DOUBLE PRECISION,      -- Direct Normal Irradiance

    -- Wind resource
    wind_speed_ms DOUBLE PRECISION,        -- Mean wind speed at 50m (m/s)

    -- Terrain
    elevation_m DOUBLE PRECISION,          -- Mean elevation (m)
    slope_deg DOUBLE PRECISION,            -- Mean slope (degrees)
    land_cover INTEGER,                    -- ESA WorldCover dominant class

    -- Infrastructure proximity
    dist_grid_mv_km DOUBLE PRECISION,      -- Distance to nearest MV line (km)
    dist_grid_hv_km DOUBLE PRECISION,      -- Distance to nearest HV line (km)
    dist_road_km DOUBLE PRECISION,         -- Distance to nearest road (km)
    dist_substation_km DOUBLE PRECISION,   -- Distance to nearest substation (km)

    -- Accessibility
    travel_time_hrs DOUBLE PRECISION,      -- Travel time to nearest city (hours)

    -- Metadata
    pop_source VARCHAR(50),                -- e.g. 'WorldPop2020', 'GHSL2023'
    data_year SMALLINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clusters_geom ON settlement_clusters USING GIST (geom);
CREATE INDEX idx_clusters_centroid ON settlement_clusters USING GIST (centroid);
CREATE INDEX idx_clusters_pop ON settlement_clusters (population);
CREATE INDEX idx_clusters_urban ON settlement_clusters (is_urban);
CREATE INDEX idx_clusters_adm1 ON settlement_clusters (adm1_name);
CREATE INDEX idx_clusters_grid ON settlement_clusters (dist_grid_mv_km);
