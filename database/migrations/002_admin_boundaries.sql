CREATE TABLE admin_boundaries (
    id SERIAL PRIMARY KEY,
    adm0_name VARCHAR(100) NOT NULL DEFAULT 'Mozambique',
    adm1_name VARCHAR(100),        -- Province
    adm1_code VARCHAR(20),
    adm2_name VARCHAR(100),        -- District
    adm2_code VARCHAR(20),
    adm3_name VARCHAR(100),        -- Posto administrativo
    adm3_code VARCHAR(20),
    level SMALLINT NOT NULL,       -- 0=country, 1=province, 2=district, 3=posto
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    area_km2 DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_admin_geom ON admin_boundaries USING GIST (geom);
CREATE INDEX idx_admin_level ON admin_boundaries (level);
CREATE INDEX idx_admin_adm1 ON admin_boundaries (adm1_name);
