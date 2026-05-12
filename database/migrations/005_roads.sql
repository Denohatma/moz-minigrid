CREATE TABLE roads (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    road_type VARCHAR(30),  -- primary, secondary, tertiary, trunk, motorway
    name VARCHAR(200),
    surface VARCHAR(30),
    geom GEOMETRY(MultiLineString, 4326) NOT NULL,
    length_km DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_roads_geom ON roads USING GIST (geom);
CREATE INDEX idx_roads_type ON roads (road_type);
