from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import sites, analysis, reports

app = FastAPI(
    title="Moz — Mini-Grid Prefeasibility API",
    version="0.1.0",
    description="Backend API for solar+battery mini-grid prefeasibility analysis in Mozambique",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sites.router, prefix="/api/sites", tags=["sites"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "moz-api"}
