from fastapi import APIRouter, HTTPException, Query

from app.schemas.site import ClusterInfo, SuitabilityScreening
from app.engines.gis_engine import lookup_cluster, screen_suitability

router = APIRouter()


@router.get("/lookup", response_model=ClusterInfo)
def get_cluster(
    lat: float = Query(..., ge=-27, le=-10, description="Latitude"),
    lon: float = Query(..., ge=29, le=42, description="Longitude"),
):
    cluster = lookup_cluster(lat, lon)
    if cluster is None:
        raise HTTPException(status_code=404, detail="No settlement cluster found near this location")
    return cluster


@router.get("/screen", response_model=SuitabilityScreening)
def get_suitability(
    lat: float = Query(..., ge=-27, le=-10),
    lon: float = Query(..., ge=29, le=42),
):
    cluster = lookup_cluster(lat, lon)
    if cluster is None:
        raise HTTPException(status_code=404, detail="No settlement cluster found")
    return screen_suitability(cluster)
