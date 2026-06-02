from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OpportunityBase(BaseModel):
    project_name: str
    province: str
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cluster_id: Optional[int] = None
    status: str = "scoped"
    program_name: str = "Enabel"
    connections_targeted: Optional[int] = None
    pue_value_chains: Optional[list[str]] = None
    pv_capacity_kwp: Optional[float] = None
    battery_capacity_kwh: Optional[float] = None
    distribution_line_length_m: Optional[float] = None
    total_capex_usd: Optional[float] = None
    cost_per_connection_usd: Optional[float] = None
    grant_per_connection_usd: Optional[float] = None
    lcoe_usd_kwh: Optional[float] = None
    irr_pct: Optional[float] = None
    payback_years: Optional[float] = None
    analysis_id: Optional[UUID] = None
    metadata: Optional[dict] = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    project_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[str] = None
    program_name: Optional[str] = None
    connections_targeted: Optional[int] = None
    pue_value_chains: Optional[list[str]] = None
    pv_capacity_kwp: Optional[float] = None
    battery_capacity_kwh: Optional[float] = None
    distribution_line_length_m: Optional[float] = None
    total_capex_usd: Optional[float] = None
    cost_per_connection_usd: Optional[float] = None
    grant_per_connection_usd: Optional[float] = None
    lcoe_usd_kwh: Optional[float] = None
    irr_pct: Optional[float] = None
    payback_years: Optional[float] = None


class Opportunity(OpportunityBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "draft"


class PortfolioCreate(PortfolioBase):
    opportunity_ids: list[UUID] = Field(default_factory=list)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class Portfolio(PortfolioBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    opportunities: list[Opportunity] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PortfolioSummary(PortfolioBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    opportunity_count: int = 0
    submission_count: int = 0

    model_config = {"from_attributes": True}


class SubmissionBase(BaseModel):
    portfolio_id: UUID
    bidder_name: str
    bidder_organization: Optional[str] = None
    contact_email: Optional[str] = None
    status: str = "pending"
    proposed_capex_usd: Optional[float] = None
    proposed_grant_ask_usd: Optional[float] = None
    proposed_tariff_usd_kwh: Optional[float] = None
    proposed_lcoe_usd_kwh: Optional[float] = None
    proposed_irr_pct: Optional[float] = None
    proposed_timeline_months: Optional[int] = None
    technical_approach: Optional[str] = None
    experience_summary: Optional[str] = None
    scoring_technical: Optional[float] = None
    scoring_financial: Optional[float] = None
    scoring_experience: Optional[float] = None
    scoring_total: Optional[float] = None
    documents: Optional[list[dict]] = None
    notes: Optional[str] = None


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionUpdate(BaseModel):
    status: Optional[str] = None
    proposed_capex_usd: Optional[float] = None
    proposed_grant_ask_usd: Optional[float] = None
    proposed_tariff_usd_kwh: Optional[float] = None
    proposed_lcoe_usd_kwh: Optional[float] = None
    proposed_irr_pct: Optional[float] = None
    proposed_timeline_months: Optional[int] = None
    technical_approach: Optional[str] = None
    experience_summary: Optional[str] = None
    scoring_technical: Optional[float] = None
    scoring_financial: Optional[float] = None
    scoring_experience: Optional[float] = None
    scoring_total: Optional[float] = None
    notes: Optional[str] = None


class Submission(SubmissionBase):
    id: UUID
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
