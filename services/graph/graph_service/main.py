"""FastAPI entry point for the graph service.

Exposes relationship intelligence queries over HTTP so the orchestrator's
GraphAgent can call them without a direct Bolt connection.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent import (
    company_relationships,
    data_freshness,
    etf_overlap,
    event_propagation,
    hidden_concentration,
    peer_group,
    supply_chain,
    theme_exposure,
)
from .client import GraphConnectionError, MemgraphClient
from .config import load_config
from .market_ingest import DEFAULT_MAX_PER_ETF, ETF_UNIVERSE, run_live_ingest
from .results import GraphResult

_client: MemgraphClient | None = None
_config = load_config()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _client
    _client = MemgraphClient(_config.memgraph)
    yield
    _client = None


app = FastAPI(title="StockIntel Graph Service", lifespan=_lifespan)


def _runner() -> MemgraphClient:
    if _client is None:
        raise HTTPException(status_code=503, detail="Graph service not ready")
    return _client


def _to_response(result: GraphResult) -> dict[str, Any]:
    return {
        "query": result.query,
        "data": result.data,
        "sources": result.sources,
        "as_of": result.as_of.isoformat() if result.as_of else None,
        "warnings": result.warnings,
    }


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "graph"}


@app.get("/relationships/{ticker}")
def get_relationships(ticker: str) -> dict[str, Any]:
    try:
        result = company_relationships(_runner(), ticker.upper(), _config.traversal)
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


@app.get("/supply-chain/{ticker}")
def get_supply_chain(ticker: str) -> dict[str, Any]:
    try:
        result = supply_chain(_runner(), ticker.upper(), _config.traversal)
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


@app.get("/peers/{ticker}")
def get_peers(ticker: str) -> dict[str, Any]:
    try:
        result = peer_group(_runner(), ticker.upper())
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


class TickerListBody(BaseModel):
    tickers: list[str]


@app.post("/hidden-concentration")
def post_hidden_concentration(body: TickerListBody) -> dict[str, Any]:
    tickers = [t.upper() for t in body.tickers]
    try:
        result = hidden_concentration(_runner(), tickers, _config.traversal)
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


@app.post("/etf-overlap")
def post_etf_overlap(body: TickerListBody) -> dict[str, Any]:
    tickers = [t.upper() for t in body.tickers]
    try:
        result = etf_overlap(_runner(), tickers, _config.traversal)
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


@app.post("/theme-exposure")
def post_theme_exposure(body: TickerListBody) -> dict[str, Any]:
    tickers = [t.upper() for t in body.tickers]
    try:
        result = theme_exposure(_runner(), tickers, _config.traversal)
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


class EventBody(BaseModel):
    event_key: str
    tickers: list[str] | None = None


@app.post("/event-propagation")
def post_event_propagation(body: EventBody) -> dict[str, Any]:
    try:
        result = event_propagation(
            _runner(), body.event_key, _config.traversal,
            tickers=[t.upper() for t in body.tickers] if body.tickers else None,
        )
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


@app.get("/data-freshness")
def get_data_freshness() -> dict[str, Any]:
    try:
        result = data_freshness(_runner())
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_response(result)


class LiveIngestBody(BaseModel):
    tickers: list[str] = []
    etfs: list[str] = ETF_UNIVERSE
    max_holdings_per_etf: int = DEFAULT_MAX_PER_ETF


@app.post("/ingest/live")
async def post_ingest_live(body: LiveIngestBody) -> dict[str, Any]:
    """Fetch ETF holdings and sector/industry data from yfinance and write to Memgraph."""
    try:
        return await run_live_ingest(
            _runner(),
            [t.upper() for t in body.tickers],
            body.etfs,
            body.max_holdings_per_etf,
        )
    except GraphConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
