-- Analysis tables: news, catalysts, signals, snapshots, changes, runs

-- ─── news_events ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_events (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tickers          text[] NOT NULL DEFAULT '{}',
  source           text NOT NULL,
  headline         text NOT NULL,
  url              text,
  materiality_score numeric CHECK (materiality_score BETWEEN 0 AND 1),
  sentiment        text CHECK (sentiment IN ('positive','negative','neutral')),
  affects_earnings bool NOT NULL DEFAULT false,
  affects_valuation bool NOT NULL DEFAULT false,
  affects_thesis   bool NOT NULL DEFAULT false,
  as_of            timestamptz NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_news_events_tickers ON news_events USING GIN (tickers);
CREATE INDEX IF NOT EXISTS idx_news_events_as_of ON news_events (as_of DESC);

-- ─── catalysts ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS catalysts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker          text REFERENCES tickers(symbol),
  type            text NOT NULL CHECK (type IN ('earnings','filing','fda','macro','dividend','guidance','other')),
  description     text NOT NULL,
  date            date NOT NULL,
  expected_impact text CHECK (expected_impact IN ('positive','negative','neutral')),
  source          text NOT NULL,
  as_of           timestamptz NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_catalysts_ticker_date ON catalysts (ticker, date);

-- ─── signals (ML outputs) ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signals (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker        text NOT NULL REFERENCES tickers(symbol),
  date          date NOT NULL,
  model_version text NOT NULL,
  probability   numeric CHECK (probability BETWEEN 0 AND 1),
  rank_score    numeric CHECK (rank_score BETWEEN 0 AND 100),
  confidence    numeric CHECK (confidence BETWEEN 0 AND 1),
  is_forecast   bool NOT NULL DEFAULT true,
  source        text NOT NULL DEFAULT 'ml_engine',
  as_of         timestamptz NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ticker, date, model_version)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker_date ON signals (ticker, date DESC);

-- ─── portfolio_snapshots ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id            uuid NOT NULL REFERENCES portfolios ON DELETE CASCADE,
  date                    date NOT NULL,
  total_value             numeric NOT NULL,
  day_return              numeric,
  period_return           numeric,
  health_score            numeric CHECK (health_score BETWEEN 0 AND 100),
  diversification_score   numeric,
  risk_score              numeric,
  quality_score           numeric,
  risk_level              text CHECK (risk_level IN ('low','moderate','elevated','high')),
  exposures               jsonb NOT NULL DEFAULT '{}',
  risk_metrics            jsonb NOT NULL DEFAULT '{}',
  target_probability      numeric CHECK (target_probability BETWEEN 0 AND 1),
  target_probability_delta numeric,
  created_at              timestamptz NOT NULL DEFAULT now(),
  UNIQUE (portfolio_id, date)
);
ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY snapshots_owner ON portfolio_snapshots
  USING (portfolio_id IN (SELECT id FROM portfolios WHERE user_id = auth.uid()));
CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio_date ON portfolio_snapshots (portfolio_id, date DESC);

-- ─── portfolio_changes (material diffs only) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolio_changes (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id uuid NOT NULL REFERENCES portfolios ON DELETE CASCADE,
  date         date NOT NULL,
  ticker       text,
  change_type  text NOT NULL CHECK (change_type IN ('price','news','fundamental','risk','graph','ml','target_probability')),
  summary      text NOT NULL,
  detail       text,
  evidence_url text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE portfolio_changes ENABLE ROW LEVEL SECURITY;
CREATE POLICY changes_owner ON portfolio_changes
  USING (portfolio_id IN (SELECT id FROM portfolios WHERE user_id = auth.uid()));
CREATE INDEX IF NOT EXISTS idx_changes_portfolio_date ON portfolio_changes (portfolio_id, date DESC);

-- ─── analysis_runs (orchestrator audit log) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis_runs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        uuid REFERENCES auth.users ON DELETE SET NULL,
  ticker         text,
  tickers        text[],
  run_type       text NOT NULL CHECK (run_type IN ('analyze','compare','brief','contribution')),
  agents_invoked text[],
  tool_results   jsonb,
  final_report   text,
  token_usage    int,
  latency_ms     int,
  model_version  text,
  warnings       text[],
  created_at     timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY runs_owner ON analysis_runs USING (user_id = auth.uid());
CREATE INDEX IF NOT EXISTS idx_runs_user ON analysis_runs (user_id, created_at DESC);
