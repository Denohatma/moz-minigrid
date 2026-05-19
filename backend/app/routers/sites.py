from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.site import ClusterInfo, SuitabilityScreening
from app.engines.gis_engine import lookup_cluster, screen_suitability

router = APIRouter()

COUNTRY_DIR = Path(__file__).resolve().parents[3] / "countries" / "mozambique"


@router.get("/lookup", response_model=ClusterInfo)
def get_cluster(
    lat: float = Query(..., ge=-27, le=-10, description="Latitude"),
    lon: float = Query(..., ge=29, le=42, description="Longitude"),
):
    try:
        cluster = lookup_cluster(lat, lon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if cluster is None:
        raise HTTPException(status_code=404, detail="No settlement cluster found near this location")
    return cluster


@router.get("/screen", response_model=SuitabilityScreening)
def get_suitability(
    lat: float = Query(..., ge=-27, le=-10),
    lon: float = Query(..., ge=29, le=42),
):
    try:
        cluster = lookup_cluster(lat, lon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if cluster is None:
        raise HTTPException(status_code=404, detail="No settlement cluster found")
    return screen_suitability(cluster)


@router.get("/priority")
def get_priority_sites(
    province: Optional[str] = Query(None, description="Filter by province name"),
    min_score: float = Query(0, description="Minimum priority score"),
    limit: int = Query(200, ge=1, le=500),
):
    path = COUNTRY_DIR / "priority_minigrid_sites.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Priority sites data not available")

    data = json.loads(path.read_text())
    sites = data.get("sites", [])

    if province:
        province_lower = province.lower()
        sites = [s for s in sites if province_lower in s.get("province", "").lower()]

    if min_score > 0:
        sites = [s for s in sites if s.get("score", 0) >= min_score]

    return {
        "total": len(sites),
        "sites": sites[:limit],
        "provinces": sorted(set(s["province"] for s in data.get("sites", []))),
    }
