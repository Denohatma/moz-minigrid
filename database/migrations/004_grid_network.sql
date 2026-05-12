CREATE TABLE grid_lines (
    id SERIAL PRIMARY KEY,
    line_type VARCHAR(10) NOT NULL,  -- 'HV' or 'MV'
    voltage_kv DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'existing',  -- existing, planned, under_construction
    source VARCHAR(100),
    geom GEOMETRY(MultiLineString, 4326) NOT NULL,
    length_km DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_grid_geom ON grid_lines USING GIST (geom);
CREATE INDEX idx_grid_type ON grid_lines (line_type);
CREATE INDEX idx_grid_status ON grid_lines (status);

CREATE TABLE substations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    substation_type VARCHAR(20),  -- 'transmission', 'distribution'
    voltage_kv DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'existing',
    source VARCHAR(100),
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_substation_geom ON substations USING GIST (geom);
