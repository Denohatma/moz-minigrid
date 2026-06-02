from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text

from app.schemas.opportunity import (
    Opportunity,
    OpportunityCreate,
    OpportunityUpdate,
)

router = APIRouter()

DATABASE_URL = os.environ.get("DATABASE_URL")


def _get_engine():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    return create_engine(DATABASE_URL)


@router.get("/", response_model=list[Opportunity])
def list_opportunities(
    status: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    program: Optional[str] = Query(None),
):
    engine = _get_engine()
    clauses = []
    params: dict = {}
    if status:
        clauses.append("status = :status")
        params["status"] = status
    if province:
        clauses.append("province = :province")
        params["province"] = province
    if program:
        clauses.append("program_name = :program")
        params["program"] = program

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM opportunities {where} ORDER BY created_at DESC"),
            params,
        ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/", response_model=Opportunity, status_code=201)
def create_opportunity(body: OpportunityCreate):
    engine = _get_engine()
    data = body.model_dump(exclude_none=True)
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())

    if "pue_value_chains" in data and data["pue_value_chains"] is not None:
        data["pue_value_chains"] = list(data["pue_value_chains"])

    with engine.connect() as conn:
        row = conn.execute(
            text(f"INSERT INTO opportunities ({cols}) VALUES ({placeholders}) RETURNING *"),
            data,
        ).mappings().fetchone()
        conn.commit()
    return dict(row)


@router.get("/{opportunity_id}", response_model=Opportunity)
def get_opportunity(opportunity_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM opportunities WHERE id = :id"),
            {"id": str(opportunity_id)},
        ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return dict(row)


@router.patch("/{opportunity_id}", response_model=Opportunity)
def update_opportunity(opportunity_id: UUID, body: OpportunityUpdate):
    engine = _get_engine()
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["id"] = str(opportunity_id)
    with engine.connect() as conn:
        row = conn.execute(
            text(f"UPDATE opportunities SET {sets}, updated_at = NOW() WHERE id = :id RETURNING *"),
            data,
        ).mappings().fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return dict(row)


@router.delete("/{opportunity_id}", status_code=204)
def delete_opportunity(opportunity_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM opportunities WHERE id = :id"),
            {"id": str(opportunity_id)},
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Opportunity not found")
