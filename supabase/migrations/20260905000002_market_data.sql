-- Market data: prices, fundamentals, estimates, model assumptions, valuations

-- ─── prices_daily ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prices_daily (
  ticker    text NOT NULL REFERENCES tickers(symbol),
  date      date NOT NULL,
  open      numeric,
  high      numeric,
  low       numeric,
  close     numeric NOT NULL,
  adj_close numeric,
  volume    bigint,
  source    text NOT NULL,
  as_of     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, date)
) PARTITION BY RANGE (date);

CREATE TABLE IF NOT EXISTS prices_daily_2025
  PARTITION OF prices_daily FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS prices_daily_2026
  PARTITION OF prices_daily FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE IF NOT EXISTS prices_daily_2027
  PARTITION OF prices_daily FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

CREATE INDEX IF NOT EXISTS idx_prices_daily_ticker_date ON prices_daily (ticker, date DESC);

-- ─── fundamentals ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fundamentals (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker            text NOT NULL REFERENCES tickers(symbol),
  fiscal_period     text NOT NULL,
  revenue           numeric,
  revenue_growth    numeric,
  gross_margin      numeric,
  operating_margin  numeric,
  net_margin        numeric,
  eps               numeric,
  eps_expected      numeric,
  fcf               numeric,
  guidance_revenue  numeric,
  guidance_eps      numeric,
  source            text NOT NULL,
  as_of             timestamptz NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ticker, fiscal_period, source)
);
CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker ON fundamentals (ticker, fiscal_period DESC);

-- ─── estimates (consensus) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS estimates (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker           text NOT NULL REFERENCES tickers(symbol),
  fiscal_period    text NOT NULL,
  consensus_revenue numeric,
  consensus_eps     numeric,
  num_analysts      int,
  as_of             timestamptz NOT NULL,
  source            text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ticker, fiscal_period, source)
);
CREATE INDEX IF NOT EXISTS idx_estimates_ticker ON estimates (ticker, fiscal_period DESC);

-- ─── model_assumptions (versioned, never overwrite) ───────────────────────────
CREATE TABLE IF NOT EXISTS model_assumptions (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker           text NOT NULL,
  fiscal_year      text NOT NULL,
  revenue_growth   numeric,
  gross_margin     numeric,
  operating_margin numeric,
  eps              numeric,
  fcf              numeric,
  version          text NOT NULL,
  trigger_event    text CHECK (trigger_event IN ('earnings','news','manual')),
  source           text NOT NULL,
  as_of            timestamptz NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ticker, fiscal_year, version)
);
CREATE INDEX IF NOT EXISTS idx_model_assumptions_ticker ON model_assumptions (ticker, created_at DESC);

-- ─── valuations (always ranges, never single point) ───────────────────────────
CREATE TABLE IF NOT EXISTS valuations (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker              text NOT NULL REFERENCES tickers(symbol),
  method              text NOT NULL CHECK (method IN ('pe','fwd_pe','peg','ps','ev_ebitda','p_fcf','dcf','historical','peers','aggregate')),
  value_low           numeric NOT NULL,
  value_base          numeric NOT NULL,
  value_high          numeric NOT NULL,
  bear_case           numeric,
  bull_case           numeric,
  assumptions_version text,
  source              text NOT NULL,
  as_of               timestamptz NOT NULL,
  created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_valuations_ticker ON valuations (ticker, method, created_at DESC);

-- ─── raw ingest audit log ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_price_ingest (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker      text NOT NULL,
  raw         jsonb NOT NULL,
  source      text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_raw_price_ingest_ticker ON raw_price_ingest (ticker, ingested_at DESC);
