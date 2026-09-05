# ADR 0002 — Quant Engine as a standalone FastAPI service

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 2 (Ticker analysis)

## Context

Every number shown to users — volatility, VaR, Sharpe, DCF output, Monte Carlo
target probability — must originate from a deterministic engine, not an LLM
(CLAUDE.md §2 and §9). These calculations need to be:

- Independently testable with known-answer cases.
- Callable from Supabase Edge Functions (Deno/TypeScript).
- Isolated from the orchestrator so Python and TypeScript can both reach them.

## Decision

`services/quant` is a FastAPI service exposing pure Python functions over HTTP.
The functions themselves have no I/O; they receive arrays/scalars as JSON and
return JSON. The HTTP layer is thin; all logic lives in the `quant_engine`
modules which are directly importable for unit tests.

Modules:
- `returns.py` — log returns, total return, CAGR
- `risk.py` — volatility, beta, drawdown, VaR, CVaR, Sharpe, Sortino, correlation
- `indicators.py` — SMA, EMA, RSI, MACD, ATR, VWAP, support/resistance
- `valuation.py` — P/E, forward P/E, EV/EBITDA, DCF, P/S, peers (all as ranges)
- `monte_carlo.py` — GBM portfolio simulation for target-return probability
- `api.py` — FastAPI app wiring the above into HTTP endpoints

## Consequences

**Positive**
- Every function is unit-tested with known answers before Claude ever sees output.
- Edge Functions call `/valuation/dcf` the same way they call `/risk/var` — one
  HTTP client pattern.
- Adding a new method (e.g. residual income model) is a new module + new endpoint
  with no changes to the orchestrator.

**Negative**
- Another service to deploy and keep running. Mitigated by a single Docker image
  with a health endpoint.
- Latency: Edge Function → quant service round-trip adds ~20–50 ms per call.
  Acceptable given calls are made once per orchestration run, not per UI render.

## Alternatives considered

- **Call numpy directly from Edge Functions** — not possible; Deno does not have
  numpy. WASM ports exist but are immature for scientific computing.
- **Inline calculations in the orchestrator** — mixes deterministic code with
  LLM orchestration logic; harder to test in isolation and harder to audit.
