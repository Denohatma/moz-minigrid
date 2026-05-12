from fastapi import APIRouter, HTTPException

from app.schemas.analysis import AnalysisRequest, AnalysisResult
from app.services.analysis_service import run_full_analysis

router = APIRouter()


@router.post("/analyze-site", response_model=AnalysisResult)
def analyze_site(request: AnalysisRequest):
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
