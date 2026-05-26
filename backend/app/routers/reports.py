from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas.analysis import AnalysisRequest
from app.services.analysis_service import run_full_analysis
from app.engines.excel_engine import generate_excel
from app.engines.report_engine import generate_html_report
from app.engines.pfs_engine import generate_pfs_docx, generate_pfs_docx_v2, generate_pfs_summary_docx
from app.engines.concession_engine import generate_concession_json

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
def generate_pfs_report_endpoint(request: AnalysisRequest):
    """Generate the comprehensive PUE-led Pre-Feasibility Study (v2 template)."""
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    docx_bytes = generate_pfs_docx_v2(result)
    site_name = result.cluster.village_name or "site"
    pv = result.sizing.pv_kwp
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{site_name}-{pv:.0f}kWp-PFS.docx"'},
    )


@router.post("/pfs-summary")
def generate_pfs_summary_endpoint(request: AnalysisRequest):
    """Generate a 5-page executive summary of the PFS."""
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    docx_bytes = generate_pfs_summary_docx(result)
    site_name = result.cluster.village_name or "site"
    pv = result.sizing.pv_kwp
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{site_name}-{pv:.0f}kWp-Summary.docx"'},
    )


@router.post("/pfs-legacy")
def generate_pfs_report_legacy(request: AnalysisRequest):
    """Generate the original PFS document (legacy format)."""
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
        headers={"Content-Disposition": f'attachment; filename="{site_name}-{pv:.0f}kWp-PFS-legacy.docx"'},
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


@router.post("/concession")
def generate_concession_report(request: AnalysisRequest):
    try:
        result = run_full_analysis(
            latitude=request.latitude,
            longitude=request.longitude,
            name=request.name,
            overrides=request.overrides,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result.concession is None:
        raise HTTPException(status_code=500, detail="Concession data sheet generation failed")

    import json
    content = json.dumps(generate_concession_json(result.concession), indent=2, ensure_ascii=False)
    site_name = result.cluster.village_name or "site"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{site_name}-ARENE-concession.json"'},
    )
