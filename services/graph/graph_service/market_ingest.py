"""Live market data ingest — build Memgraph nodes/edges from yfinance ETF holdings."""

from __future__ import annotations

import asyncio
import datetime
from collections import defaultdict
from typing import Any

from .ingest import IngestReport, ingest
from .schema import GraphEdge, GraphNode, NodeLabel, Provenance, RelType

ETF_UNIVERSE = ["QQQ", "XLK", "SMH", "SOXX", "VGT"]
DEFAULT_MAX_PER_ETF = 25

# Sector → theme slugs
SECTOR_THEMES: dict[str, list[str]] = {
    "Technology": ["tech-growth", "digital-infrastructure"],
    "Communication Services": ["digital-media", "tech-growth"],
    "Consumer Cyclical": ["consumer-discretionary"],
    "Consumer Defensive": ["consumer-staples"],
    "Healthcare": ["biotech-innovation", "healthcare"],
    "Financial Services": ["fintech", "financial-services"],
    "Energy": ["energy-transition"],
    "Industrials": ["industrial-automation"],
    "Basic Materials": ["commodities"],
}

# Industry → theme slugs (supplements sector mapping)
INDUSTRY_THEMES: dict[str, list[str]] = {
    "Semiconductors": ["ai-infrastructure", "semiconductor-supply-chain"],
    "Semiconductor Equipment & Materials": ["semiconductor-supply-chain"],
    "Software—Application": ["saas", "ai-infrastructure"],
    "Software—Infrastructure": ["cloud-infrastructure", "saas"],
    "Internet Content & Information": ["digital-media", "ai-infrastructure"],
    "Consumer Electronics": ["consumer-tech"],
    "Drug Manufacturers—General": ["biotech-innovation"],
    "Biotechnology": ["biotech-innovation"],
}


def _yf_fetch(
    explicit_tickers: list[str],
    etf_list: list[str],
    max_per_etf: int,
) -> dict[str, Any]:
    """Blocking yfinance calls — run via run_in_executor."""
    import yfinance as yf

    today = datetime.date.today()
    companies: dict[str, dict[str, Any]] = {t: {"symbol": t} for t in explicit_tickers}
    etf_info: dict[str, dict[str, Any]] = {}
    held_by_rows: list[tuple[str, str, float]] = []  # (company, etf, weight)

    # ── ETF holdings ──────────────────────────────────────────────────────────
    for etf_sym in etf_list:
        try:
            t = yf.Ticker(etf_sym)
            info = t.info or {}
            etf_info[etf_sym] = {"name": info.get("longName") or etf_sym}

            df = None
            try:
                df = t.funds_data.top_holdings
            except Exception:
                pass

            if df is not None and not df.empty:
                df = df.head(max_per_etf).copy()
                df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

                sym_col = next((c for c in df.columns if "symbol" in c), None)
                wt_col = next(
                    (c for c in df.columns if "percent" in c or "weight" in c), None
                )

                # Some versions use the index as the symbol
                if sym_col is None:
                    syms = [str(s).upper().strip() for s in df.index.tolist()]
                    wts = df[wt_col].tolist() if wt_col else [0.01] * len(syms)
                else:
                    syms = [str(s).upper().strip() for s in df[sym_col].tolist()]
                    wts = df[wt_col].tolist() if wt_col else [0.01] * len(syms)

                for sym, raw_w in zip(syms, wts):
                    if not sym or sym in ("NAN", "NONE", ""):
                        continue
                    try:
                        w = float(raw_w)
                        if w > 1.0:  # yfinance occasionally returns 0-100 scale
                            w = w / 100.0
                        w = min(max(w, 0.001), 1.0)
                    except (TypeError, ValueError):
                        w = 0.01
                    held_by_rows.append((sym, etf_sym, w))
                    companies.setdefault(sym, {"symbol": sym})
        except Exception:
            pass

    # ── Company info ──────────────────────────────────────────────────────────
    for sym in list(companies.keys()):
        try:
            info = yf.Ticker(sym).info or {}
            companies[sym].update({
                "name": info.get("longName") or info.get("shortName") or sym,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
            })
        except Exception:
            companies[sym].setdefault("name", sym)

    return {
        "today": today,
        "companies": companies,
        "etf_info": etf_info,
        "held_by": held_by_rows,
    }


def build_graph_objects(
    data: dict[str, Any],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Translate raw yfinance data into validated GraphNode/GraphEdge objects."""
    today: datetime.date = data["today"]
    companies: dict[str, dict[str, Any]] = data["companies"]
    etf_info: dict[str, dict[str, Any]] = data["etf_info"]
    held_by_rows: list[tuple[str, str, float]] = data["held_by"]

    prov = Provenance(source="yfinance", as_of=today, confidence=0.9)
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    sectors_seen: set[str] = set()
    industries_seen: set[str] = set()
    themes_seen: set[str] = set()
    countries_seen: set[str] = set()
    company_industry: dict[str, str] = {}

    # ── ETF nodes ─────────────────────────────────────────────────────────────
    for etf_sym, info in etf_info.items():
        nodes.append(GraphNode(
            label=NodeLabel.ETF,
            key=etf_sym,
            properties={"name": info["name"]},
            provenance=prov,
        ))

    # ── Company nodes + taxonomy edges ────────────────────────────────────────
    for sym, co in companies.items():
        sector = co.get("sector")
        industry = co.get("industry")
        country = co.get("country")

        nodes.append(GraphNode(
            label=NodeLabel.COMPANY,
            key=sym,
            properties={"name": co.get("name", sym)},
            provenance=prov,
        ))

        if sector:
            if sector not in sectors_seen:
                sectors_seen.add(sector)
                nodes.append(GraphNode(
                    label=NodeLabel.SECTOR,
                    key=sector,
                    properties={"name": sector},
                    provenance=prov,
                ))
            edges.append(GraphEdge(
                rel_type=RelType.IN_SECTOR,
                start=(NodeLabel.COMPANY, sym),
                end=(NodeLabel.SECTOR, sector),
                provenance=prov,
            ))

        if industry:
            company_industry[sym] = industry
            if industry not in industries_seen:
                industries_seen.add(industry)
                nodes.append(GraphNode(
                    label=NodeLabel.INDUSTRY,
                    key=industry,
                    properties={"name": industry},
                    provenance=prov,
                ))
            edges.append(GraphEdge(
                rel_type=RelType.IN_INDUSTRY,
                start=(NodeLabel.COMPANY, sym),
                end=(NodeLabel.INDUSTRY, industry),
                provenance=prov,
            ))

        if country:
            if country not in countries_seen:
                countries_seen.add(country)
                nodes.append(GraphNode(
                    label=NodeLabel.COUNTRY,
                    key=country,
                    properties={"name": country},
                    provenance=prov,
                ))
            edges.append(GraphEdge(
                rel_type=RelType.OPERATES_IN,
                start=(NodeLabel.COMPANY, sym),
                end=(NodeLabel.COUNTRY, country),
                weight=1.0,
                provenance=prov,
            ))

        # Theme edges — industry mapping takes precedence, then sector
        theme_keys: set[str] = set()
        if industry and industry in INDUSTRY_THEMES:
            theme_keys.update(INDUSTRY_THEMES[industry])
        if sector and sector in SECTOR_THEMES:
            theme_keys.update(SECTOR_THEMES[sector])

        for theme_key in theme_keys:
            if theme_key not in themes_seen:
                themes_seen.add(theme_key)
                nodes.append(GraphNode(
                    label=NodeLabel.THEME,
                    key=theme_key,
                    properties={"name": theme_key.replace("-", " ").title()},
                    provenance=prov,
                ))
            edges.append(GraphEdge(
                rel_type=RelType.PART_OF_THEME,
                start=(NodeLabel.COMPANY, sym),
                end=(NodeLabel.THEME, theme_key),
                provenance=prov,
            ))

    # ── HELD_BY edges ─────────────────────────────────────────────────────────
    for company_sym, etf_sym, weight in held_by_rows:
        if company_sym not in companies or etf_sym not in etf_info:
            continue
        edges.append(GraphEdge(
            rel_type=RelType.HELD_BY,
            start=(NodeLabel.COMPANY, company_sym),
            end=(NodeLabel.ETF, etf_sym),
            weight=weight,
            provenance=prov,
        ))

    # ── COMPETES_WITH edges (same industry, different company) ────────────────
    industry_members: dict[str, list[str]] = defaultdict(list)
    for sym, ind in company_industry.items():
        industry_members[ind].append(sym)

    seen_pairs: set[frozenset[str]] = set()
    for members in industry_members.values():
        if len(members) < 2:
            continue
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                pair: frozenset[str] = frozenset({a, b})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                edges.append(GraphEdge(
                    rel_type=RelType.COMPETES_WITH,
                    start=(NodeLabel.COMPANY, a),
                    end=(NodeLabel.COMPANY, b),
                    provenance=prov,
                ))

    return nodes, edges


async def run_live_ingest(
    runner: Any,
    explicit_tickers: list[str],
    etf_list: list[str],
    max_per_etf: int,
) -> dict[str, Any]:
    """Fetch yfinance data, build graph primitives, and write to Memgraph."""
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(
        None, _yf_fetch, explicit_tickers, etf_list, max_per_etf
    )
    nodes, edges = build_graph_objects(data)
    report: IngestReport = ingest(runner, nodes, edges)
    return {
        "companies_found": len(data["companies"]),
        "etfs_processed": len(data["etf_info"]),
        "nodes_written": report.nodes_written,
        "edges_written": report.edges_written,
        "skipped_edges": len(report.skipped_edges),
        "skipped_details": report.skipped_edges[:10],
    }
