# Daily Workflow of a Stock Analyst

A stock analyst's job is much broader than looking at a chart and
deciding "buy or sell." A professional analyst spends much of the day
answering:

> **What changed? Why did it change? Does it change our investment
> thesis? What is the risk/reward now?**

For the AI stock intelligence platform, this workflow can be translated
into specialized AI agents, deterministic quantitative engines, and
relationship intelligence.

------------------------------------------------------------------------

## 1. Typical Daily Workflow

``` text
5:30–7:00 AM
PRE-MARKET RESEARCH
        ↓
Overnight markets
Futures / rates / commodities
Company news
Earnings
SEC filings
Analyst upgrades/downgrades
Economic calendar
        ↓
Identify important changes
        ↓
7:00–8:30 AM
PORTFOLIO REVIEW
        ↓
Which holdings are affected?
Which stocks have catalysts?
Which risks changed?
        ↓
Create morning watchlist
        ↓
────────────────────────────
9:30 AM — MARKET OPENS
────────────────────────────
        ↓
Monitor price + volume
        ↓
Compare movement with thesis
        ↓
Investigate unusual moves
        ↓
Update opportunities / risks
        ↓
────────────────────────────
DURING THE DAY
────────────────────────────
        ↓
Company research
Financial statement analysis
Industry research
Valuation
Competitor analysis
Management commentary
News / SEC filings
Model updates
        ↓
────────────────────────────
3:00–4:00 PM
PORTFOLIO REVIEW
────────────────────────────
        ↓
Position changes
Risk
Sector exposure
Upcoming catalysts
        ↓
────────────────────────────
AFTER MARKET CLOSE
────────────────────────────
        ↓
Earnings
Daily performance
Model updates
Tomorrow's catalysts
        ↓
Prepare next-day strategy
```

------------------------------------------------------------------------

## 2. Morning: What Happened Overnight?

An analyst starts by examining overnight information:

-   Index futures
-   International markets
-   Treasury yields
-   Commodities
-   Currencies
-   Economic developments
-   Major company news
-   Earnings releases
-   SEC filings
-   Analyst upgrades and downgrades

The analyst then filters information for material impact.

``` text
News
 ↓
Is it relevant?
 ↓
Which company?
 ↓
Is it material?
 ↓
Positive / Negative / Neutral?
 ↓
Does it change earnings expectations?
 ↓
Does it change valuation?
 ↓
Does it change the investment thesis?
```

In the proposed software, this maps naturally to a **News Agent + Claude
orchestration workflow**.

------------------------------------------------------------------------

## 3. Earnings Analysis

Analysts look beyond whether a company simply beat or missed EPS.

They examine:

-   Revenue
-   EPS
-   Gross margin
-   Operating margin
-   Free cash flow
-   Guidance
-   Business segments
-   Management commentary
-   Analyst expectations

Example:

``` text
Company reports earnings

Revenue
Actual        $10.5B
Expected      $10.1B
              ↑ Beat

EPS
Actual        $2.15
Expected      $2.03
              ↑ Beat

Guidance
Previous      $42B
New           $39B
              ↓ Negative

Margins
Previous      28%
Current       25%
              ↓ Negative
```

The correct conclusion may therefore be more nuanced than the headline:

> Earnings exceeded expectations, but weaker forward guidance and
> declining margins reduce the attractiveness of the near-term outlook.

Claude can synthesize this interpretation after deterministic data
services provide validated numbers.

------------------------------------------------------------------------

## 4. Maintain Financial Models

Fundamental analysts maintain financial models for companies they cover.

Typical forecasts include:

``` text
                  2026     2027     2028

Revenue           $50B     $57B     $64B
Growth             12%      14%      12%

Gross Margin       62%      63%      64%

Operating Income  $14B     $17B     $20B

EPS               $5.20    $6.10    $7.05

Free Cash Flow    $11B     $14B     $17B
```

When new information arrives:

``` text
New earnings
      ↓
Update revenue assumptions
      ↓
Update margins
      ↓
Update EPS
      ↓
Update cash flow
      ↓
Update valuation
      ↓
Update investment thesis
```

The AI platform should perform the same process programmatically and
maintain historical versions of assumptions.

------------------------------------------------------------------------

## 5. Valuation Analysis

Analysts do not only ask:

> Will this company grow?

They also ask:

> How much am I paying for that growth?

The platform should support multiple valuation approaches:

-   P/E
-   Forward P/E
-   PEG
-   Price/Sales
-   EV/EBITDA
-   Price/FCF
-   Discounted Cash Flow (DCF)
-   Historical valuation ranges
-   Peer-company comparison

Example:

``` text
Current Price          $180

DCF Value              $205
Peer Valuation         $195
Historical Multiple    $188

Fair Value Range
$190 ───────────── $205

Bull Case              $225
Base Case              $198
Bear Case              $145
```

Valuation should be represented as a range based on assumptions rather
than as a single guaranteed price target.

------------------------------------------------------------------------

## 6. Monitor Price Action

Analysts monitor:

-   Price changes
-   Volume
-   Relative performance
-   Volatility
-   Support and resistance
-   Sector movement
-   Unusual trading activity

Short-term analysis can additionally use:

-   RSI
-   MACD
-   Moving averages
-   ATR
-   VWAP
-   Relative volume
-   Momentum
-   Gap analysis

However, the important question is not simply:

> RSI = 72

The platform should determine:

> **Why is the stock moving?**

Price signals should therefore be combined with news, fundamentals,
sector behavior, market regime, and event information.

------------------------------------------------------------------------

## 7. Peer and Competitor Analysis

Analysts constantly compare companies.

Example:

``` text
             Growth    P/E    Margin    ROIC    Debt

Company A      20%     28x      31%      27%     Low
Company B      14%     19x      25%      19%     Low
Company C      31%     55x      35%      32%     Med
```

The key analytical question becomes:

> Is Company C's superior growth worth paying 55× earnings?

This maps directly to commands such as:

``` text
/compare AAPL MSFT NVDA
```

------------------------------------------------------------------------

## 8. Relationship Intelligence with Memgraph

Traditional analysis may evaluate a company independently:

``` text
NVDA
Revenue
EPS
Margins
Valuation
Momentum
```

A graph-based approach can analyze relationships:

``` text
NVDA
 │
 ├── Supplier → TSMC
 │                 │
 │                 └── Taiwan geopolitical exposure
 │
 ├── Customer → Cloud providers
 │
 ├── Competitor → AMD
 │
 ├── Industry → Semiconductors
 │
 └── Theme → AI Infrastructure
```

Memgraph can model relationships between:

-   Companies
-   Suppliers
-   Customers
-   Competitors
-   Industries
-   Sectors
-   ETFs
-   Countries
-   Commodities
-   Technologies
-   Risk factors
-   News events
-   Macro events

This enables hidden-risk and event-propagation analysis.

------------------------------------------------------------------------

## 9. Portfolio Analysts Think Differently

Once a portfolio is involved, the question changes from:

> Is NVDA a good stock?

to:

> **Is NVDA a good addition to this particular portfolio?**

Example portfolio:

``` text
QQQ        25%
MSFT       15%
NVDA       10%
GOOGL      10%
AMZN       10%
VTI        20%
Cash       10%
```

A stock-ranking model may identify another technology stock as
attractive.

The portfolio engine may nevertheless reject or cap the position because
technology exposure and correlated risks are already high.

The decision should combine:

``` text
Stock attractiveness
        +
Portfolio contribution
        +
Correlation
        +
Sector exposure
        +
Graph exposure
        +
Risk tolerance
        ↓
Portfolio Decision
```

------------------------------------------------------------------------

## 10. Continuous Portfolio Risk Monitoring

Portfolio analysts and risk teams monitor:

-   Volatility
-   Beta
-   Drawdown
-   VaR
-   CVaR
-   Correlation
-   Sector concentration
-   Position concentration
-   Liquidity
-   Factor exposure
-   Event risk
-   Geographic exposure
-   Graph-based concentration

The platform should identify meaningful changes rather than merely
displaying metrics.

Example:

``` text
⚠️ RISK CHANGE DETECTED

Technology represents 37% of portfolio exposure.

Memgraph additionally identifies common semiconductor
and AI dependencies across four positions.

Effective thematic concentration may therefore be
greater than sector allocation alone indicates.
```

------------------------------------------------------------------------

## 11. End-of-Day Analysis

One of the most important workflows is determining what changed during
the trading day.

``` text
TODAY'S PORTFOLIO
       ↓
Compare against
       ↓
YESTERDAY'S PORTFOLIO
       ↓
────────────────────
Price changes
News changes
Fundamental changes
Risk changes
Graph changes
ML signal changes
Target probability changes
────────────────────
       ↓
Material changes only
       ↓
Tomorrow's action plan
```

Example Telegram report:

``` text
📊 DAILY PORTFOLIO BRIEF

Portfolio: +0.8%

Health Score: 84/100
Risk: Moderate

🎯 2-Year Objective

Target CAGR: 12%
Estimated probability: 47%
Yesterday: 45%
Change: +2%

⚠️ IMPORTANT

Technology concentration increased.

📰 CATALYST

One portfolio company reports earnings tomorrow.

📈 OPPORTUNITIES

AAPL       81/100
MSFT       79/100
XYZ        76/100

🔎 TOMORROW

AAPL — Watch for Long
MSFT — Hold
XYZ — Research
ABC — Avoid

No portfolio rebalance required.
```

------------------------------------------------------------------------

## 12. Translating the Analyst Workflow into the AI Platform

The software should operate more like a digital investment research team
than a single stock-picking chatbot.

``` text
                   CLAUDE
              CHIEF ANALYST
                    │
       ┌────────────┼─────────────┐
       │            │             │
       ▼            ▼             ▼
   Company       Market        Portfolio
   Analyst       Analyst        Analyst
       │            │             │
 Fundamental     Macro          Allocation
 Valuation       Sector         Performance
 Earnings        Regime         Optimization
       │            │             │
       └────────────┼─────────────┘
                    │
              Risk Analyst
                    │
                 Memgraph
                    │
             Relationship
              Intelligence
                    │
                    ▼
              Quant Engine
                    │
         ML + Risk + Forecast
                    │
                    ▼
             CHIEF ANALYST
                CLAUDE
                    │
                    ▼
          Recommendation
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
      Telegram             App/Web
```

------------------------------------------------------------------------

## 13. Recommended Agent Responsibilities

### Chief Analyst / Claude

-   Orchestrate analysis
-   Determine which specialized tools or agents are needed
-   Synthesize evidence
-   Explain conflicting signals
-   Produce the final research report

### Fundamental Agent

-   Financial statements
-   Earnings
-   Growth
-   Margins
-   Cash flow
-   Balance-sheet quality
-   Valuation

### Technical Agent

-   Trend
-   Momentum
-   Volume
-   RSI
-   MACD
-   ATR
-   VWAP
-   Support/resistance

### News Agent

-   Company news
-   Earnings events
-   Analyst revisions
-   SEC filings
-   Material catalysts

### Market/Macro Agent

-   Market regime
-   Interest rates
-   Inflation
-   Treasury yields
-   Sector movement
-   Economic events

### Graph Intelligence Agent

Use Memgraph for:

-   Supplier relationships
-   Customer relationships
-   Competitors
-   ETF overlap
-   Geographic exposure
-   Sector relationships
-   Theme exposure
-   Event propagation
-   Hidden portfolio concentration

### Quant Engine

Use deterministic Python calculations for:

-   Returns
-   Volatility
-   Correlation
-   Beta
-   Sharpe
-   Sortino
-   VaR
-   CVaR
-   Technical indicators
-   Monte Carlo simulation
-   Portfolio optimization

### ML Engine

Support:

-   Next-day probability models
-   Stock ranking
-   Volatility prediction
-   Market regime detection
-   Risk prediction

### Portfolio Agent

Evaluate:

-   Current allocation
-   Candidate investments
-   Diversification
-   Portfolio contribution
-   Risk limits
-   Target-return probability
-   Rebalancing requirements

------------------------------------------------------------------------

## 14. Core Design Principle

Do **not** build a system where Claude simply picks stocks.

Build a **digital equity research and portfolio-management team**.

Claude should act as the chief analyst.

Specialized agents and services gather evidence.

Deterministic quantitative engines calculate financial metrics.

Memgraph identifies relationships and hidden concentration.

ML models provide probabilistic signals.

The portfolio engine determines whether an investment fits the user's
overall portfolio.

Claude then synthesizes the validated information into an understandable
recommendation.

The architecture should support both:

1.  **Daily portfolio-management workflow**
2.  **Next-trading-day ticker analysis**, such as `/analyze AAPL`

The ultimate workflow is:

``` text
MARKET DATA
     +
FUNDAMENTALS
     +
NEWS / SEC
     +
TECHNICALS
     +
MACRO
     +
MEMGRAPH
     ↓
QUANT + ML ENGINES
     ↓
PORTFOLIO/RISK ENGINE
     ↓
CLAUDE CHIEF ANALYST
     ↓
EVIDENCE-BASED RESEARCH
     ↓
TELEGRAM / MOBILE / WEB
```

------------------------------------------------------------------------

## 15. Safety and Decision-Support Principle

The platform should:

-   Never guarantee investment returns.
-   Never fabricate prices, ratios, probabilities, or financial metrics.
-   Clearly identify stale or missing data.
-   Expose disagreement between models.
-   Distinguish forecasts from facts.
-   Treat return targets such as 12% as objectives rather than promises.
-   Initially provide research and recommendations rather than
    autonomous trade execution.
