"""Macro Agent — fetches market regime and macro environment data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel


class MacroItem(BaseModel):
    key: str
    label: str
    value: float | None
    change: float | None
    change_pct: float | None
    unit: str


class MacroData(BaseModel):
    regime: str | None  # bull / bear / volatile / sideways
    vix: float | None
    items: list[MacroItem]
    sector_performance: dict[str, float]
    as_of: str
    warnings: list[str]


class AgentResult(BaseModel):
    data: MacroData
    sources: list[str]
    as_of: str
    warnings: list[str]


# Keys we expect to find in prices_daily for macro instruments
_MACRO_TICKERS: list[dict[str, Any]] = [
    {"symbol": "^VIX",  "key": "VIX",      "label": "VIX",           "unit": "pts"},
    {"symbol": "^TNX",  "key": "10Y_YIELD", "label": "10Y Yield",     "unit": "%"},
    {"symbol": "DX-Y.NYB", "key": "DXY",   "label": "US Dollar",     "unit": "pts"},
    {"symbol": "CL=F",  "key": "CRUDE",     "label": "Crude Oil",     "unit": "$"},
    {"symbol": "GC=F",  "key": "GOLD",      "label": "Gold",          "unit": "$"},
    {"symbol": "^GSPC", "key": "SP500",     "label": "S&P 500",       "unit": "pts"},
]


class MacroAgent:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self._url = supabase_url
        self._key = supabase_key

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._key, "Authorization": f"Bearer {self._key}"}

    async def run(self, client: httpx.AsyncClient) -> AgentResult:
        warnings: list[str] = []
        now = datetime.now(timezone.utc).isoformat()
        items: list[MacroItem] = []
        vix_val: float | None = None

        for m in _MACRO_TICKERS:
            resp = await client.get(
                f"{self._url}/rest/v1/prices_daily",
                params={
                    "ticker": f"eq.{m['symbol']}",
                    "order": "date.desc",
                    "limit": "2",
                    "select": "close,date",
                },
                headers=self._headers(),
            )
            if resp.status_code == 200 and resp.json():
                rows = resp.json()
                current = float(rows[0]["close"])
                prev = float(rows[1]["close"]) if len(rows) > 1 else None
                change = (current - prev) if prev is not None else None
                change_pct = (change / prev) if prev else None
                item = MacroItem(
                    key=m["key"], label=m["label"],
                    value=current, change=change, change_pct=change_pct,
                    unit=m["unit"],
                )
                items.append(item)
                if m["key"] == "VIX":
                    vix_val = current
            else:
                warnings.append(f"No macro data for {m['symbol']}")
                items.append(MacroItem(
                    key=m["key"], label=m["label"],
                    value=None, change=None, change_pct=None,
                    unit=m["unit"],
                ))

        # Determine regime
        sp500_item = next((i for i in items if i.key == "SP500"), None)
        regime: str | None = None
        if vix_val is not None and sp500_item and sp500_item.value is not None:
            if vix_val > 30:
                regime = "volatile"
            elif sp500_item.change_pct and sp500_item.change_pct < -0.20:
                regime = "bear"
            elif vix_val < 20 and sp500_item.change_pct and sp500_item.change_pct > 0:
                regime = "bull"
            else:
                regime = "sideways"

        data = MacroData(
            regime=regime,
            vix=vix_val,
            items=items,
            sector_performance={},  # populated by intraday pipeline
            as_of=now,
            warnings=warnings,
        )
        return AgentResult(data=data, sources=["supabase/prices_daily/macro"], as_of=now, warnings=warnings)
