# CLAUDE.md — AI Stock Intelligence Platform

This file is the working guide for Claude Code (and any other Claude instance) contributing to this repository. Read it fully before making changes. When in doubt, follow the principles in **Core Design Principle** and **Safety Rules** — they override everything else.

---

## 1. What we are building

A **mobile app (iOS, SwiftUI)** backed by **Supabase** that behaves like a digital equity-research and portfolio-management team, not a stock-picking chatbot.

The product mirrors a professional stock analyst's daily workflow. Every feature should help the user answer:

> **What changed? Why did it change? Does it change the investment thesis? What is the risk/reward now?**

Two primary workflows must be supported end-to-end:

1. **Daily portfolio-management workflow** — pre-market brief → intraday monitoring → end-of-day "what changed" report → tomorrow's action plan.
2. **Next-trading-day ticker analysis** — `/analyze AAPL`, `/compare AAPL MSFT NVDA`, etc.

---

## 2. Core Design Principle (non-negotiable)

**Do not build a system where Claude simply picks stocks.**

Roles are strictly separated:

| Layer | Responsibility | Never does |
|---|---|---|
| **Claude — Chief Analyst** | Orchestrates, decides which agents/tools to call, synthesizes evidence, explains conflicting signals, writes the final report | Compute a number, invent a price, ratio, or probability |
| **Specialized agents** (Fundamental, Technical, News, Macro, Graph, Portfolio) | Gather and structure evidence in their domain | Make the final recommendation |
| **Quant Engine** (deterministic Python) | Returns, volatility, correlation, beta, Sharpe, Sortino, VaR, CVaR, indicators, Monte Carlo, optimization | Interpret results |
| **ML Engine** | Next-day probability, stock ranking, volatility forecast, regime detection, risk prediction | Present outputs as facts |
| **Graph (Memgraph)** | Supplier / customer / competitor / ETF / geography / theme relationships; event propagation; hidden concentration | Store time-series or user data |
| **Portfolio / Risk Engine** | "Is X a good addition to *this* portfolio?" — allocation, correlation, sector & graph exposure, risk limits, target-return probability, rebalance needs | Ignore the user's existing holdings |

**Every number shown to the user must originate from a deterministic engine or a data provider — never from an LLM.** Claude reasons *over* validated numbers; it does not produce them.

---

## 3. Tech stack

### Mobile (iOS)
- Swift 5.10+, SwiftUI, iOS 17+ minimum
- Architecture: MVVM + a thin `Repository` layer over Supabase
- `supabase-swift` SDK (Auth, PostgREST, Realtime, Functions, Storage)
- Swift Package Manager only; no CocoaPods
- Charts: Swift Charts
- Push: APNs via Supabase Edge Function → APNs (no third-party push SDK initially)
- Testing: XCTest + Swift Testing; ViewModels must be unit-testable without network

### Backend (Supabase)
- **Postgres** — system of record for users, portfolios, positions, watchlists, snapshots, reports, model versions
- **Auth** — email/password + Sign in with Apple. RLS on every user-facing table.
- **Edge Functions** (Deno / TypeScript) — API surface for the app, orchestration entry points, scheduled jobs, push delivery
- **pg_cron + pg_net** — schedule pre-market (05:30 ET), close (16:15 ET), and end-of-day (18:00 ET) pipelines
- **Realtime** — stream price/alert updates to the app
- **Storage** — generated PDF/markdown reports
- **Vault** — third-party API keys; never in code or migrations

### Analysis services (outside Supabase, called by Edge Functions)
- `services/quant` — Python 3.12, FastAPI, numpy/pandas/scipy. Deterministic. Fully unit-tested.
- `services/ml` — Python, scikit-learn / LightGBM initially. Versioned models with stored metrics.
- `services/graph` — Memgraph + Python client (GQLAlchemy). Cypher queries live in `services/graph/queries/`.
- `services/orchestrator` — Python; runs the Chief Analyst loop using the Anthropic API with tool use. Agents are tools.

### Notifications
- iOS push (primary), Telegram bot (secondary, same report payload)

---

## 4. Repository layout

```
.
├── CLAUDE.md
├── docs/
│   ├── analyst_workflow.md        # source spec — the daily analyst workflow
│   ├── architecture.md
│   └── decisions/                 # ADRs, one file per decision
├── ios/
│   └── StockIntel/
│       ├── StockIntel.xcodeproj
│       ├── App/                   # entry, DI container, config
│       ├── Features/              # one folder per screen: Brief, Portfolio, Ticker, Compare, Alerts, Settings
│       │   └── <Feature>/{View,ViewModel,Models}
│       ├── Data/                  # Supabase client, repositories, DTOs
│       ├── Domain/                # pure Swift models, no imports of Supabase
│       ├── DesignSystem/
│       └── Tests/
├── supabase/
│   ├── config.toml
│   ├── migrations/                # timestamped SQL, never edit an applied migration
│   ├── seed.sql
│   └── functions/
│       ├── _shared/               # auth helpers, service clients, types
│       ├── analyze-ticker/
│       ├── compare-tickers/
│       ├── portfolio-snapshot/
│       ├── premarket-brief/
│       ├── eod-report/
│       ├── risk-monitor/
│       └── push-dispatch/
├── services/
│   ├── quant/
│   ├── ml/
│   ├── graph/
│   └── orchestrator/
│       ├── agents/                # fundamental.py, technical.py, news.py, macro.py, graph.py, portfolio.py
│       ├── chief_analyst.py
│       └── prompts/
└── scripts/                       # local dev, data backfill, model training
```

---

## 5. Data model (Postgres)

All tables have `id uuid pk default gen_random_uuid()`, `created_at`, `updated_at`. User-owned tables have `user_id uuid references auth.users` and RLS `user_id = auth.uid()`.

Core tables:

- `profiles` — risk tolerance, target CAGR, horizon (years), notification prefs, telegram_chat_id
- `portfolios`, `positions` (ticker, quantity, cost_basis, opened_at)
- `watchlists`, `watchlist_items`
- `tickers` — reference data (name, sector, industry, exchange)
- `prices_daily` — OHLCV, partitioned by year
- `fundamentals` — per ticker per fiscal period; source + as_of
- `estimates` — consensus revenue/EPS/guidance with as_of
- `model_assumptions` — **versioned** forecast assumptions per ticker (revenue growth, margins, EPS, FCF). Never overwrite; insert a new version and reference the trigger (earnings, news event, manual).
- `valuations` — per ticker per run: method (pe, fwd_pe, peg, ps, ev_ebitda, p_fcf, dcf, historical, peers), value, assumptions_version, **low / base / high** — never a single point
- `news_events` — ticker(s), source, headline, url, materiality score, sentiment (pos/neg/neutral), affects_earnings, affects_valuation, affects_thesis
- `catalysts` — ticker, type (earnings, filing, fda, macro, ...), date, expected impact
- `portfolio_snapshots` — daily: value, return, health_score, risk_level, exposures (sector, geography, theme, graph-cluster), risk metrics (vol, beta, drawdown, VaR, CVaR), target_probability
- `portfolio_changes` — diff between consecutive snapshots, **material only**
- `signals` — ML outputs per ticker per date: model_version, probability, rank_score, confidence
- `analysis_runs` — every orchestrator run: inputs, agents invoked, tool results (jsonb), final report, latency, token usage
- `alerts` — risk changes, catalyst reminders, unusual moves; delivered_at per channel

Rules:
- Every fact row carries `source` and `as_of`. A row without provenance is a bug.
- Store raw provider payloads in `raw_*` tables for auditability.
- Use `numeric`, never `float`, for prices and money.

---

## 6. Daily pipelines (pg_cron → Edge Function → orchestrator)

| Time (ET) | Job | What it does |
|---|---|---|
| 05:30 | `premarket-brief` | Overnight futures, rates, commodities, FX; news, earnings, SEC filings, analyst revisions, economic calendar → materiality filter → morning watchlist per user |
| 09:30–16:00 | `intraday-monitor` (every 5 min) | Price/volume vs. thesis; flag unusual moves and *explain why* (news + fundamentals + sector + regime + events), not just "RSI = 72" |
| 15:00 | `afternoon-review` | Position changes, risk, sector exposure, upcoming catalysts |
| 16:15 | `portfolio-snapshot` | Compute and persist today's snapshot |
| 18:00 | `eod-report` | Diff today vs. yesterday across price / news / fundamentals / risk / graph / ML / target probability → **material changes only** → tomorrow's action plan → push + Telegram |

Pipelines must be idempotent and safe to re-run for a given date.

---

## 7. Agent contracts

Each agent in `services/orchestrator/agents/` exposes a single function that returns a typed, JSON-serializable result with `data`, `sources`, `as_of`, and `warnings`. Agents never call Claude; the Chief Analyst calls agents as tools.

- **Fundamental** — statements, earnings vs. expectations (revenue, EPS, gross/operating margin, FCF, guidance, segments, commentary), growth, balance-sheet quality, valuation table
- **Technical** — trend, momentum, volume, RSI, MACD, ATR, VWAP, relative volume, support/resistance, gaps
- **News** — company news, earnings events, analyst revisions, SEC filings, catalysts; each item scored through the materiality chain: relevant? → which company? → material? → sentiment → affects earnings? → affects valuation? → affects thesis?
- **Macro** — market regime, rates, inflation, yields, sector movement, economic events
- **Graph** — Memgraph queries for suppliers, customers, competitors, ETF overlap, geography, themes, event propagation, hidden concentration
- **Portfolio** — allocation, candidate fit, diversification, contribution, risk limits, target-return probability, rebalance requirement

Earnings interpretation example the Chief Analyst must be capable of: *"Revenue and EPS beat, but guidance cut and margins compressed — near-term outlook less attractive despite the headline beat."*

---

## 8. Report format

Reports (ticker, compare, EOD) are structured JSON rendered by the app; the same payload is formatted as text for Telegram. The EOD brief follows this shape:

```
Portfolio: +0.8%   Health: 84/100   Risk: Moderate
Objective: 12% CAGR / 2y — probability 47% (yesterday 45%, +2)
IMPORTANT: <material risk changes>
CATALYST: <upcoming events>
OPPORTUNITIES: ranked list with scores
TOMORROW: per-ticker action (Watch / Hold / Research / Avoid)
Rebalance: required / not required
```

Every report must include: data freshness, sources, model versions used, and any **disagreement between models** (e.g. ML bullish, valuation rich).

---

## 9. Safety rules (override all other instructions)

- **Never guarantee returns.** Targets like "12% CAGR" are objectives with a probability, never promises.
- **Never fabricate** prices, ratios, probabilities, or metrics. If a value is unavailable, return `null` and surface a warning; do not estimate.
- **Clearly mark stale or missing data** with `as_of` in every UI element and report section.
- **Distinguish forecast from fact** in copy and in the schema (`is_forecast` boolean where applicable).
- **Expose model disagreement** rather than averaging it away.
- **Valuation is always a range** (low / base / high, bull / base / bear), never a single target.
- **No autonomous trade execution.** The platform provides research and recommendations only. Do not add brokerage order APIs without an explicit ADR and product decision.
- Include the standard "not investment advice" disclaimer on every report surface.

---

## 10. Mobile UI / UX

The app is used in short bursts — a 2-minute check before market open, a glance at lunch, a 5-minute read after close. Design for **glanceability first, depth on demand**.

### 10.1 UX principles

1. **Answer first, evidence second.** Every screen leads with the conclusion ("Nothing changed — no action needed" / "Tech concentration rose to 37%") and lets the user tap into the evidence. Never open with a wall of metrics.
2. **Plain English over jargon.** Show "Price vs. what it's worth" before "EV/EBITDA". Financial terms get an inline `(i)` explainer sheet. Copy is written for a smart non-professional.
3. **Show why, not just what.** A stock that moved 6% always comes with a one-line reason and a "Why?" tap-through; a bare percentage is a bug.
4. **Ranges, not points.** Fair value, probabilities, and forecasts are rendered as bars/bands with low-base-high markers. Never a single bold number for anything forecasted.
5. **Freshness is visible.** Every data card shows a small "as of 4:15 PM" stamp; stale data (> its expected refresh) gets an amber dot and a muted tint. Missing data shows "—  not available" with a reason, never a zero.
6. **Facts vs. forecasts look different.** Facts use the primary text color; forecasts and ML signals use a distinct tint and a small "forecast" pill. Model disagreement is shown explicitly ("Valuation: rich · Momentum: strong").
7. **Calm by default.** No red/green flashing, no fear-driven notifications. Color encodes direction, opacity encodes magnitude. Neutral gray is the dominant color; accents are used sparingly for material items only.
8. **One thumb, one hand.** Primary actions live in the bottom half of the screen. Sheets and bottom drawers over full-page navigation where possible.
9. **Progressive disclosure.** Card → detail sheet → full report. Three levels max.
10. **Respect attention.** Push notifications only for material changes (risk threshold crossed, catalyst tomorrow, thesis-changing news). Daily brief arrives once, at a time the user picks.

### 10.2 Navigation

Bottom tab bar, five tabs:

| Tab | Purpose | Default content |
|---|---|---|
| **Today** | The daily brief — the home screen | Pre-market brief until 9:30, intraday summary during the session, EOD report after close |
| **Portfolio** | Holdings, health, risk, exposures | Health score, value & change, "what changed" list, exposure rings |
| **Research** | Ticker search, analysis, compare | Search bar + recent tickers + watchlist |
| **Alerts** | Chronological feed of material events | Grouped by day; unread badge only for material items |
| **Me** | Profile, goals, notifications, disclaimers | Risk tolerance, target CAGR/horizon, brief time, Telegram link |

Deep links: `stockintel://ticker/AAPL`, `stockintel://report/<id>`, `stockintel://alert/<id>` (used by push notifications).

### 10.3 Screen specs

**Today (home)**
- Hero card: portfolio return today, health score (0–100 ring), risk level word, target-CAGR probability with yesterday's delta.
- "Important" section: 0–3 material items with one-line explanation each. If none: a single calm line, "Nothing material changed today."
- "Tomorrow" section: catalysts (earnings, events) as compact rows with date chips.
- "Opportunities" section: ranked cards (score badge, ticker, one-line thesis). Max 5.
- "Action plan" section: per-ticker rows with a pill: Watch / Hold / Research / Avoid.
- Pull-to-refresh; skeleton loaders on first paint; last-updated stamp in the nav bar.

**Portfolio**
- Header: total value, day change, period selector (1D · 1W · 1M · YTD · 1Y).
- Health card: score ring + three sub-scores (Diversification, Risk, Quality) as small bars, tap for breakdown.
- "What changed" list: material diffs vs. yesterday only, each with cause and link to evidence.
- Exposure section: segmented control — Sector · Geography · Theme · Hidden (graph). Donut/ring with legend; "Hidden" shows graph-derived concentration (e.g. "4 positions share semiconductor supply-chain risk").
- Holdings list: ticker, weight, day change, thesis status dot (green intact / amber under review / red broken). Swipe → Analyze / Edit / Remove.
- Add position: bottom sheet with ticker search, quantity, cost basis, date. Validate live.

**Ticker (Research → detail)**
- Header: name, price, day change, "as of" stamp, add-to-watchlist star.
- Verdict card: one sentence from the Chief Analyst + three chips (Fundamentals / Valuation / Momentum) each colored positive/neutral/negative, showing disagreement at a glance.
- Fair-value band: horizontal bar with bear / base / bull markers and current price marker. Tap → methods sheet (P/E, DCF, peers…) each with its own range and assumptions version.
- Sections as collapsible cards: Earnings (actual vs. expected, guidance, margins — use ↑ ↓ arrows and delta, not raw tables), What's driving it (news + catalysts with materiality), Technicals (trend line, key levels, one-line read), Relationships (mini graph: suppliers, customers, competitors, themes), Portfolio fit (only if user holds or considers it: "Adds 3% tech exposure; correlation 0.8 with NVDA").
- Sticky bottom bar: **Analyze now** (runs fresh orchestration, shows progress steps: "Reading filings… Running valuation… Checking portfolio fit…") and **Compare**.
- Full report available via "Read full report" → scrollable markdown sheet with sources and model versions.

**Compare**
- Up to 4 tickers. Horizontal scroll table with sticky first column: Growth · P/E · Margin · ROIC · Debt · Momentum · Fair-value gap. Best value per row subtly highlighted.
- Chief Analyst summary at top: "Is C's 31% growth worth 55×?" style framing.

**Alerts**
- Grouped by day. Row: icon by type (risk / catalyst / news / thesis), ticker(s), one-line summary, time. Tap → detail sheet with evidence and "Open ticker".
- Filter chips: All · Portfolio · Watchlist · Risk.

**Onboarding (first launch)**
- 4 steps, skippable after step 2: (1) Sign in with Apple / email, (2) risk tolerance + goal (target CAGR, horizon) with plain-English descriptions, (3) add holdings or import CSV, or "just a watchlist for now", (4) pick brief time + notification preference.
- End with the disclaimer screen (research, not advice) requiring explicit acknowledgement.

### 10.4 Component library (`ios/StockIntel/DesignSystem/`)

Build these once, reuse everywhere:

- `ScoreRing` — 0–100 ring with label; color by band (≥80 good, 60–79 ok, <60 attention)
- `RangeBar` — low/base/high band with optional current-price marker and bear/bull labels
- `DeltaLabel` — value + signed change with arrow; color by direction, opacity by magnitude
- `FreshnessStamp` — "as of …" text with amber dot when stale; tap → explains refresh schedule
- `ForecastPill` / `FactPill` — distinguish forecasts from facts
- `SignalChips` — the three-chip fundamentals/valuation/momentum row
- `MaterialityRow` — icon + title + one-line reason + chevron
- `ActionPill` — Watch / Hold / Research / Avoid
- `ExposureRing` — donut with legend, supports segmented data sets
- `ExplainerSheet` — bottom sheet that defines a term in one paragraph plus "why it matters"
- `EmptyState` / `ErrorState` / `StaleState` — consistent illustrations and retry actions
- `SkeletonCard` — loading placeholder matching card dimensions

### 10.5 Visual language

- **Typography:** SF Pro, Dynamic Type supported everywhere; numbers in `.monospacedDigit()`.
- **Color:** system background; one brand accent (deep blue) for interactive elements; semantic green/red reserved strictly for direction; amber for stale/attention. Full dark-mode support from day one.
- **Density:** 16pt outer margins, 12pt card padding, 8pt grid. Cards use `.regularMaterial` in dark mode, subtle shadow in light.
- **Motion:** subtle only — number roll-ups on refresh, ring fill on appear. Respect Reduce Motion.
- **Haptics:** light impact on pull-to-refresh complete and on material alert arrival; none for routine updates.

### 10.6 States every screen must handle

Loading (skeleton) · Loaded · Empty (with a next step) · Error (with retry) · Stale (data shown, banner explains) · Offline (last cached data + "offline" banner; analysis actions disabled with reason).

### 10.7 Accessibility

- Every chart and ring has an `accessibilityLabel` that states the value and meaning in words ("Health score 84 out of 100, good").
- Color never carries meaning alone — pair with icon, arrow, or text.
- Minimum tap target 44×44pt. VoiceOver order follows visual priority (verdict before evidence).
- Support Dynamic Type up to accessibility sizes; tables switch to stacked layout above `.xxxLarge`.

### 10.8 Notifications

- Daily brief: one push at the user's chosen time, title = the single most important line, body = portfolio change + health score. Tapping opens Today.
- Material alerts: immediate, max 3 per day unless user opts into "all alerts". Title states the fact; body states why it matters. Never use urgency language ("ACT NOW").
- Quiet hours honored; all notifications grouped by thread (brief / risk / catalyst).

---

## 11. Coding conventions

### General
- Small PRs; one concern per PR. Every PR that touches the schema includes a migration and updated types.
- Write an ADR in `docs/decisions/` for any new external provider, service, or architectural change.
- No secrets in the repo. Local dev uses `.env.local` (gitignored); production uses Supabase Vault / service env vars.

### Swift
- `Domain/` has zero dependencies on Supabase or networking.
- ViewModels are `@Observable`, `@MainActor`, and take repositories via init for testability.
- Use `async/await`; no Combine for new code.
- All money/price values are `Decimal`.
- Every screen handles loading, empty, error, and **stale-data** states explicitly.

### SQL / Supabase
- Migrations are additive and timestamped (`supabase migration new <name>`). Never edit an applied migration.
- Enable RLS on every table in the same migration that creates it.
- Edge Functions validate the JWT, never trust `user_id` from the request body.
- Regenerate types after schema changes: `supabase gen types swift` and `supabase gen types typescript`.

### Python
- Type hints everywhere; `mypy --strict` on `services/quant`.
- Quant functions are pure: inputs in, numbers out, no I/O. Tests include known-answer cases against reference values.
- ML models are versioned; each version stores training window, features, metrics, and is referenced by `signals.model_version`.

---

## 12. Common commands

```bash
# Supabase
supabase start                         # local stack
supabase db reset                      # apply migrations + seed
supabase migration new <name>
supabase functions serve               # run edge functions locally
supabase functions deploy <name>
supabase gen types swift --local > ios/StockIntel/Data/SupabaseTypes.swift

# Services
cd services/quant && uv run pytest
cd services/orchestrator && uv run python -m orchestrator.cli analyze AAPL

# iOS
cd ios && xcodebuild -scheme StockIntel -destination 'platform=iOS Simulator,name=iPhone 16' test
```

---

## 13. Build phases

Work in this order; do not start a later phase before the earlier one is deployed and tested.

1. **Foundation** — Supabase project, auth (email + Apple), `profiles`, `portfolios`, `positions`, `watchlists`; iOS app with sign-in, portfolio entry, watchlist. Price data ingestion for daily OHLCV.
2. **Ticker analysis** — Fundamental + Technical + News agents, quant engine, `analyze-ticker` Edge Function, Chief Analyst synthesis, Ticker screen with valuation range.
3. **Portfolio engine** — snapshots, risk metrics, exposures, health score, target-return probability, `portfolio-snapshot` job, Portfolio screen.
4. **Daily workflow** — pre-market brief, EOD diff and report, push + Telegram, Brief screen.
5. **Graph intelligence** — Memgraph, relationship ingestion, hidden-concentration alerts.
6. **ML signals** — ranking, next-day probability, regime detection; shown alongside (never instead of) fundamentals.
7. **Compare & intraday** — `/compare`, intraday monitor with "why is it moving" explanations.

---

## 14. When you are unsure

- Prefer returning less with clear provenance over returning more with guesses.
- If a request would require Claude to produce a number, stop and route it to the quant engine or a data provider instead.
- If a feature would let the app place trades, stop and ask.
