"""Quant service FastAPI application."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import ingest, market, metrics, portfolio, snapshot, valuation

app = FastAPI(
    title="StockIntel Quant Service",
    description="Deterministic quantitative engine — returns, risk, valuation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(portfolio.router)
app.include_router(valuation.router)
app.include_router(ingest.router)
app.include_router(snapshot.router)
app.include_router(market.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "quant"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("quant_service.main:app", host=settings.host, port=settings.port, reload=True)
