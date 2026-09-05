"""Portfolio Agent — evaluates a candidate ticker's fit within a user's portfolio."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel


class PortfolioFitData(BaseModel):
    ticker: str
    portfolio_id: str
    current_weights: dict[str, float]
    sector_exposure: dict[str, float]
    sector_delta_if_added: dict[str, float]
    correlation_with_portfolio: float | None
    tech_concentration_current: float | None
    tech_concentration_delta: float | None
    recommendation: str  # add / reduce / avoid / neutral
    reason: str
    as_of: str
    warnings: list[str]


class AgentResult(BaseModel):
    data: PortfolioFitData
    sources: list[str]
    as_of: str
    warnings: list[str]


_TECH_SECTORS = {"Technology", "Communication Services", "Semiconductors"}


class PortfolioAgent:
    def __init__(self, supabase_url: str, supabase_key: str, quant_url: str) -> None:
        self._url = supabase_url
        self._key = supabase_key
        self._quant = quant_url

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._key, "Authorization": f"Bearer {self._key}"}

    async def run(
        self, ticker: str, portfolio_id: str, client: httpx.AsyncClient
    ) -> AgentResult:
        warnings: list[str] = []
        now = datetime.now(timezone.utc).isoformat()

        # Fetch positions
        pos_resp = await client.get(
            f"{self._url}/rest/v1/positions",
            params={"portfolio_id": f"eq.{portfolio_id}", "select": "ticker,quantity,cost_basis"},
            headers=self._headers(),
        )
        positions: list[dict[str, Any]] = []
        if pos_resp.status_code == 200:
            positions = pos_resp.json()

        if not positions:
            warnings.append("No positions found — portfolio fit analysis limited")
            data = PortfolioFitData(
                ticker=ticker, portfolio_id=portfolio_id,
                current_weights={}, sector_exposure={}, sector_delta_if_added={},
                correlation_with_portfolio=None,
                tech_concentration_current=None, tech_concentration_delta=None,
                recommendation="neutral",
                reason="Portfolio is empty — no concentration risk to evaluate.",
                as_of=now, warnings=warnings,
            )
            return AgentResult(data=data, sources=[], as_of=now, warnings=warnings)

        # Compute weights from cost_basis * quantity
        total = sum(float(p["cost_basis"]) * float(p["quantity"]) for p in positions)
        weights = {
            p["ticker"]: float(p["cost_basis"]) * float(p["quantity"]) / total
            for p in positions
        } if total > 0 else {}

        # Fetch ticker sector data
        tickers_in_portfolio = list(weights.keys())
        sector_resp = await client.get(
            f"{self._url}/rest/v1/tickers",
            params={"symbol": f"in.({','.join(tickers_in_portfolio + [ticker])})", "select": "symbol,sector"},
            headers=self._headers(),
        )
        sectors: dict[str, str] = {}
        if sector_resp.status_code == 200:
            for row in sector_resp.json():
                sectors[row["symbol"]] = row.get("sector") or "Unknown"

        # Sector exposure
        sector_exp: dict[str, float] = {}
        for t, w in weights.items():
            s = sectors.get(t, "Unknown")
            sector_exp[s] = sector_exp.get(s, 0.0) + w

        # Tech concentration
        tech_current = sum(w for t, w in weights.items() if sectors.get(t, "") in _TECH_SECTORS)

        # Simulate adding ticker at 5% weight (reduce others proportionally)
        candidate_sector = sectors.get(ticker, "Unknown")
        candidate_weight = 0.05
        scale = 1.0 - candidate_weight
        new_sector_exp: dict[str, float] = {s: w * scale for s, w in sector_exp.items()}
        new_sector_exp[candidate_sector] = new_sector_exp.get(candidate_sector, 0.0) + candidate_weight

        tech_new = sum(w for s, w in new_sector_exp.items() if s in _TECH_SECTORS)
        tech_delta = tech_new - tech_current

        sector_delta = {s: new_sector_exp.get(s, 0) - sector_exp.get(s, 0) for s in set(sector_exp) | set(new_sector_exp)}

        # Recommendation logic
        recommendation = "neutral"
        reason = f"Adding {ticker} at 5% would change sector exposure by {tech_delta:+.1%} in tech."

        if tech_new > 0.40:
            recommendation = "avoid"
            reason = f"Tech/comms concentration would reach {tech_new:.0%} — above 40% threshold."
        elif ticker in weights and weights[ticker] > 0.10:
            recommendation = "reduce"
            reason = f"Already hold {weights[ticker]:.0%} in {ticker} — adding more increases concentration."
        elif tech_delta < -0.02:
            recommendation = "add"
            reason = f"Adding {ticker} improves diversification, reducing tech concentration by {abs(tech_delta):.1%}."

        data = PortfolioFitData(
            ticker=ticker,
            portfolio_id=portfolio_id,
            current_weights=weights,
            sector_exposure=sector_exp,
            sector_delta_if_added=sector_delta,
            correlation_with_portfolio=None,  # requires quant service call with full returns
            tech_concentration_current=tech_current,
            tech_concentration_delta=tech_delta,
            recommendation=recommendation,
            reason=reason,
            as_of=now,
            warnings=warnings,
        )
        return AgentResult(data=data, sources=["supabase/positions", "supabase/tickers"], as_of=now, warnings=warnings)
