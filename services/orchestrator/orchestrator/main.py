"""Orchestrator service FastAPI application."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import analyze, brief, compare

app = FastAPI(
    title="StockIntel Orchestrator",
    description="Chief Analyst orchestrator — synthesizes evidence from specialized agents via Claude",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(compare.router)
app.include_router(brief.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestrator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator.main:app", host=settings.host, port=settings.port, reload=True)
