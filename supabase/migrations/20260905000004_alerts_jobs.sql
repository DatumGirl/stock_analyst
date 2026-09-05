-- Alerts, push tokens, and pg_cron scheduled jobs

-- ─── alerts ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  type             text NOT NULL CHECK (type IN ('risk','catalyst','news','thesis','price')),
  tickers          text[] NOT NULL DEFAULT '{}',
  title            text NOT NULL,
  body             text NOT NULL,
  evidence         text,
  delivered_at     timestamptz,
  read_at          timestamptz,
  push_sent_at     timestamptz,
  telegram_sent_at timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY alerts_owner ON alerts USING (user_id = auth.uid());
CREATE INDEX IF NOT EXISTS idx_alerts_user_created ON alerts (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts (user_id, read_at) WHERE read_at IS NULL;

-- ─── push_tokens ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS push_tokens (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  device_token text NOT NULL,
  platform     text NOT NULL CHECK (platform IN ('ios','android')),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, device_token)
);
ALTER TABLE push_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY push_tokens_owner ON push_tokens USING (user_id = auth.uid());

-- pg_cron scheduled jobs are defined in 20260905000005_pg_cron.sql
