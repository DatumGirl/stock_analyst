"""Data ingestion — fetch real market data via yfinance and upsert to Supabase."""
from __future__ import annotations

import asyncio
import datetime
import math
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from ..config import settings

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


async def _supabase_upsert(
    table: str,
    rows: list[dict[str, Any]],
    on_conflict: str,
) -> dict[str, Any]:
    if not rows:
        return {"inserted": 0}
    url = f"{settings.supabase_url}/rest/v1/{table}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    total = 0
    chunk_size = 500
    async with httpx.AsyncClient() as client:
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            res = await client.post(
                f"{url}?on_conflict={on_conflict}",
                headers=headers,
                json=chunk,
                timeout=30.0,
            )
            if res.status_code not in (200, 201):
                raise HTTPException(
                    status_code=500,
                    detail=f"Supabase upsert to {table} failed: {res.text[:300]}",
                )
            total += len(chunk)
    return {"inserted": total}


def _fetch_yfinance(ticker: str) -> dict[str, Any]:
    """Synchronous yfinance fetch — called via run_in_executor."""
    import pandas as pd
    import yfinance as yf

    t = yf.Ticker(ticker)
    today = datetime.date.today().isoformat()
    result: dict[str, Any] = {
        "ticker": ticker,
        "prices": [],
        "ticker_info": None,
        "fundamentals": [],
        "catalysts": [],
        "news": [],
    }

    # ── Prices ───────────────────────────────────────────────────────────────
    try:
        hist = t.history(period="2y", auto_adjust=False)
        adj_col = "Adj Close" if "Adj Close" in hist.columns else "Close"
        for ts, row in hist.iterrows():
            close = _safe_float(row.get("Close"))
            adj = _safe_float(row.get(adj_col)) or close
            if close is None or adj is None:
                continue
            vol = row.get("Volume")
            result["prices"].append({
                "ticker": ticker,
                "date": ts.strftime("%Y-%m-%d"),
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": close,
                "adj_close": adj,
                "volume": int(vol) if vol is not None and not pd.isna(vol) else None,
                "source": "yfinance",
            })
    except Exception:
        pass

    # ── Ticker reference ─────────────────────────────────────────────────────
    try:
        info = t.info or {}
        result["ticker_info"] = {
            "symbol": ticker,
            "name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange") or "NASDAQ",
        }
    except Exception:
        result["ticker_info"] = {
            "symbol": ticker,
            "name": ticker,
            "sector": None,
            "industry": None,
            "exchange": "NASDAQ",
        }

    # ── Quarterly fundamentals ───────────────────────────────────────────────
    try:
        qf = t.quarterly_financials   # index = line items, columns = quarter-end dates
        qcf = t.quarterly_cashflow

        def _get(df: Any, *keys: str, col: Any) -> float | None:
            for k in keys:
                try:
                    return _safe_float(df.loc[k, col])
                except KeyError:
                    continue
            return None

        prior_revenue: float | None = None
        for col in reversed(list(qf.columns)):  # oldest first for growth calc
            revenue = _get(qf, "Total Revenue", "Revenue", col=col)
            gross = _get(qf, "Gross Profit", col=col)
            op_inc = _get(qf, "Operating Income", "EBIT", col=col)
            net_inc = _get(qf, "Net Income", col=col)
            eps = _get(qf, "Basic EPS", "Diluted EPS", col=col)
            op_cf = _get(qcf, "Operating Cash Flow", "Total Cash From Operating Activities", col=col)
            capex = _get(qcf, "Capital Expenditure", "Capital Expenditures", col=col)

            # capex is typically negative in yfinance; FCF = op_cf + capex
            fcf: float | None = None
            if op_cf is not None and capex is not None:
                fcf = op_cf + capex
            elif op_cf is not None:
                fcf = op_cf

            rev_growth: float | None = None
            if revenue is not None and prior_revenue is not None and prior_revenue != 0:
                rev_growth = (revenue - prior_revenue) / abs(prior_revenue)
            if revenue is not None:
                prior_revenue = revenue

            fiscal_period = f"{col.year}-Q{(col.month - 1) // 3 + 1}"

            result["fundamentals"].append({
                "ticker": ticker,
                "fiscal_period": fiscal_period,
                "revenue": revenue,
                "revenue_growth": rev_growth,
                "gross_margin": (gross / revenue) if gross is not None and revenue else None,
                "operating_margin": (op_inc / revenue) if op_inc is not None and revenue else None,
                "net_margin": (net_inc / revenue) if net_inc is not None and revenue else None,
                "eps": eps,
                "eps_expected": None,
                "fcf": fcf,
                "guidance_revenue": None,
                "guidance_eps": None,
                "source": "yfinance",
                "as_of": today,
            })
    except Exception:
        pass

    # ── Earnings calendar ────────────────────────────────────────────────────
    try:
        cal = t.earnings_dates
        if cal is not None and not cal.empty:
            cutoff = datetime.date.today()
            for ts, _ in cal.iterrows():
                d = ts.date() if hasattr(ts, "date") else ts
                if d >= cutoff:
                    result["catalysts"].append({
                        "ticker": ticker,
                        "type": "earnings",
                        "description": f"{ticker} Earnings",
                        "date": d.isoformat(),
                        "expected_impact": "neutral",
                    })
    except Exception:
        pass

    # ── Recent news ──────────────────────────────────────────────────────────
    try:
        news_items = t.news or []
        for item in news_items[:10]:
            pub = item.get("providerPublishTime") or item.get("published") or 0
            if isinstance(pub, int) and pub > 0:
                pub_ts = datetime.datetime.fromtimestamp(pub, tz=datetime.timezone.utc).isoformat()
            elif isinstance(pub, str):
                pub_ts = pub
            else:
                pub_ts = today
            headline = (item.get("title") or "")[:500]
            if not headline:
                continue
            result["news"].append({
                "tickers": [ticker],
                "headline": headline,
                "source": item.get("publisher") or item.get("source") or "yfinance",
                "url": item.get("link") or item.get("url") or None,
                "as_of": pub_ts,
                "sentiment": "neutral",
                "materiality_score": 0.5,
                "affects_earnings": False,
                "affects_valuation": False,
                "affects_thesis": False,
            })
    except Exception:
        pass

    return result


@router.post("/{ticker}", summary="Fetch and store real market data for a ticker")
async def ingest_ticker(ticker: str) -> dict[str, Any]:
    ticker = ticker.upper()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_yfinance, ticker)

    out: dict[str, Any] = {"ticker": ticker}

    if data["prices"]:
        out["prices"] = await _supabase_upsert("prices_daily", data["prices"], "ticker,date")

    if data["ticker_info"]:
        out["ticker_info"] = await _supabase_upsert("tickers", [data["ticker_info"]], "symbol")

    if data["fundamentals"]:
        out["fundamentals"] = await _supabase_upsert(
            "fundamentals", data["fundamentals"], "ticker,fiscal_period,source"
        )

    # news_events: insert only headlines not already stored for this ticker
    if data["news"]:
        headers_base = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }
        async with httpx.AsyncClient() as client:
            ex = await client.get(
                f"{settings.supabase_url}/rest/v1/news_events"
                f"?tickers=cs.{{\"{ticker}\"}}&select=headline&limit=100",
                headers=headers_base,
                timeout=10.0,
            )
        existing_headlines = {r["headline"] for r in (ex.json() if ex.status_code == 200 else [])}
        fresh = [n for n in data["news"] if n["headline"] not in existing_headlines]
        if fresh:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.supabase_url}/rest/v1/news_events",
                    headers={**headers_base, "Content-Type": "application/json", "Prefer": "return=minimal"},
                    json=fresh,
                    timeout=30.0,
                )
            out["news"] = {"inserted": len(fresh) if res.status_code in (200, 201) else 0}
        else:
            out["news"] = {"inserted": 0}

    # catalysts has no unique constraint — check existing dates to avoid dupes
    if data["catalysts"]:
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{settings.supabase_url}/rest/v1/catalysts"
                f"?ticker=eq.{ticker}&type=eq.earnings&select=date",
                headers=headers,
                timeout=10.0,
            )
        existing = {r["date"] for r in (res.json() if res.status_code == 200 else [])}
        new = [c for c in data["catalysts"] if c["date"] not in existing]
        if new:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.supabase_url}/rest/v1/catalysts",
                    headers={**headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
                    json=new,
                    timeout=30.0,
                )
            out["catalysts"] = {"inserted": len(new)}
        else:
            out["catalysts"] = {"inserted": 0}

    return out
