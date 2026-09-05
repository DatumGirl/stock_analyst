"""FastAPI application for the orchestrator service (port 8002)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator.chief_analyst import ChiefAnalyst

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
# Reuse the same Supabase project that the mobile app uses
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
QUANT_URL = os.environ.get("QUANT_URL", "http://localhost:8001")
GRAPH_URL = os.environ.get("GRAPH_URL", "http://localhost:8003")

_analyst: ChiefAnalyst | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _analyst
    _analyst = ChiefAnalyst(
        anthropic_api_key=ANTHROPIC_API_KEY,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY,
        quant_url=QUANT_URL,
        graph_url=GRAPH_URL,
    )
    yield


app = FastAPI(title="Orchestrator", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_analyst() -> ChiefAnalyst:
    if _analyst is None:
        raise RuntimeError("Chief analyst not initialised")
    return _analyst


def _ok(data: Any, sources: list[str] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "data": data,
        "sources": sources or [],
        "as_of": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings or [],
    }


# ─── Request models ───────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    ticker: str
    portfolio_id: str | None = None


class CompareRequest(BaseModel):
    tickers: list[str]


class ContributionRequest(BaseModel):
    ticker: str
    portfolio_id: str


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0", "anthropic_model": "claude-opus-4-8"}


@app.post("/analyze")
async def analyze_ticker(body: AnalyzeRequest) -> dict[str, Any]:
    ticker = body.ticker.upper().strip()
    if not ticker or not ticker.isalnum() or len(ticker) > 5:
        raise HTTPException(400, f"Invalid ticker: {body.ticker!r}")

    result = await _get_analyst().analyze_ticker(ticker, body.portfolio_id)
    warnings: list[str] = result.pop("warnings", [])
    return _ok(result, warnings=warnings)


@app.post("/compare")
async def compare_tickers(body: CompareRequest) -> dict[str, Any]:
    if len(body.tickers) < 2 or len(body.tickers) > 4:
        raise HTTPException(400, "Provide 2–4 tickers to compare")

    tickers = [t.upper().strip() for t in body.tickers]
    analyst = _get_analyst()

    import asyncio
    analyses = await asyncio.gather(
        *[analyst.analyze_ticker(t) for t in tickers],
        return_exceptions=True,
    )

    rows: list[dict[str, Any]] = []
    for ticker, analysis in zip(tickers, analyses):
        if isinstance(analysis, Exception):
            rows.append({"ticker": ticker, "error": str(analysis)})
            continue
        tech = analysis.get("technical_snapshot") or {}
        val = analysis.get("valuation_range") or {}
        fund = analysis.get("earnings") or {}
        rows.append({
            "ticker": ticker,
            "revenue_growth": fund.get("revenue_growth"),
            "pe": None,  # computed from EPS + price
            "fwd_pe": None,
            "gross_margin": fund.get("gross_margin"),
            "roic": None,
            "debt_to_equity": None,
            "momentum_score": _rsi_to_score(tech.get("rsi_14")),
            "fair_value_gap_pct": _fair_value_gap(
                tech.get("current_price"), val.get("base")
            ),
        })

    summaries = [
        a.get("verdict", "") for a in analyses if isinstance(a, dict)
    ]

    return _ok({
        "tickers": tickers,
        "chief_analyst_summary": _compare_summary(tickers, rows),
        "rows": rows,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "is_forecast": True,
    })


@app.get("/brief/{portfolio_id}")
async def daily_brief(portfolio_id: str, date: str | None = None) -> dict[str, Any]:
    """Assemble the daily brief from snapshot + changes + catalysts."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }

        # Latest snapshot
        snap_resp = await http.get(
            f"{SUPABASE_URL}/rest/v1/portfolio_snapshots",
            params={"portfolio_id": f"eq.{portfolio_id}", "order": "date.desc", "limit": "2"},
            headers=headers,
        )
        snapshots = snap_resp.json() if snap_resp.status_code == 200 else []

        # Material changes
        change_date = date or datetime.now(timezone.utc).date().isoformat()
        changes_resp = await http.get(
            f"{SUPABASE_URL}/rest/v1/portfolio_changes",
            params={"portfolio_id": f"eq.{portfolio_id}", "date": f"eq.{change_date}", "order": "created_at.desc"},
            headers=headers,
        )
        changes = changes_resp.json() if changes_resp.status_code == 200 else []

        today_snap = snapshots[0] if snapshots else {}
        yesterday_snap = snapshots[1] if len(snapshots) > 1 else {}

        prob = today_snap.get("target_probability", 0)
        yesterday_prob = yesterday_snap.get("target_probability", 0)

        brief = {
            "date": change_date,
            "portfolio_return": today_snap.get("day_return", 0),
            "health_score": today_snap.get("health_score", 0),
            "risk_level": today_snap.get("risk_level", "moderate"),
            "target_probability": prob,
            "target_probability_delta": prob - yesterday_prob if yesterday_snap else 0,
            "important": changes[:3],
            "catalysts": [],
            "macro": None,
            "opportunities": [],
            "action_plan": [],
            "rebalance_required": False,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    return _ok(brief)


@app.post("/portfolio-contribution")
async def portfolio_contribution(body: ContributionRequest) -> dict[str, Any]:
    from orchestrator.agents.portfolio import PortfolioAgent
    async with httpx.AsyncClient(timeout=30.0) as http:
        agent = PortfolioAgent(SUPABASE_URL, SUPABASE_KEY, QUANT_URL)
        result = await agent.run(body.ticker.upper(), body.portfolio_id, http)
        data = result.data
        return _ok({
            "ticker": data.ticker,
            "sector_delta": data.sector_delta_if_added,
            "theme_delta": {},
            "correlation_with_portfolio": data.correlation_with_portfolio,
            "recommendation": data.recommendation,
            "reason": data.reason,
            "is_forecast": True,
        }, warnings=result.warnings)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _rsi_to_score(rsi: float | None) -> float | None:
    if rsi is None:
        return None
    # Normalize RSI 0-100 to momentum score 0-100 with 50 as neutral
    return round(rsi, 1)


def _fair_value_gap(current: float | None, base: float | None) -> float | None:
    if current is None or base is None or current == 0:
        return None
    return round((base - current) / current * 100, 1)


def _compare_summary(tickers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"Comparing {', '.join(tickers)}."
    best_growth = max(rows, key=lambda r: r.get("revenue_growth") or -999)
    return (
        f"Comparing {', '.join(tickers)}: "
        f"{best_growth['ticker']} leads on revenue growth. "
        f"See table for full metrics — check fair value gap for entry opportunities."
    )
