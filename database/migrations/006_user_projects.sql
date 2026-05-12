CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    cluster_id INTEGER REFERENCES settlement_clusters(cluster_id),

    -- Snapshot of inputs
    overrides JSONB DEFAULT '{}',

    -- Snapshot of results
    result JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analyses_project ON analyses (project_id);
CREATE INDEX idx_analyses_cluster ON analyses (cluster_id);
CREATE INDEX idx_analyses_created ON analyses (created_at DESC);
