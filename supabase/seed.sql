-- Seed data for local development
-- Run after: supabase db reset

-- ─── Reference tickers ───────────────────────────────────────────────────────
insert into public.tickers (symbol, name, sector, industry, exchange) values
  ('AAPL',  'Apple Inc.',                    'Technology',         'Consumer Electronics',          'NASDAQ'),
  ('MSFT',  'Microsoft Corporation',         'Technology',         'Software—Infrastructure',       'NASDAQ'),
  ('NVDA',  'NVIDIA Corporation',            'Technology',         'Semiconductors',                'NASDAQ'),
  ('GOOGL', 'Alphabet Inc.',                 'Communication Svcs', 'Internet Content & Information', 'NASDAQ'),
  ('AMZN',  'Amazon.com Inc.',               'Consumer Cyclical',  'Internet Retail',               'NASDAQ'),
  ('META',  'Meta Platforms Inc.',           'Communication Svcs', 'Internet Content & Information', 'NASDAQ'),
  ('TSLA',  'Tesla Inc.',                    'Consumer Cyclical',  'Auto Manufacturers',            'NASDAQ'),
  ('JPM',   'JPMorgan Chase & Co.',          'Financial Services', 'Banks—Diversified',             'NYSE'),
  ('V',     'Visa Inc.',                     'Financial Services', 'Credit Services',               'NYSE'),
  ('JNJ',   'Johnson & Johnson',             'Healthcare',         'Drug Manufacturers—General',    'NYSE'),
  ('SPY',   'SPDR S&P 500 ETF Trust',        null,                 'ETF',                           'NYSE'),
  ('QQQ',   'Invesco QQQ Trust',             null,                 'ETF',                           'NASDAQ'),
  ('AMD',   'Advanced Micro Devices Inc.',   'Technology',         'Semiconductors',                'NASDAQ'),
  ('TSMC',  'Taiwan Semiconductor Mfg Co.',  'Technology',         'Semiconductors',                'NYSE')
on conflict (symbol) do nothing;

-- ─── Demo prices (AAPL, MSFT, NVDA — last 5 days) ────────────────────────────
insert into public.prices_daily (ticker, date, open, high, low, close, adj_close, volume, source) values
  ('AAPL', '2026-08-29', 218.50, 221.30, 217.80, 220.45, 220.45, 62000000, 'seed'),
  ('AAPL', '2026-09-01', 220.00, 223.10, 219.50, 222.80, 222.80, 58000000, 'seed'),
  ('AAPL', '2026-09-02', 222.50, 225.00, 221.80, 224.10, 224.10, 71000000, 'seed'),
  ('AAPL', '2026-09-03', 224.00, 226.40, 223.20, 225.90, 225.90, 65000000, 'seed'),
  ('AAPL', '2026-09-04', 225.50, 228.00, 224.70, 227.30, 227.30, 68000000, 'seed'),

  ('MSFT', '2026-08-29', 415.20, 419.80, 414.60, 418.50, 418.50, 22000000, 'seed'),
  ('MSFT', '2026-09-01', 418.00, 422.30, 417.40, 421.70, 421.70, 19000000, 'seed'),
  ('MSFT', '2026-09-02', 421.50, 425.00, 420.80, 424.20, 424.20, 24000000, 'seed'),
  ('MSFT', '2026-09-03', 424.00, 427.50, 423.10, 426.80, 426.80, 21000000, 'seed'),
  ('MSFT', '2026-09-04', 426.50, 430.00, 425.60, 429.40, 429.40, 23000000, 'seed'),

  ('NVDA', '2026-08-29', 118.40, 122.60, 117.90, 121.50, 121.50, 310000000, 'seed'),
  ('NVDA', '2026-09-01', 121.00, 125.80, 120.50, 124.90, 124.90, 340000000, 'seed'),
  ('NVDA', '2026-09-02', 124.50, 129.20, 123.80, 128.30, 128.30, 380000000, 'seed'),
  ('NVDA', '2026-09-03', 128.00, 132.40, 127.30, 131.70, 131.70, 420000000, 'seed'),
  ('NVDA', '2026-09-04', 131.20, 135.80, 130.50, 134.90, 134.90, 455000000, 'seed')
on conflict (ticker, date) do nothing;

-- ─── Demo fundamentals ───────────────────────────────────────────────────────
insert into public.fundamentals (ticker, fiscal_period, revenue, revenue_growth, gross_margin, operating_margin, net_margin, eps, eps_expected, fcf, guidance_revenue, guidance_eps, source, as_of) values
  ('AAPL',  '2026-Q2', 95200000000,  0.052, 0.463, 0.311, 0.263, 1.65, 1.60, 27300000000, 97500000000, 1.72, 'seed', '2026-08-01'),
  ('MSFT',  '2026-Q4', 70000000000,  0.159, 0.698, 0.452, 0.368, 3.23, 3.10, 26800000000, 72500000000, 3.35, 'seed', '2026-07-30'),
  ('NVDA',  '2026-Q2', 36100000000,  1.220, 0.748, 0.617, 0.553, 0.89, 0.82, 19400000000, 40000000000, 0.95, 'seed', '2026-08-28')
on conflict (ticker, fiscal_period, source) do nothing;

-- ─── Demo catalysts ───────────────────────────────────────────────────────────
insert into public.catalysts (ticker, type, description, date, expected_impact) values
  ('AAPL',  'earnings', 'Q3 FY2026 earnings call', '2026-10-28', 'neutral'),
  ('MSFT',  'earnings', 'Q1 FY2027 earnings call', '2026-10-29', 'positive'),
  ('NVDA',  'earnings', 'Q3 FY2027 earnings call', '2026-11-19', 'positive'),
  ('JPM',   'earnings', 'Q3 2026 earnings call',   '2026-10-14', 'neutral')
on conflict do nothing;

-- ─── Demo news events ────────────────────────────────────────────────────────
insert into public.news_events (tickers, source, headline, url, materiality_score, sentiment, affects_earnings, affects_valuation, affects_thesis, as_of) values
  (array['NVDA'], 'Bloomberg', 'NVIDIA announces next-gen Blackwell Ultra chip with 40% performance uplift', null, 0.85, 'positive', true, true, true, now() - interval '1 day'),
  (array['AAPL'], 'Reuters',   'Apple expands AI features in iOS 20, targets enterprise market', null, 0.65, 'positive', true, false, false, now() - interval '2 days'),
  (array['TSMC', 'NVDA', 'AMD'], 'WSJ', 'Taiwan earthquake causes minor disruption to TSMC fabs', null, 0.72, 'negative', true, true, true, now() - interval '3 hours')
on conflict do nothing;

-- ─── Demo ML signals ─────────────────────────────────────────────────────────
insert into public.signals (ticker, date, model_version, probability, rank_score, confidence, is_forecast) values
  ('NVDA', current_date, 'v1.0-seed', 0.71, 81, 0.78, true),
  ('MSFT', current_date, 'v1.0-seed', 0.64, 76, 0.72, true),
  ('AAPL', current_date, 'v1.0-seed', 0.59, 71, 0.68, true),
  ('GOOGL', current_date, 'v1.0-seed', 0.55, 65, 0.61, true),
  ('AMD',  current_date, 'v1.0-seed', 0.52, 61, 0.59, true)
on conflict (ticker, date, model_version) do nothing;
