"""Portfolio agent: allocation, correlation, risk limits, target-return probability."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

import httpx

from .base import BaseAgent
from ..models import AgentResult


class PortfolioAgent(BaseAgent):
    def __init__(self, quant_service_url: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._quant_url = quant_service_url

    async def run(self, portfolio_id: str, candidate_ticker: str | None = None) -> AgentResult:  # type: ignore[override]
        today = datetime.date.today().isoformat()
        warnings: list[str] = []

        # Fetch positions
        positions = await self._supabase_get(
            "positions",
            {"portfolio_id": f"eq.{portfolio_id}", "select": "ticker,quantity,cost_basis"},
        )

        # Fetch latest snapshot
        snapshots = await self._supabase_get(
            "portfolio_snapshots",
            {
                "portfolio_id": f"eq.{portfolio_id}",
                "order": "date.desc",
                "limit": "1",
                "select": "*",
            },
        )
        snapshot = snapshots[0] if snapshots else None

        if not positions:
            warnings.append(f"Portfolio {portfolio_id} has no positions")
            return AgentResult(
                data={"portfolio_id": portfolio_id, "positions": [], "snapshot": None},
                sources=[],
                as_of=today,
                warnings=warnings,
            )

        tickers = [p["ticker"] for p in positions]

        # Fetch portfolio risk from quant service
        total_cost = sum(Decimal(str(p["cost_basis"])) * Decimal(str(p["quantity"])) for p in positions)
        weights = []
        for p in positions:
            pos_value = Decimal(str(p["cost_basis"])) * Decimal(str(p["quantity"]))
            weights.append(float(pos_value / total_cost) if total_cost > 0 else 0.0)

        risk_data: dict[str, Any] = {}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self._quant_url}/portfolio/risk",
                    json={"tickers": tickers, "weights": weights},
                    timeout=15.0,
                )
            if res.status_code == 200:
                risk_data = res.json().get("data", {})
        except httpx.RequestError as e:
            warnings.append(f"Could not compute portfolio risk: {e}")

        # Candidate fit analysis
        candidate_fit: str | None = None
        if candidate_ticker:
            ticker_weight_in_portfolio = next(
                (w for t, w in zip(tickers, weights) if t == candidate_ticker), 0.0
            )
            existing_exposure = round(ticker_weight_in_portfolio * 100, 1)
            candidate_fit = (
                f"{candidate_ticker} currently represents {existing_exposure}% of the portfolio."
                if existing_exposure > 0
                else f"{candidate_ticker} is not currently in the portfolio."
            )

        return AgentResult(
            data={
                "portfolio_id": portfolio_id,
                "positions": positions,
                "tickers": tickers,
                "weights": weights,
                "risk_metrics": risk_data,
                "snapshot": snapshot,
                "candidate_fit": candidate_fit,
            },
            sources=[f"supabase:positions:{portfolio_id}", f"quant_service:portfolio:{portfolio_id}"],
            as_of=snapshot.get("date", today) if snapshot else today,
            warnings=warnings,
        )
