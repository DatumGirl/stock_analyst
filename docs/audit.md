# Feature Audit: App vs. Analyst Workflow

Audit date: 2026-09-05
Reference: `docs/analyst_workflow.md`

---

## What's Built

| Capability | Status | Location |
|---|---|---|
| Graph schema (nodes + edges) | Built | `services/graph/graph_service/schema.py` |
| Company relationships query | Built | `services/graph/graph_service/agent.py` |
| Supply-chain traversal | Built | `services/graph/graph_service/agent.py` |
| ETF overlap detection | Built | `services/graph/graph_service/agent.py` |
| Hidden concentration | Built | `services/graph/graph_service/agent.py` |
| Event propagation | Built | `services/graph/graph_service/agent.py` |
| Peer group query | Built | `services/graph/graph_service/agent.py` |
| Theme/geography exposure | Built | `services/graph/graph_service/agent.py` |
| Data freshness monitoring | Built | `services/graph/graph_service/agent.py` |
| Idempotent batch ingestion | Built | `services/graph/graph_service/ingest.py` |
| Supabase config | Built | `supabase/config.toml` |
| Foundation schema (profiles, portfolios, positions, watchlists, tickers) | Built | `supabase/migrations/20260905000001_foundation.sql` |
| Market data schema (prices_daily, fundamentals, estimates) | Built | `supabase/migrations/20260905000002_market_data.sql` |
| Analysis schema (valuations, news, catalysts, snapshots, signals, alerts) | Built | `supabase/migrations/20260905000003_analysis.sql` |
| Seed data (18 reference tickers) | Built | `supabase/seed.sql` |
| Quant: returns (daily, total, CAGR) | Built | `services/quant/quant_engine/returns.py` |
| Quant: risk (vol, beta, drawdown, VaR, CVaR, Sharpe, Sortino, correlation) | Built | `services/quant/quant_engine/risk.py` |
| Quant: indicators (SMA, EMA, RSI, MACD, ATR, VWAP, support/resistance) | Built | `services/quant/quant_engine/indicators.py` |
| Quant: valuation (P/E, fwd P/E, EV/EBITDA, DCF, P/S, peers — all as ranges) | Built | `services/quant/quant_engine/valuation.py` |
| Quant: Monte Carlo target-return probability | Built | `services/quant/quant_engine/monte_carlo.py` |
| Quant: FastAPI HTTP service | Built | `services/quant/quant_engine/api.py` |
| Quant: unit tests (known-answer cases) | Built | `services/quant/tests/` |

---

## Remaining Gaps

| Phase | Capability | Gap |
|---|---|---|
| 2 | **Orchestrator service** | No `services/orchestrator/` — no Claude API integration, no agent routing, no chief analyst loop |
| 2 | **Fundamental agent** | No financial statement fetching, earnings vs. estimates scoring, guidance analysis |
| 2 | **Technical agent** | No price-data fetching; indicators built but not wired to a data source |
| 2 | **News agent** | No news ingestion, no SEC filing parser, no materiality scoring pipeline |
| 2 | **Macro agent** | No futures/rates/commodities feed, no regime detection |
| 2 | **`analyze-ticker` Edge Function** | No Supabase function orchestrating agents for a single ticker |
| 3 | **Portfolio engine** | No snapshots job, no health score calculation, no exposure aggregation |
| 3 | **`portfolio-snapshot` Edge Function** | No scheduled snapshot job |
| 4 | **Daily pipeline Edge Functions** | No `premarket-brief`, `eod-report`, `risk-monitor`, `push-dispatch` |
| 4 | **Telegram delivery** | No bot integration |
| 5 | **Graph → orchestrator wiring** | Graph service built but not wired to orchestrator as a tool |
| 6 | **ML service** | No `services/ml/` — no ranking, next-day probability, regime detection |
| 7 | **Compare & intraday** | No `/compare` endpoint, no intraday "why is it moving" pipeline |
| All | **iOS app** | No `ios/` directory — no SwiftUI app, no screens, no design system components |
| All | **Market data connectors** | No price/earnings/SEC/macro data ingestion scripts |

---

## Build Phase Progress

| Phase | Description | Status |
|---|---|---|
| 1 | Foundation (Supabase schema + auth + price ingestion) | Schema done; market data connectors pending; iOS pending |
| 2 | Ticker analysis (agents + quant + Edge Function + Ticker screen) | Quant engine done; agents + orchestrator + iOS pending |
| 3 | Portfolio engine | Not started |
| 4 | Daily workflow | Not started |
| 5 | Graph intelligence | **Done** |
| 6 | ML signals | Not started |
| 7 | Compare & intraday | Not started |
