"""CLI for the orchestrator service. Usage: python -m orchestrator.cli analyze AAPL"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")


def _analyst():
    from orchestrator.chief_analyst import ChiefAnalyst
    return ChiefAnalyst(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        quant_url=os.environ.get("QUANT_URL", "http://localhost:8001"),
        graph_url=os.environ.get("GRAPH_URL", "http://localhost:8003"),
    )


async def _analyze(ticker: str, portfolio_id: str | None) -> None:
    result = await _analyst().analyze_ticker(ticker, portfolio_id)
    _print_summary(result)
    print("\n" + "─" * 60)
    print(result.get("full_report_markdown", ""))


async def _compare(tickers: list[str]) -> None:
    import asyncio
    analyst = _analyst()
    analyses = await asyncio.gather(*[analyst.analyze_ticker(t) for t in tickers])
    print(f"\n{'Ticker':<8} {'Fundamentals':<14} {'Valuation':<12} {'Momentum':<12} {'Action':<10}")
    print("─" * 60)
    for a in analyses:
        if isinstance(a, Exception):
            continue
        sigs = a.get("signals", {})
        print(
            f"{a['ticker']:<8} {sigs.get('fundamentals','?'):<14} "
            f"{sigs.get('valuation','?'):<12} {sigs.get('momentum','?'):<12} "
            f"{a.get('action','?'):<10}"
        )


async def _brief(portfolio_id: str) -> None:
    import httpx
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"{os.environ.get('ORCHESTRATOR_URL','http://localhost:8002')}/brief/{portfolio_id}"
        )
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return
        brief = resp.json().get("data", {})

    day_ret = brief.get("portfolio_return", 0)
    health = brief.get("health_score", 0)
    risk = brief.get("risk_level", "?")
    prob = brief.get("target_probability", 0)
    prob_delta = brief.get("target_probability_delta", 0)

    print(f"\n📊 DAILY PORTFOLIO BRIEF")
    print(f"Portfolio: {day_ret:+.1%}")
    print(f"Health Score: {health:.0f}/100   Risk: {risk.title()}")
    print(f"\n🎯 Objective")
    print(f"Est. probability: {prob:.0%}  (delta {prob_delta:+.0%})")

    important = brief.get("important", [])
    if important:
        print(f"\n⚠️  IMPORTANT")
        for item in important[:3]:
            print(f"  · {item.get('summary','')}")

    catalysts = brief.get("catalysts", [])
    if catalysts:
        print(f"\n📰 CATALYSTS")
        for c in catalysts[:3]:
            print(f"  · {c.get('ticker','')} — {c.get('description','')} ({c.get('date','')})")

    opps = brief.get("opportunities", [])
    if opps:
        print(f"\n📈 OPPORTUNITIES")
        for o in opps[:5]:
            print(f"  {o.get('ticker',''):<6} {o.get('score',0):.0f}/100  {o.get('one_line_thesis','')}")

    plan = brief.get("action_plan", [])
    if plan:
        print(f"\n🔎 TOMORROW")
        for p in plan:
            print(f"  {p.get('ticker',''):<6} {p.get('action',''):<10}  {p.get('reason','')}")

    if brief.get("rebalance_required"):
        print("\n⚖️  Rebalance required.")

    print("\nThis report is for research purposes only. Not investment advice.")


def _print_summary(result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  {result['ticker']}  —  {result.get('action','?')}")
    print(f"{'='*60}")
    print(f"Verdict: {result.get('verdict','')}")
    sigs = result.get("signals", {})
    print(f"\nSignals:")
    print(f"  Fundamentals : {sigs.get('fundamentals','?')}")
    print(f"  Valuation    : {sigs.get('valuation','?')}")
    print(f"  Momentum     : {sigs.get('momentum','?')}")
    disc = result.get("model_disagreements", [])
    if disc:
        print(f"\n⚠️  Disagreements:")
        for d in disc:
            print(f"  · {d}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="orchestrator.cli")
    sub = parser.add_subparsers(dest="cmd")

    p_analyze = sub.add_parser("analyze")
    p_analyze.add_argument("ticker")
    p_analyze.add_argument("--portfolio", default=None)

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("tickers", nargs="+")

    p_brief = sub.add_parser("brief")
    p_brief.add_argument("portfolio_id")

    args = parser.parse_args()
    if args.cmd == "analyze":
        asyncio.run(_analyze(args.ticker.upper(), args.portfolio))
    elif args.cmd == "compare":
        asyncio.run(_compare([t.upper() for t in args.tickers]))
    elif args.cmd == "brief":
        asyncio.run(_brief(args.portfolio_id))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
