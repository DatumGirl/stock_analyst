# Mobile App Audit — Stock Analyst Workflow
**Date:** 2026-09-05  
**Source:** `stock_analyst_daily_workflow.md` (15 sections)  
**Scope:** Expo React Native mobile app (`stock_analyst/mobile/`)

---

## Executive Summary

The mobile app is a strong first pass at the consumption layer. The safety
architecture (`is_forecast` literals, `FreshnessStamp`, `model_disagreements`,
disclaimers on every screen), the type system, and the daily-brief / portfolio
views are well-aligned with the workflow. The biggest gaps are surface-level
omissions — macro context, technical indicator values, the catalyst section on
the Today tab, watchlist management, and the risk-metrics card — rather than
structural problems. No screen requires a rewrite; all gaps are additive.

---

## Coverage Matrix

| Workflow Section | Status | Summary |
|---|---|---|
| §1 Daily workflow rhythm | Partial | Brief + Portfolio cover AM/EOD. No morning watchlist creation. |
| §2 Morning overnight scan | Partial | `MarketChart` on Today tab; no futures/rates/FX/commodities data. |
| §3 Earnings analysis | Partial | Table shown; beat/miss delta, guidance EPS, FCF, and segments missing. |
| §4 Financial model (forecasts) | Missing | No multi-year forward table; `assumptions_version` not surfaced. |
| §5 Valuation | Good | All 9 methods typed; `RangeBar` + bull/base/bear rendered; method label shown. |
| §6 Price action / "why moving?" | Partial | `what_is_driving` section is correct; no individual technical indicator values. |
| §7 Peer comparison | Good | `/compare` screen with 8-metric table + chief analyst summary. |
| §8 Relationship intelligence | Partial | Relationships list on ticker screen; hidden-concentration tab in portfolio. |
| §9 Portfolio-fit thinking | Good | `portfolio_fit` text, CAGR target, target-probability delta in Brief. |
| §10 Continuous risk monitoring | Partial | Exposure tabs + hidden concentration shown; VaR/Sharpe/beta not rendered. |
| §11 End-of-day delta | Good | `PortfolioChange` covers all 7 change types; `what changed` list in Portfolio. |
| §12–13 Agent architecture | Good | `TickerSignals`, `verdict`, `model_disagreements` surface agent output. |
| §14 Core design principle | Good | Orchestrator pattern with portfolio-fit check in place. |
| §15 Safety / decision-support | Good | `is_forecast: true`, freshness stamps, disclaimer on every screen. |

---

## Strengths

### §5 Valuation — type system is complete
`ValuationMethod` enumerates all nine methods the workflow specifies (`pe`,
`fwd_pe`, `peg`, `ps`, `ev_ebitda`, `p_fcf`, `dcf`, `historical`, `peers`).
`ValuationRange` carries `bear`/`bull`/`low`/`base`/`high` plus
`assumptions_version` and `is_forecast: true`. The `RangeBar` component pins
the live price on the range and `ForecastPill` tags the section. This is
exactly the "range, not a single price target" requirement from §5.

### §15 Safety — enforced at the type layer
`is_forecast: true` as a literal type (not `boolean`) on `ValuationRange`,
`Signal`, `TickerAnalysis`, and `CompareAnalysis` means the compiler rejects
any response object that omits the flag. `FreshnessStamp` is placed on every
data surface (Today nav bar, ticker price card, portfolio header). The API
envelope carries a `warnings[]` array and `TickerAnalysis` exposes
`model_disagreements[]`, which the ticker screen renders as an amber banner.

### §11 End-of-day delta — seven change types typed and routed
`PortfolioChange.change_type` covers `price | news | fundamental | risk | graph
| ml | target_probability` — the exact seven categories the workflow diagram
specifies. `MaterialityRow` renders each with a type-appropriate icon. Changes
are shown in both the Portfolio ("What changed") and Today ("Important")
screens. `target_probability_delta` in `DailyBrief` maps directly to the
workflow's "Yesterday: 45% → Today: 47% → Change: +2%" example.

### §7 Peer comparison — metric selection is correct
`CompareRow` includes `revenue_growth`, `pe`, `fwd_pe`, `gross_margin`, `roic`,
`debt_to_equity`, `momentum_score`, and `fair_value_gap_pct`. This covers the
workflow's Growth / P/E / Margin / ROIC / Debt table from §7. A
`chief_analyst_summary` field brings the "Is Company C's 55× earnings
justified?" synthesis to the UI.

### §8 Hidden concentration — surfaced in portfolio
`HiddenConcentration` carries `dependency`, `tickers[]`, and `description`.
The portfolio's "Hidden" exposure tab renders these as amber warning rows,
matching the "⚠️ RISK CHANGE DETECTED — common semiconductor and AI
dependencies across four positions" example from §10.

---

## Gaps

### GAP-1 · Macro / market context is a placeholder (§2, §13 Market Agent)
**Priority: High**

The Today tab renders `<MarketChart />` under a "Markets" heading, but the
component takes no props and its data source is unknown. The `DailyBrief` type
has no fields for index futures, treasury yields, VIX, international market
moves, or commodities. The workflow explicitly lists these as the first thing an
analyst checks. The `Market/Macro Agent` in §13 has no corresponding UI surface.

**What's needed:**
- Add a `MacroSnapshot` type and a `macro` field to `DailyBrief` (SPX futures
  %, 10Y yield, VIX, DXY, crude).
- Pass the data into `MarketChart` (or replace it with a `MacroBar` row list).
- Add a `macro` alert type and catalyst type to surface rate or economic events.

---

### GAP-2 · Catalyst section missing from Today tab (§1, §11)
**Priority: High**

`DailyBrief` has a `catalysts: Catalyst[]` field but `index.tsx` never renders
it. The workflow's daily brief example (§11) explicitly calls out "📰 CATALYST —
One portfolio company reports earnings tomorrow." This is the most actionable
forward-looking signal and it is silently dropped.

**What's needed:**
- Add a "Catalysts" section between "Important" and "Opportunities" in
  `index.tsx`, using the existing `Catalyst` type.

---

### GAP-3 · Risk metrics card not rendered (§10)
**Priority: High**

`RiskMetrics` in the snapshot has `volatility_30d`, `beta`, `max_drawdown`,
`var_95`, `cvar_95`, `sharpe`, and `sortino` — all the metrics the workflow
lists. However, `portfolio.tsx` renders only three labelled progress bars
(Diversification, Risk, Quality scores) from the health card. The numeric risk
metrics (`RiskMetrics`) are never displayed anywhere in the app.

**What's needed:**
- Add a collapsible "Risk metrics" card below the health card in `portfolio.tsx`
  showing VaR 95%, CVaR 95%, Sharpe, Sortino, beta, and max drawdown as a
  simple grid.

---

### GAP-4 · Earnings table missing beat/miss delta and key fields (§3)
**Priority: Medium**

`EarningsTable` in `[symbol].tsx` shows Revenue, EPS, Gross margin, Operating
margin — but:
- No beat/miss colouring: EPS actual vs `eps_expected` is shown side-by-side
  but not highlighted green/red with a delta.
- `guidance_eps` is in `Fundamental` but not in the table (only
  `guidance_revenue` is shown).
- Free cash flow (`fcf`) is in `Fundamental` but not shown.
- No "Guidance revision" row comparing previous vs new guidance.

The workflow explicitly states (§3): "Guidance fell from $42B to $39B — this is
the most important number." The app would show the new guidance but not flag the
change or direction.

**What's needed:**
- Add a delta column to the earnings table with green/red for beats.
- Add FCF and guidance EPS rows.
- Add a guidance-change row when both previous and current guidance are present.

---

### GAP-5 · Technical indicator values not exposed (§6)
**Priority: Medium**

`TickerSignals.momentum` surfaces a `SignalDirection` (positive/neutral/negative)
but the Technical Agent (§13) is expected to produce RSI, MACD, ATR, VWAP, and
moving averages. None of these values are in `TickerAnalysis`, `TickerSignals`,
or any type in `types.ts`. The signal chip shows a direction but not the
evidence behind it.

**What's needed:**
- Add a `TechnicalSnapshot` interface with the key indicator values.
- Add a `technical_snapshot?: TechnicalSnapshot` field to `TickerAnalysis`.
- Add a collapsible "Technicals" section on the ticker screen (below Earnings)
  showing the values in a grid, tagged with `ForecastPill`.

---

### GAP-6 · Watchlist management is wired but not implemented (§1)
**Priority: Medium**

`Watchlist` and `WatchlistItem` types exist. The ticker screen nav bar has a
star icon with `accessibilityLabel="Add to watchlist"` but its `onPress` is
empty (no handler). The Research tab shows "recent tickers" but no user-managed
watchlists. The workflow calls out morning watchlist creation as a distinct step
between pre-market research and market open.

**What's needed:**
- Wire the star button on `[symbol].tsx` to a mutation that creates/toggles a
  watchlist item.
- Add a Watchlists section to the Research tab showing saved lists.

---

### GAP-7 · Full research report is unreachable (§12)
**Priority: Medium**

`TickerAnalysis.full_report_markdown` is produced by the orchestrator but there
is no "Read full report" button or expand section in `[symbol].tsx`. The verdict
card shows one sentence; the markdown report is discarded.

**What's needed:**
- Add a "Full report" collapsible section at the bottom of the ticker screen
  rendering the markdown string (use a lightweight markdown renderer or a
  WebView for the initial pass).

---

### GAP-8 · Multi-year financial model not present (§4)
**Priority: Low**

The workflow specifies that analysts maintain a forward model (Revenue / Growth /
Gross Margin / Operating Income / EPS / FCF for 2026–2028). There is no
type or screen for a multi-year forecast table. `ValuationRange.assumptions_version`
references a model version but the model itself is not surfaced.

**What's needed:**
- Define a `ForecastModel` type (year, revenue, revenue_growth, gross_margin,
  eps, fcf keyed by fiscal year).
- Add a `forecast_model?: ForecastModel[]` field to `TickerAnalysis`.
- Render a horizontal scroll table in the ticker screen (collapsed by default).

---

### GAP-9 · Period selector on Portfolio tab has no data effect (§1)
**Priority: Low**

`PERIOD_OPTIONS = ['1D', '1W', '1M', 'YTD', '1Y']` are selectable but
`usePortfolioSnapshot(activePortfolioId)` takes only an ID — there is no period
parameter. The selected period has no effect on the displayed snapshot.

**What's needed:**
- Add a `period` parameter to `usePortfolioSnapshot` and pass it to the API, or
  add `usePortfolioHistory(id, period)` that fetches a time-series and renders
  a sparkline chart instead of the current single-value card.

---

### GAP-10 · Add-position screen lacks portfolio-contribution analysis (§9)
**Priority: Low**

The workflow (§9) states: "A stock-ranking model may identify another technology
stock as attractive, but the portfolio engine may reject it because technology
exposure is already high." The `add-position.tsx` screen exists but has not been
audited here; based on the type system, `TickerAnalysis.portfolio_fit` is a free-
text string rather than a structured pre-add impact model.

**What's needed:**
- Before confirming a new position, call the orchestrator for a
  `portfolio_contribution` endpoint that returns expected sector/theme delta,
  correlation with existing holdings, and a go/no-go from the portfolio engine.
- Display the result as a confirmation step before saving.

---

## Summary — Prioritised Fix List

| # | Gap | Effort | Impact |
|---|---|---|---|
| 1 | Render `DailyBrief.catalysts` on Today tab | XS | High |
| 2 | Add macro snapshot fields + render in MarketChart | S | High |
| 3 | Add RiskMetrics card to Portfolio screen | S | High |
| 4 | Earnings beat/miss delta + FCF + guidance EPS | S | Medium |
| 5 | Wire watchlist star button on ticker screen | S | Medium |
| 6 | Add full_report_markdown expand section | S | Medium |
| 7 | Technical indicator values in TickerAnalysis | M | Medium |
| 8 | Period parameter on usePortfolioSnapshot | M | Low |
| 9 | Multi-year forecast model type + table | L | Low |
| 10 | Portfolio-contribution analysis on add-position | L | Low |
