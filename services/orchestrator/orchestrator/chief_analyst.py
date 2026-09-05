"""Chief Analyst — orchestrates agents via Claude tool use and synthesizes TickerAnalysis."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import httpx
from pydantic import BaseModel

from orchestrator.agents.fundamental import FundamentalAgent
from orchestrator.agents.graph import GraphAgent
from orchestrator.agents.macro import MacroAgent
from orchestrator.agents.news import NewsAgent
from orchestrator.agents.portfolio import PortfolioAgent
from orchestrator.agents.technical import TechnicalAgent

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "chief_analyst.md").read_text()

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "run_fundamental_agent",
        "description": "Fetch earnings, revenue, margins, guidance and balance-sheet data for a ticker.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "run_technical_agent",
        "description": "Fetch price data and compute RSI, MACD, SMA, ATR, VWAP and trend/momentum signals.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "run_news_agent",
        "description": "Fetch material news, upcoming catalysts and analyst revisions for a ticker.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "run_macro_agent",
        "description": "Fetch macro environment: VIX, yields, DXY, crude, S&P 500 and market regime.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "run_graph_agent",
        "description": "Fetch relationship intelligence: suppliers, customers, competitors, hidden concentration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "portfolio_tickers": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "run_portfolio_agent",
        "description": "Evaluate how a ticker fits the user's existing portfolio — sector delta, correlation, concentration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "portfolio_id": {"type": "string"},
            },
            "required": ["ticker", "portfolio_id"],
        },
    },
    {
        "name": "run_quant_valuation",
        "description": "Compute multi-method valuation ranges (P/E, DCF, peers) using the quant engine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "current_price": {"type": "number"},
                "eps": {"type": "number"},
                "fwd_eps": {"type": "number"},
                "revenue_per_share": {"type": "number"},
                "fcf_per_share": {"type": "number"},
                "growth_rate": {"type": "number"},
            },
            "required": ["ticker", "current_price"],
        },
    },
]


class ChiefAnalyst:
    def __init__(
        self,
        anthropic_api_key: str,
        supabase_url: str,
        supabase_key: str,
        quant_url: str,
        graph_url: str,
        model: str = "claude-opus-4-8",
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        self._model = model
        self._fundamental = FundamentalAgent(supabase_url, supabase_key)
        self._technical = TechnicalAgent(supabase_url, supabase_key)
        self._news = NewsAgent(supabase_url, supabase_key)
        self._macro = MacroAgent(supabase_url, supabase_key)
        self._graph = GraphAgent(graph_url)
        self._portfolio = PortfolioAgent(supabase_url, supabase_key, quant_url)
        self._quant_url = quant_url
        self._supabase_url = supabase_url
        self._supabase_key = supabase_key

    async def analyze_ticker(
        self, ticker: str, portfolio_id: str | None = None
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tool_results: dict[str, Any] = {}
        warnings: list[str] = []
        agents_invoked: list[str] = []

        async with httpx.AsyncClient(timeout=30.0) as http:
            messages: list[dict[str, Any]] = [
                {
                    "role": "user",
                    "content": (
                        f"Analyze {ticker} for the next trading day."
                        + (f" Portfolio ID: {portfolio_id}." if portfolio_id else "")
                        + " Call all relevant tools before writing your report."
                    ),
                }
            ]

            # Agentic loop
            for _ in range(12):  # max iterations
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=_SYSTEM_PROMPT,
                    tools=_TOOLS,  # type: ignore[arg-type]
                    messages=messages,  # type: ignore[arg-type]
                )

                # Collect assistant message
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    break

                # Execute tool calls
                tool_results_block: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    tool_name: str = block.name
                    tool_input: dict[str, Any] = block.input  # type: ignore[assignment]
                    agents_invoked.append(tool_name)

                    result = await self._dispatch_tool(tool_name, tool_input, http, portfolio_id)
                    tool_results[tool_name] = result
                    tool_results_block.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

                messages.append({"role": "user", "content": tool_results_block})

        # Extract final text
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        # Parse structured output from tool_results
        fundamental = tool_results.get("run_fundamental_agent", {})
        technical = tool_results.get("run_technical_agent", {})
        news = tool_results.get("run_news_agent", {})
        valuation_data = tool_results.get("run_quant_valuation", {})
        portfolio_fit = tool_results.get("run_portfolio_agent", {})

        fund_data = fundamental.get("data", {})
        tech_data = technical.get("data", {})

        # Signals
        signals = _infer_signals(fund_data, tech_data, valuation_data)

        # Model disagreements
        disagreements = _detect_disagreements(signals, tool_results)

        # Valuation range (first result from quant)
        valuation_range: dict[str, Any] | None = None
        val_list: list[Any] = valuation_data.get("data", []) if isinstance(valuation_data.get("data"), list) else []
        agg = next((v for v in val_list if v.get("method") == "aggregate"), None)
        if agg:
            valuation_range = {**agg, "is_forecast": True}

        news_data = news.get("data", {})
        portfolio_data = portfolio_fit.get("data", {})

        result: dict[str, Any] = {
            "ticker": ticker,
            "run_id": run_id,
            "verdict": _extract_verdict(final_text, ticker),
            "signals": signals,
            "valuation_range": valuation_range,
            "fair_value_current_price": str(tech_data.get("current_price")) if tech_data.get("current_price") else None,
            "earnings": _map_earnings(fund_data),
            "what_is_driving": news_data.get("material_news", []),
            "catalysts": news_data.get("upcoming_catalysts", []),
            "ml_signal": None,
            "portfolio_fit": portfolio_data.get("reason") if portfolio_data else None,
            "action": _extract_action(final_text),
            "full_report_markdown": final_text,
            "model_disagreements": disagreements,
            "data_freshness": now,
            "technical_snapshot": _map_technical(tech_data),
            "forecast_model": None,
            "as_of": now,
            "is_forecast": True,
        }

        # Collect all warnings
        for v in tool_results.values():
            if isinstance(v, dict):
                warnings.extend(v.get("warnings", []))
        result["warnings"] = warnings
        result["agents_invoked"] = agents_invoked

        return result

    async def _dispatch_tool(
        self,
        name: str,
        inp: dict[str, Any],
        http: httpx.AsyncClient,
        portfolio_id: str | None,
    ) -> dict[str, Any]:
        try:
            if name == "run_fundamental_agent":
                r = await self._fundamental.run(inp["ticker"], http)
                return r.model_dump()
            elif name == "run_technical_agent":
                r = await self._technical.run(inp["ticker"], http)
                return r.model_dump()
            elif name == "run_news_agent":
                r = await self._news.run(inp["ticker"], http)
                return r.model_dump()
            elif name == "run_macro_agent":
                r = await self._macro.run(http)
                return r.model_dump()
            elif name == "run_graph_agent":
                r = await self._graph.run(
                    inp["ticker"], inp.get("portfolio_tickers", []), http
                )
                return r.model_dump()
            elif name == "run_portfolio_agent":
                pid = inp.get("portfolio_id") or portfolio_id
                if not pid:
                    return {"error": "portfolio_id required", "warnings": ["No portfolio_id provided"]}
                r = await self._portfolio.run(inp["ticker"], pid, http)
                return r.model_dump()
            elif name == "run_quant_valuation":
                resp = await http.post(
                    f"{self._quant_url}/valuation/{inp['ticker']}",
                    json={k: v for k, v in inp.items() if k != "ticker"},
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"Quant service error: {resp.status_code}", "warnings": [], "data": []}
        except Exception as e:
            return {"error": str(e), "warnings": [f"Tool {name} failed: {e}"], "data": None}
        return {"error": f"Unknown tool: {name}", "warnings": [], "data": None}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _infer_signals(fund: dict[str, Any], tech: dict[str, Any], val: dict[str, Any]) -> dict[str, str]:
    # Fundamentals signal
    fund_sig = "neutral"
    if fund.get("eps_beat") is True and fund.get("guidance_direction") in ("raised", "maintained"):
        fund_sig = "positive"
    elif fund.get("eps_beat") is False or fund.get("guidance_direction") == "lowered":
        fund_sig = "negative"

    # Momentum signal
    mom_sig = "neutral"
    momentum = tech.get("momentum")
    if momentum in ("strong", "overbought"):
        mom_sig = "positive"
    elif momentum in ("weak", "oversold"):
        mom_sig = "negative"

    # Valuation signal — compare current price to aggregate base
    val_sig = "neutral"
    val_list = val.get("data", []) if isinstance(val.get("data"), list) else []
    agg = next((v for v in val_list if v.get("method") == "aggregate"), None)
    current = tech.get("current_price")
    if agg and current:
        base = agg.get("base")
        if base and base > 0:
            gap = (float(base) - float(current)) / float(base)
            if gap > 0.10:
                val_sig = "positive"  # trading below fair value
            elif gap < -0.10:
                val_sig = "negative"  # trading above fair value

    return {"fundamentals": fund_sig, "valuation": val_sig, "momentum": mom_sig}


def _detect_disagreements(signals: dict[str, str], tool_results: dict[str, Any]) -> list[str]:
    disagreements: list[str] = []
    if signals["valuation"] == "negative" and signals["momentum"] == "positive":
        disagreements.append("Valuation is rich while momentum is strong — price may be running ahead of fundamentals.")
    if signals["fundamentals"] == "positive" and signals["momentum"] == "negative":
        disagreements.append("Fundamentals are improving but price momentum is weak — potential value opportunity or thesis still developing.")
    if signals["fundamentals"] == "negative" and signals["momentum"] == "positive":
        disagreements.append("Price momentum is strong despite weak fundamentals — momentum-driven move may not be sustained.")
    return disagreements


def _extract_verdict(text: str, ticker: str) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("**Verdict**") or line.lower().startswith("verdict:"):
            verdict = line.split(":", 1)[-1].strip().lstrip("*").strip()
            if verdict:
                return verdict
    # Fallback: first non-empty sentence
    for sent in text.replace("\n", " ").split("."):
        s = sent.strip()
        if len(s) > 20:
            return s + "."
    return f"Analysis complete for {ticker}."


def _extract_action(text: str) -> str:
    for keyword in ("Avoid", "Watch", "Research", "Hold"):
        if keyword in text:
            return keyword
    return "Hold"


def _map_earnings(fund: dict[str, Any]) -> dict[str, Any] | None:
    if not fund or not fund.get("latest_period"):
        return None
    return {
        "ticker": fund.get("ticker", ""),
        "fiscal_period": fund.get("latest_period"),
        "revenue": fund.get("revenue"),
        "revenue_growth": fund.get("revenue_growth"),
        "gross_margin": fund.get("gross_margin"),
        "operating_margin": fund.get("operating_margin"),
        "net_margin": fund.get("net_margin"),
        "eps": fund.get("eps_actual"),
        "eps_expected": fund.get("eps_expected"),
        "fcf": fund.get("fcf"),
        "guidance_revenue": fund.get("guidance_revenue"),
        "guidance_eps": fund.get("guidance_eps"),
        "source": "fundamental_agent",
        "as_of": fund.get("as_of", ""),
    }


def _map_technical(tech: dict[str, Any]) -> dict[str, Any] | None:
    if not tech:
        return None
    return {
        "rsi_14": tech.get("rsi_14"),
        "macd_line": tech.get("macd_line"),
        "macd_signal": tech.get("macd_signal"),
        "macd_hist": tech.get("macd_hist"),
        "sma_20": tech.get("sma_20"),
        "sma_50": tech.get("sma_50"),
        "sma_200": tech.get("sma_200"),
        "atr_14": tech.get("atr_14"),
        "vwap": tech.get("vwap"),
        "relative_volume": tech.get("relative_volume"),
        "as_of": tech.get("as_of", ""),
    }
