from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import sites, analysis, reports, chat

app = FastAPI(
    title="Moz — Mini-Grid Prefeasibility API",
    version="0.1.0",
    description="Backend API for solar+battery mini-grid prefeasibility analysis in Mozambique",
)

import os

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sites.router, prefix="/api/sites", tags=["sites"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "moz-api"}
