// ─── Auth & Profile ─────────────────────────────────────────────────────────

export type RiskTolerance = 'conservative' | 'moderate' | 'aggressive';

export interface Profile {
  id: string;
  user_id: string;
  display_name: string | null;
  risk_tolerance: RiskTolerance;
  target_cagr: number;       // e.g. 0.12 = 12%
  horizon_years: number;
  brief_time: string;        // HH:MM local time, e.g. "06:00"
  telegram_chat_id: string | null;
  notifications_enabled: boolean;
  disclaimer_acknowledged: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Portfolio & Positions ───────────────────────────────────────────────────

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: string;
  portfolio_id: string;
  ticker: string;
  quantity: number;
  cost_basis: string;        // numeric as string to avoid float drift
  opened_at: string;
  notes: string | null;
}

export interface Ticker {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  exchange: string;
}

// ─── Price ───────────────────────────────────────────────────────────────────

export interface PriceDaily {
  ticker: string;
  date: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
  adj_close: string;
}

export interface QuoteSnapshot {
  ticker: string;
  price: string;
  change: string;
  change_pct: number;
  volume: number;
  as_of: string;
}

// ─── Watchlist ────────────────────────────────────────────────────────────────

export interface Watchlist {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
}

export interface WatchlistItem {
  id: string;
  watchlist_id: string;
  ticker: string;
  added_at: string;
}

// ─── Portfolio Snapshot (daily computed) ─────────────────────────────────────

export type RiskLevel = 'low' | 'moderate' | 'elevated' | 'high';

export interface ExposureBreakdown {
  sector: Record<string, number>;
  geography: Record<string, number>;
  theme: Record<string, number>;
  hidden: HiddenConcentration[];
}

export interface HiddenConcentration {
  dependency: string;
  tickers: string[];
  description: string;
}

export interface RiskMetrics {
  volatility_30d: number | null;
  beta: number | null;
  max_drawdown: number | null;
  var_95: number | null;
  cvar_95: number | null;
  sharpe: number | null;
  sortino: number | null;
  as_of: string;
}

export interface PortfolioSnapshot {
  id: string;
  portfolio_id: string;
  date: string;
  total_value: string;
  day_return: number;
  period_return: number;
  health_score: number;        // 0–100
  diversification_score: number;
  risk_score: number;
  quality_score: number;
  risk_level: RiskLevel;
  exposures: ExposureBreakdown;
  risk_metrics: RiskMetrics;
  target_probability: number;  // probability of hitting CAGR target
  target_probability_delta: number;
  created_at: string;
}

export interface PortfolioChange {
  id: string;
  portfolio_id: string;
  date: string;
  ticker: string | null;
  change_type: 'price' | 'news' | 'fundamental' | 'risk' | 'graph' | 'ml' | 'target_probability';
  summary: string;
  detail: string | null;
  evidence_url: string | null;
}

// ─── Fundamentals & Valuation ────────────────────────────────────────────────

export interface Fundamental {
  id: string;
  ticker: string;
  fiscal_period: string;        // e.g. "2024-Q4", "2024-FY"
  revenue: string | null;
  revenue_growth: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  eps: string | null;
  eps_expected: string | null;
  fcf: string | null;
  guidance_revenue: string | null;
  guidance_eps: string | null;
  source: string;
  as_of: string;
}

export type ValuationMethod =
  | 'pe'
  | 'fwd_pe'
  | 'peg'
  | 'ps'
  | 'ev_ebitda'
  | 'p_fcf'
  | 'dcf'
  | 'historical'
  | 'peers';

export interface ValuationRange {
  method: ValuationMethod;
  low: string;
  base: string;
  high: string;
  bear: string;
  bull: string;
  assumptions_version: string;
  source: string;
  as_of: string;
  is_forecast: true;
}

// ─── News & Catalysts ─────────────────────────────────────────────────────────

export type Sentiment = 'positive' | 'negative' | 'neutral';

export interface NewsEvent {
  id: string;
  tickers: string[];
  source: string;
  headline: string;
  url: string | null;
  materiality_score: number;   // 0–1
  sentiment: Sentiment;
  affects_earnings: boolean;
  affects_valuation: boolean;
  affects_thesis: boolean;
  as_of: string;
}

export type CatalystType = 'earnings' | 'filing' | 'fda' | 'macro' | 'dividend' | 'guidance' | 'other';

export interface Catalyst {
  id: string;
  ticker: string;
  type: CatalystType;
  description: string;
  date: string;
  expected_impact: Sentiment;
}

// ─── ML Signals ───────────────────────────────────────────────────────────────

export interface Signal {
  ticker: string;
  date: string;
  model_version: string;
  probability: number;         // next-day up probability
  rank_score: number;          // 0–100
  confidence: number;          // 0–1
  is_forecast: true;
}

// ─── Alerts ──────────────────────────────────────────────────────────────────

export type AlertType = 'risk' | 'catalyst' | 'news' | 'thesis' | 'price';

export interface Alert {
  id: string;
  user_id: string;
  type: AlertType;
  tickers: string[];
  title: string;
  body: string;
  evidence: string | null;
  delivered_at: string | null;
  read_at: string | null;
  created_at: string;
}

// ─── Analysis (orchestrator output) ──────────────────────────────────────────

export type ThesisStatus = 'intact' | 'under_review' | 'broken';
export type ActionRecommendation = 'Watch' | 'Hold' | 'Research' | 'Avoid';

export type SignalDirection = 'positive' | 'neutral' | 'negative';

export interface TickerSignals {
  fundamentals: SignalDirection;
  valuation: SignalDirection;
  momentum: SignalDirection;
}

export interface TickerAnalysis {
  ticker: string;
  run_id: string;
  verdict: string;              // one-sentence Chief Analyst summary
  signals: TickerSignals;
  valuation_range: ValuationRange | null;
  fair_value_current_price: string | null;
  earnings: Fundamental | null;
  what_is_driving: NewsEvent[];
  catalysts: Catalyst[];
  ml_signal: Signal | null;
  portfolio_fit: string | null;
  action: ActionRecommendation;
  full_report_markdown: string;
  model_disagreements: string[];
  data_freshness: string;
  as_of: string;
  is_forecast: true;
}

export interface CompareRow {
  ticker: string;
  revenue_growth: number | null;
  pe: string | null;
  fwd_pe: string | null;
  gross_margin: number | null;
  roic: number | null;
  debt_to_equity: number | null;
  momentum_score: number | null;
  fair_value_gap_pct: number | null;
}

export interface CompareAnalysis {
  tickers: string[];
  chief_analyst_summary: string;
  rows: CompareRow[];
  as_of: string;
  is_forecast: true;
}

// ─── Daily Brief ──────────────────────────────────────────────────────────────

export interface OpportunityCard {
  ticker: string;
  score: number;              // 0–100
  one_line_thesis: string;
  action: ActionRecommendation;
}

export interface DailyBrief {
  date: string;
  portfolio_return: number;
  health_score: number;
  risk_level: RiskLevel;
  target_probability: number;
  target_probability_delta: number;
  important: PortfolioChange[];
  catalysts: Catalyst[];
  opportunities: OpportunityCard[];
  action_plan: Array<{ ticker: string; action: ActionRecommendation; reason: string }>;
  rebalance_required: boolean;
  as_of: string;
}

// ─── UI state helpers ─────────────────────────────────────────────────────────

export type LoadState = 'idle' | 'loading' | 'success' | 'error' | 'stale';

export interface AsyncState<T> {
  data: T | null;
  state: LoadState;
  error: string | null;
  as_of: string | null;
}

// ─── API response envelope ────────────────────────────────────────────────────

export interface ApiOk<T> {
  data: T;
  sources: string[];
  as_of: string;
  warnings: string[];
}

export interface ApiError {
  error: string;
  detail: string | null;
}
