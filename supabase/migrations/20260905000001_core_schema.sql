-- Core schema: users, portfolios, positions, watchlists, tickers
-- All money/price values use numeric, never float (CLAUDE.md §5)

-- ─── updated_at trigger ──────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

-- ─── profiles ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                 uuid NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  display_name            text,
  risk_tolerance          text NOT NULL DEFAULT 'moderate'
                          CHECK (risk_tolerance IN ('conservative','moderate','aggressive')),
  target_cagr             numeric NOT NULL DEFAULT 0.10 CHECK (target_cagr > 0),
  horizon_years           int NOT NULL DEFAULT 3 CHECK (horizon_years > 0),
  brief_time              text NOT NULL DEFAULT '06:00',
  telegram_chat_id        text,
  notifications_enabled   bool NOT NULL DEFAULT true,
  disclaimer_acknowledged bool NOT NULL DEFAULT false,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id)
);
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY profiles_owner ON profiles USING (user_id = auth.uid());
CREATE TRIGGER profiles_updated_at BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── tickers (reference, no RLS — public read, service-role write) ────────────
CREATE TABLE IF NOT EXISTS tickers (
  symbol     text PRIMARY KEY,
  name       text NOT NULL,
  sector     text,
  industry   text,
  exchange   text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ─── portfolios ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolios (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  name       text NOT NULL DEFAULT 'My Portfolio',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY portfolios_owner ON portfolios USING (user_id = auth.uid());
CREATE TRIGGER portfolios_updated_at BEFORE UPDATE ON portfolios
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── positions ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS positions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id uuid NOT NULL REFERENCES portfolios ON DELETE CASCADE,
  ticker       text NOT NULL REFERENCES tickers(symbol),
  quantity     numeric NOT NULL CHECK (quantity > 0),
  cost_basis   numeric NOT NULL CHECK (cost_basis > 0),
  opened_at    timestamptz NOT NULL,
  notes        text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY positions_owner ON positions
  USING (portfolio_id IN (SELECT id FROM portfolios WHERE user_id = auth.uid()));
CREATE TRIGGER positions_updated_at BEFORE UPDATE ON positions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE INDEX idx_positions_portfolio ON positions (portfolio_id);

-- ─── watchlists ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlists (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  name       text NOT NULL DEFAULT 'My Watchlist',
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;
CREATE POLICY watchlists_owner ON watchlists USING (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS watchlist_items (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  watchlist_id uuid NOT NULL REFERENCES watchlists ON DELETE CASCADE,
  ticker       text NOT NULL REFERENCES tickers(symbol),
  added_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (watchlist_id, ticker)
);
ALTER TABLE watchlist_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY watchlist_items_owner ON watchlist_items
  USING (watchlist_id IN (SELECT id FROM watchlists WHERE user_id = auth.uid()));
CREATE INDEX idx_watchlist_items_watchlist ON watchlist_items (watchlist_id);
