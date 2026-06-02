-- Opportunities: project pipeline entries (one per minigrid site)
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(300) NOT NULL,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    cluster_id INTEGER REFERENCES settlement_clusters(cluster_id),
    status VARCHAR(50) NOT NULL DEFAULT 'scoped'
        CHECK (status IN ('scoped', 'floated', 'submitted')),
    program_name VARCHAR(200) NOT NULL DEFAULT 'Enabel',
    connections_targeted INTEGER,
    pue_value_chains TEXT[],
    pv_capacity_kwp DOUBLE PRECISION,
    battery_capacity_kwh DOUBLE PRECISION,
    distribution_line_length_m DOUBLE PRECISION,
    total_capex_usd DOUBLE PRECISION,
    cost_per_connection_usd DOUBLE PRECISION,
    grant_per_connection_usd DOUBLE PRECISION,
    lcoe_usd_kwh DOUBLE PRECISION,
    irr_pct DOUBLE PRECISION,
    payback_years DOUBLE PRECISION,
    analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_opportunities_status ON opportunities (status);
CREATE INDEX idx_opportunities_province ON opportunities (province);
CREATE INDEX idx_opportunities_program ON opportunities (program_name);

-- Portfolios: bundles of opportunities sent out for bidding / investment
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(300) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'under_review', 'awarded', 'closed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction table linking opportunities to portfolios (many-to-many)
CREATE TABLE portfolio_opportunities (
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (portfolio_id, opportunity_id)
);

-- Bidder submissions against a portfolio
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    bidder_name VARCHAR(300) NOT NULL,
    bidder_organization VARCHAR(300),
    contact_email VARCHAR(300),
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'under_review', 'shortlisted', 'accepted', 'rejected')),
    proposed_capex_usd DOUBLE PRECISION,
    proposed_grant_ask_usd DOUBLE PRECISION,
    proposed_tariff_usd_kwh DOUBLE PRECISION,
    proposed_lcoe_usd_kwh DOUBLE PRECISION,
    proposed_irr_pct DOUBLE PRECISION,
    proposed_timeline_months INTEGER,
    technical_approach TEXT,
    experience_summary TEXT,
    scoring_technical DOUBLE PRECISION,
    scoring_financial DOUBLE PRECISION,
    scoring_experience DOUBLE PRECISION,
    scoring_total DOUBLE PRECISION,
    documents JSONB DEFAULT '[]',
    notes TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_submissions_portfolio ON submissions (portfolio_id);
CREATE INDEX idx_submissions_status ON submissions (status);
CREATE INDEX idx_submissions_bidder ON submissions (bidder_name);
