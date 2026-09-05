"""Chief Analyst — orchestrates agents, calls Claude to synthesize evidence.

Claude's role here is strictly synthesis: it reads structured agent outputs
and writes the verdict, signals, and report. It never produces numbers.
Every number in the response comes from an agent result (which in turn comes
from the quant service or Supabase).
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import anthropic

from .config import settings
from .models import AgentResult, AnalyzeResponse, SignalDirection

CHIEF_ANALYST_SYSTEM = """You are the Chief Analyst of an AI equity research platform.

Your role is STRICTLY synthesis. You orchestrate specialized agents, read their
structured outputs, and write a research summary. You NEVER invent or estimate
numbers — every statistic, price, ratio, and probability comes from the agents.

When agents provide conflicting signals, surface the disagreement explicitly rather
than averaging it away.

Valuation: always a range (low/base/high, bear/bull), never a single target.

Output format: respond ONLY with valid JSON matching the requested schema.
Safety: never guarantee returns; never suggest executing trades.
"""

ANALYZE_PROMPT_TEMPLATE = """Analyze {ticker} based on the following agent evidence.

FUNDAMENTAL DATA:
{fundamental}

TECHNICAL DATA:
{technical}

NEWS & CATALYSTS:
{news}

GRAPH RELATIONSHIPS:
{graph}

PORTFOLIO FIT:
{portfolio}

Respond with JSON in this exact schema:
{{
  "verdict": "<one sentence — the most important takeaway, max 150 chars>",
  "signals": {{
    "fundamentals": "<positive|neutral|negative>",
    "valuation": "<positive|neutral|negative>",
    "momentum": "<positive|neutral|negative>"
  }},
  "action": "<Watch|Hold|Research|Avoid>",
  "portfolio_fit_summary": "<one sentence on portfolio fit, or null if no portfolio context>",
  "model_disagreements": ["<list any signals that conflict with each other>"],
  "full_report_markdown": "<complete markdown research report with all evidence, sources, and freshness>"
}}
"""


class ChiefAnalyst:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze(
        self,
        ticker: str,
        fundamental: AgentResult,
        technical: AgentResult,
        news: AgentResult,
        graph: AgentResult,
        portfolio: AgentResult | None = None,
    ) -> AnalyzeResponse:
        run_id = str(uuid.uuid4())

        prompt = ANALYZE_PROMPT_TEMPLATE.format(
            ticker=ticker,
            fundamental=json.dumps(fundamental.data, indent=2, default=str),
            technical=json.dumps(technical.data, indent=2, default=str),
            news=json.dumps(news.data, indent=2, default=str),
            graph=json.dumps(graph.data, indent=2, default=str),
            portfolio=json.dumps(portfolio.data if portfolio else {}, indent=2, default=str),
        )

        message = await self._client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=CHIEF_ANALYST_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text if message.content else "{}"

        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            parsed: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "verdict": "Analysis complete — see full report for details.",
                "signals": {"fundamentals": "neutral", "valuation": "neutral", "momentum": "neutral"},
                "action": "Research",
                "portfolio_fit_summary": None,
                "model_disagreements": [],
                "full_report_markdown": raw,
            }

        all_as_of = [fundamental.as_of, technical.as_of, news.as_of, graph.as_of]
        data_freshness = f"Fundamental: {fundamental.as_of} | Technical: {technical.as_of} | News: {news.as_of}"

        return AnalyzeResponse(
            ticker=ticker,
            run_id=run_id,
            verdict=parsed.get("verdict", ""),
            signals=SignalDirection(**parsed.get("signals", {"fundamentals": "neutral", "valuation": "neutral", "momentum": "neutral"})),
            valuation_range=None,   # populated by the route after calling quant service
            action=parsed.get("action", "Research"),
            portfolio_fit=parsed.get("portfolio_fit_summary"),
            full_report_markdown=parsed.get("full_report_markdown", ""),
            model_disagreements=parsed.get("model_disagreements", []),
            data_freshness=data_freshness,
            as_of=max(all_as_of),
            is_forecast=True,
        )

    async def compare(self, tickers: list[str], rows: list[dict[str, Any]]) -> str:
        """Generate a Chief Analyst summary comparing multiple tickers."""
        prompt = (
            f"Compare these {len(tickers)} companies: {', '.join(tickers)}\n\n"
            f"Comparison data:\n{json.dumps(rows, indent=2, default=str)}\n\n"
            "Write ONE sentence that names the most interesting trade-off — e.g. "
            "\"Is Company C's 31% growth worth paying 55× earnings?\" "
            "Do not recommend a buy/sell. Max 200 chars."
        )
        message = await self._client.messages.create(
            model=settings.claude_model,
            max_tokens=256,
            system=CHIEF_ANALYST_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip() if message.content else ""
