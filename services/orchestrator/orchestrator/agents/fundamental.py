"""Fundamental Agent — fetches and structures earnings/financial data from Supabase."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel


class FundamentalData(BaseModel):
    ticker: str
    latest_period: str | None
    revenue: float | None
    revenue_growth: float | None
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None
    eps_actual: float | None
    eps_expected: float | None
    eps_beat: bool | None
    eps_delta_pct: float | None
    fcf: float | None
    guidance_revenue: float | None
    guidance_eps: float | None
    guidance_direction: str | None  # raised / lowered / maintained / new
    balance_sheet_quality: str | None  # strong / adequate / stretched
    sources: list[str]
    as_of: str
    warnings: list[str]


class AgentResult(BaseModel):
    data: FundamentalData
    sources: list[str]
    as_of: str
    warnings: list[str]


class FundamentalAgent:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self._url = supabase_url
        self._key = supabase_key

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._key, "Authorization": f"Bearer {self._key}"}

    async def run(self, ticker: str, client: httpx.AsyncClient) -> AgentResult:
        warnings: list[str] = []
        now = datetime.now(timezone.utc).isoformat()

        # Fetch latest two fundamentals periods for direction comparison
        resp = await client.get(
            f"{self._url}/rest/v1/fundamentals",
            params={"ticker": f"eq.{ticker}", "order": "as_of.desc", "limit": "2"},
            headers=self._headers(),
        )

        rows: list[dict[str, Any]] = []
        if resp.status_code == 200:
            rows = resp.json()
        else:
            warnings.append(f"Fundamentals fetch failed: HTTP {resp.status_code}")

        # Fetch consensus estimates for beat/miss
        est_resp = await client.get(
            f"{self._url}/rest/v1/estimates",
            params={"ticker": f"eq.{ticker}", "order": "as_of.desc", "limit": "1"},
            headers=self._headers(),
        )
        estimate: dict[str, Any] = {}
        if est_resp.status_code == 200 and est_resp.json():
            estimate = est_resp.json()[0]

        if not rows:
            warnings.append(f"No fundamental data available for {ticker}")
            data = FundamentalData(
                ticker=ticker,
                latest_period=None,
                revenue=None, revenue_growth=None, gross_margin=None,
                operating_margin=None, net_margin=None,
                eps_actual=None, eps_expected=None,
                eps_beat=None, eps_delta_pct=None,
                fcf=None, guidance_revenue=None, guidance_eps=None,
                guidance_direction=None, balance_sheet_quality=None,
                sources=[], as_of=now, warnings=warnings,
            )
            return AgentResult(data=data, sources=[], as_of=now, warnings=warnings)

        latest = rows[0]
        prior = rows[1] if len(rows) > 1 else None

        eps_actual = _f(latest.get("eps"))
        eps_expected = _f(estimate.get("consensus_eps"))
        eps_beat: bool | None = None
        eps_delta_pct: float | None = None
        if eps_actual is not None and eps_expected is not None and eps_expected != 0:
            eps_beat = eps_actual > eps_expected
            eps_delta_pct = (eps_actual - eps_expected) / abs(eps_expected)

        # Guidance direction vs prior period
        guidance_direction: str | None = None
        g_rev = _f(latest.get("guidance_revenue"))
        if g_rev is not None and prior:
            prior_g = _f(prior.get("guidance_revenue"))
            if prior_g is None:
                guidance_direction = "new"
            elif g_rev > prior_g * 1.005:
                guidance_direction = "raised"
            elif g_rev < prior_g * 0.995:
                guidance_direction = "lowered"
            else:
                guidance_direction = "maintained"

        data = FundamentalData(
            ticker=ticker,
            latest_period=latest.get("fiscal_period"),
            revenue=_f(latest.get("revenue")),
            revenue_growth=_f(latest.get("revenue_growth")),
            gross_margin=_f(latest.get("gross_margin")),
            operating_margin=_f(latest.get("operating_margin")),
            net_margin=_f(latest.get("net_margin")),
            eps_actual=eps_actual,
            eps_expected=eps_expected,
            eps_beat=eps_beat,
            eps_delta_pct=eps_delta_pct,
            fcf=_f(latest.get("fcf")),
            guidance_revenue=g_rev,
            guidance_eps=_f(latest.get("guidance_eps")),
            guidance_direction=guidance_direction,
            balance_sheet_quality=None,  # computed from balance sheet data when available
            sources=[latest.get("source", "supabase")],
            as_of=latest.get("as_of", now),
            warnings=warnings,
        )
        return AgentResult(data=data, sources=data.sources, as_of=data.as_of, warnings=warnings)


def _f(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
