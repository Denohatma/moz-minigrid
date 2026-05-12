from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas.analysis import AnalysisRequest
from app.services.analysis_service import run_full_analysis
from app.engines.excel_engine import generate_excel
from app.engines.report_engine import generate_html_report
from app.engines.pfs_engine import generate_pfs_docx

router = APIRouter()


@router.post("/pdf")
def generate_pdf_report(request: AnalysisRequest):
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    html = generate_html_report(result)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="moz-report-{result.cluster.id}.html"'},
    )


@router.post("/pfs")
def generate_pfs_report(request: AnalysisRequest):
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    docx_bytes = generate_pfs_docx(result)
    site_name = result.cluster.village_name or "site"
    pv = result.sizing.pv_kwp
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{site_name}-{pv:.0f}kWp-PFS.docx"'},
    )


@router.post("/excel")
def generate_excel_report(request: AnalysisRequest):
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    xlsx_bytes = generate_excel(result)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="moz-model-{result.cluster.id}.xlsx"'},
    )
