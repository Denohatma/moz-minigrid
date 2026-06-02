from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from app.schemas.opportunity import (
    Portfolio,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioSummary,
    Submission,
    SubmissionCreate,
    SubmissionUpdate,
)

router = APIRouter()

DATABASE_URL = os.environ.get("DATABASE_URL")


def _get_engine():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    return create_engine(DATABASE_URL)


# ── Portfolios ──────────────────────────────────────────────────

@router.get("/", response_model=list[PortfolioSummary])
def list_portfolios(status: Optional[str] = Query(None)):
    engine = _get_engine()
    where = "WHERE p.status = :status" if status else ""
    params = {"status": status} if status else {}
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT p.*,
                   COUNT(DISTINCT po.opportunity_id) AS opportunity_count,
                   COUNT(DISTINCT s.id) AS submission_count
            FROM portfolios p
            LEFT JOIN portfolio_opportunities po ON po.portfolio_id = p.id
            LEFT JOIN submissions s ON s.portfolio_id = p.id
            {where}
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """), params).mappings().all()
    return [dict(r) for r in rows]


@router.post("/", response_model=Portfolio, status_code=201)
def create_portfolio(body: PortfolioCreate):
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            INSERT INTO portfolios (name, description, status)
            VALUES (:name, :description, :status)
            RETURNING *
        """), {
            "name": body.name,
            "description": body.description,
            "status": body.status,
        }).mappings().fetchone()

        portfolio_id = row["id"]

        for opp_id in body.opportunity_ids:
            conn.execute(text("""
                INSERT INTO portfolio_opportunities (portfolio_id, opportunity_id)
                VALUES (:pid, :oid)
                ON CONFLICT DO NOTHING
            """), {"pid": str(portfolio_id), "oid": str(opp_id)})

        opps = conn.execute(text("""
            SELECT o.* FROM opportunities o
            JOIN portfolio_opportunities po ON po.opportunity_id = o.id
            WHERE po.portfolio_id = :pid
        """), {"pid": str(portfolio_id)}).mappings().all()

        conn.commit()

    result = dict(row)
    result["opportunities"] = [dict(o) for o in opps]
    return result


@router.get("/{portfolio_id}", response_model=Portfolio)
def get_portfolio(portfolio_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM portfolios WHERE id = :id"),
            {"id": str(portfolio_id)},
        ).mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        opps = conn.execute(text("""
            SELECT o.* FROM opportunities o
            JOIN portfolio_opportunities po ON po.opportunity_id = o.id
            WHERE po.portfolio_id = :pid
            ORDER BY o.project_name
        """), {"pid": str(portfolio_id)}).mappings().all()

    result = dict(row)
    result["opportunities"] = [dict(o) for o in opps]
    return result


@router.patch("/{portfolio_id}", response_model=Portfolio)
def update_portfolio(portfolio_id: UUID, body: PortfolioUpdate):
    engine = _get_engine()
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["id"] = str(portfolio_id)
    with engine.connect() as conn:
        row = conn.execute(
            text(f"UPDATE portfolios SET {sets}, updated_at = NOW() WHERE id = :id RETURNING *"),
            data,
        ).mappings().fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    with engine.connect() as conn:
        opps = conn.execute(text("""
            SELECT o.* FROM opportunities o
            JOIN portfolio_opportunities po ON po.opportunity_id = o.id
            WHERE po.portfolio_id = :pid
        """), {"pid": str(portfolio_id)}).mappings().all()

    result = dict(row)
    result["opportunities"] = [dict(o) for o in opps]
    return result


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM portfolios WHERE id = :id"),
            {"id": str(portfolio_id)},
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Portfolio not found")


class AddOpportunitiesBody(BaseModel):
    opportunity_ids: list[UUID]


@router.post("/{portfolio_id}/opportunities", response_model=Portfolio)
def add_opportunities_to_portfolio(portfolio_id: UUID, body: AddOpportunitiesBody):
    engine = _get_engine()
    with engine.connect() as conn:
        port = conn.execute(
            text("SELECT id FROM portfolios WHERE id = :id"),
            {"id": str(portfolio_id)},
        ).fetchone()
        if not port:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        for opp_id in body.opportunity_ids:
            conn.execute(text("""
                INSERT INTO portfolio_opportunities (portfolio_id, opportunity_id)
                VALUES (:pid, :oid)
                ON CONFLICT DO NOTHING
            """), {"pid": str(portfolio_id), "oid": str(opp_id)})
        conn.commit()

    return get_portfolio(portfolio_id)


@router.delete("/{portfolio_id}/opportunities/{opportunity_id}", status_code=204)
def remove_opportunity_from_portfolio(portfolio_id: UUID, opportunity_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            DELETE FROM portfolio_opportunities
            WHERE portfolio_id = :pid AND opportunity_id = :oid
        """), {"pid": str(portfolio_id), "oid": str(opportunity_id)})
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Opportunity not in portfolio")


# ── Submissions ─────────────────────────────────────────────────

@router.get("/{portfolio_id}/submissions", response_model=list[Submission])
def list_submissions(portfolio_id: UUID, status: Optional[str] = Query(None)):
    engine = _get_engine()
    clauses = ["portfolio_id = :pid"]
    params: dict = {"pid": str(portfolio_id)}
    if status:
        clauses.append("status = :status")
        params["status"] = status
    where = " AND ".join(clauses)
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM submissions WHERE {where} ORDER BY submitted_at DESC"),
            params,
        ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/{portfolio_id}/submissions", response_model=Submission, status_code=201)
def create_submission(portfolio_id: UUID, body: SubmissionCreate):
    engine = _get_engine()
    with engine.connect() as conn:
        port = conn.execute(
            text("SELECT id FROM portfolios WHERE id = :id"),
            {"id": str(portfolio_id)},
        ).fetchone()
        if not port:
            raise HTTPException(status_code=404, detail="Portfolio not found")

    data = body.model_dump(exclude_none=True)
    data["portfolio_id"] = str(portfolio_id)
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())

    with engine.connect() as conn:
        row = conn.execute(
            text(f"INSERT INTO submissions ({cols}) VALUES ({placeholders}) RETURNING *"),
            data,
        ).mappings().fetchone()
        conn.commit()
    return dict(row)


@router.get("/{portfolio_id}/submissions/{submission_id}", response_model=Submission)
def get_submission(portfolio_id: UUID, submission_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM submissions WHERE id = :id AND portfolio_id = :pid"),
            {"id": str(submission_id), "pid": str(portfolio_id)},
        ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return dict(row)


@router.patch("/{portfolio_id}/submissions/{submission_id}", response_model=Submission)
def update_submission(portfolio_id: UUID, submission_id: UUID, body: SubmissionUpdate):
    engine = _get_engine()
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "status" in data and data["status"] in ("under_review", "shortlisted", "accepted", "rejected"):
        data["reviewed_at"] = "NOW()"

    sets_parts = []
    for k in data.keys():
        if data[k] == "NOW()":
            sets_parts.append(f"{k} = NOW()")
        else:
            sets_parts.append(f"{k} = :{k}")
    sets = ", ".join(sets_parts)

    clean_params = {k: v for k, v in data.items() if v != "NOW()"}
    clean_params["id"] = str(submission_id)
    clean_params["pid"] = str(portfolio_id)

    with engine.connect() as conn:
        row = conn.execute(
            text(f"UPDATE submissions SET {sets}, updated_at = NOW() WHERE id = :id AND portfolio_id = :pid RETURNING *"),
            clean_params,
        ).mappings().fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return dict(row)


@router.delete("/{portfolio_id}/submissions/{submission_id}", status_code=204)
def delete_submission(portfolio_id: UUID, submission_id: UUID):
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM submissions WHERE id = :id AND portfolio_id = :pid"),
            {"id": str(submission_id), "pid": str(portfolio_id)},
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
