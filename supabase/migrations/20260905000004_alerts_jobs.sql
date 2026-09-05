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

-- ─── pg_cron scheduled jobs ───────────────────────────────────────────────────
-- Requires pg_cron and pg_net extensions (enabled in Supabase by default)

-- Pre-market brief: 05:30 ET = 09:30 UTC, weekdays
SELECT cron.schedule(
  'premarket-brief',
  '30 9 * * 1-5',
  $$
  SELECT pg_net.http_post(
    url := current_setting('app.supabase_url') || '/functions/v1/premarket-brief',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);

-- Portfolio snapshot: 16:15 ET = 20:15 UTC, weekdays
SELECT cron.schedule(
  'portfolio-snapshot',
  '15 20 * * 1-5',
  $$
  SELECT pg_net.http_post(
    url := current_setting('app.supabase_url') || '/functions/v1/portfolio-snapshot',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);

-- EOD report: 18:00 ET = 22:00 UTC, weekdays
SELECT cron.schedule(
  'eod-report',
  '0 22 * * 1-5',
  $$
  SELECT pg_net.http_post(
    url := current_setting('app.supabase_url') || '/functions/v1/eod-report',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);
