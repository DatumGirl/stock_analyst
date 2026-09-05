"""Technical agent: trend, momentum, volume, and key levels.

Returns computed indicators from the quant service — never interprets them.
"""
from __future__ import annotations

import datetime
from typing import Any

import httpx

from .base import BaseAgent
from ..models import AgentResult


class TechnicalAgent(BaseAgent):
    def __init__(self, quant_service_url: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._quant_url = quant_service_url

    async def run(self, ticker: str, period: str = "3M") -> AgentResult:  # type: ignore[override]
        today = datetime.date.today().isoformat()
        warnings: list[str] = []
        data: dict[str, Any] = {"ticker": ticker}

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{self._quant_url}/metrics/{ticker}",
                    params={"period": period},
                    timeout=10.0,
                )
            if res.status_code == 200:
                metrics_payload = res.json()
                data["metrics"] = metrics_payload.get("data", {})
                data["as_of"] = metrics_payload.get("as_of", today)
            else:
                warnings.append(f"Quant service returned {res.status_code} for {ticker}")
        except httpx.RequestError as e:
            warnings.append(f"Quant service unavailable: {e}")

        prices = await self._supabase_get(
            "prices_daily",
            {"ticker": f"eq.{ticker}", "order": "date.desc", "limit": "65", "select": "date,close,volume,high,low"},
        )
        data["recent_prices"] = prices[:5] if prices else []

        return AgentResult(
            data=data,
            sources=[f"quant_service:{ticker}", f"supabase:prices_daily:{ticker}"],
            as_of=data.get("as_of", today),
            warnings=warnings,
        )
