"""FastAPI application for the graph service (port 8003)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph_service.queries import GraphQueries
from graph_service.schema import MemgraphQueryRunner

MEMGRAPH_HOST = os.environ.get("MEMGRAPH_HOST", "localhost")
MEMGRAPH_PORT = int(os.environ.get("MEMGRAPH_PORT", "7687"))
_STALE_DAYS = 120

_runner: MemgraphQueryRunner | None = None
_gq: GraphQueries | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _runner, _gq
    _runner = MemgraphQueryRunner(MEMGRAPH_HOST, MEMGRAPH_PORT)
    _gq = GraphQueries(_runner)
    yield
    if _runner:
        await _runner.close()


app = FastAPI(title="Graph Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ok(data: Any, sources: list[str] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"data": data, "sources": sources or ["memgraph"], "as_of": _now(), "warnings": warnings or []}


def _gq_or_raise() -> GraphQueries:
    if _gq is None:
        raise RuntimeError("Graph queries not initialised")
    return _gq


def _staleness_warning(rows: list[dict[str, Any]]) -> list[str]:
    from datetime import date, timedelta
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=_STALE_DAYS)).isoformat()
    stale = [r for r in rows if r.get("as_of", "") < cutoff]
    if stale:
        return [f"{len(stale)} relationship(s) have not been refreshed in over {_STALE_DAYS} days."]
    return []


# ─── Models ───────────────────────────────────────────────────────────────────

class TickersBody(BaseModel):
    tickers: list[str]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, Any]:
    connected = False
    try:
        await _gq_or_raise()._runner.execute("RETURN 1 AS n", {})
        connected = True
    except Exception:
        pass
    return {"status": "ok", "memgraph_connected": connected}


@app.get("/relationships/{ticker}")
async def get_relationships(ticker: str) -> dict[str, Any]:
    rels = await _gq_or_raise().get_relationships(ticker.upper())
    warnings = _staleness_warning(rels)
    return _ok(rels, warnings=warnings)


@app.get("/supply-chain/{ticker}")
async def get_supply_chain(ticker: str, max_hops: int = 3) -> dict[str, Any]:
    if not (1 <= max_hops <= 5):
        raise HTTPException(400, "max_hops must be 1–5")
    rows = await _gq_or_raise().get_supply_chain(ticker.upper(), max_hops)
    return _ok(rows)


@app.post("/hidden-concentration")
async def hidden_concentration(body: TickersBody) -> dict[str, Any]:
    if len(body.tickers) < 2:
        raise HTTPException(400, "Provide at least 2 tickers")
    rows = await _gq_or_raise().get_hidden_concentration(body.tickers)
    return _ok(rows)


@app.post("/etf-overlap")
async def etf_overlap(body: TickersBody) -> dict[str, Any]:
    if len(body.tickers) < 2:
        raise HTTPException(400, "Provide at least 2 tickers")
    rows = await _gq_or_raise().get_etf_overlap(body.tickers)
    return _ok(rows)


@app.post("/theme-exposure")
async def theme_exposure(body: TickersBody) -> dict[str, Any]:
    rows = await _gq_or_raise().get_theme_exposure(body.tickers)
    return _ok(rows)
