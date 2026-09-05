-- Seed data for local development
-- Run after: supabase db reset

INSERT INTO tickers (symbol, name, sector, industry, exchange) VALUES
  ('AAPL',  'Apple Inc.',                  'Technology',              'Consumer Electronics',   'NASDAQ'),
  ('MSFT',  'Microsoft Corporation',        'Technology',              'Software',               'NASDAQ'),
  ('NVDA',  'NVIDIA Corporation',           'Technology',              'Semiconductors',         'NASDAQ'),
  ('GOOGL', 'Alphabet Inc.',               'Communication Services',   'Internet Services',      'NASDAQ'),
  ('AMZN',  'Amazon.com Inc.',             'Consumer Discretionary',  'E-Commerce',             'NASDAQ'),
  ('META',  'Meta Platforms Inc.',         'Communication Services',   'Social Media',           'NASDAQ'),
  ('TSLA',  'Tesla Inc.',                  'Consumer Discretionary',  'Electric Vehicles',      'NASDAQ'),
  ('JPM',   'JPMorgan Chase & Co.',        'Financials',              'Banking',                'NYSE'),
  ('V',     'Visa Inc.',                   'Financials',              'Payment Processing',     'NYSE'),
  ('JNJ',   'Johnson & Johnson',           'Health Care',             'Pharmaceuticals',        'NYSE'),
  -- Macro instruments (used by macro agent)
  ('^VIX',    'CBOE Volatility Index',     NULL, NULL, 'CBOE'),
  ('^TNX',    '10-Year Treasury Yield',    NULL, NULL, 'CBOE'),
  ('^GSPC',   'S&P 500 Index',             NULL, NULL, 'NYSE'),
  ('DX-Y.NYB','US Dollar Index',           NULL, NULL, 'NYSE'),
  ('CL=F',    'Crude Oil Futures',         NULL, NULL, 'NYMEX'),
  ('GC=F',    'Gold Futures',              NULL, NULL, 'NYMEX')
ON CONFLICT (symbol) DO NOTHING;

-- Synthetic AAPL prices for last 30 trading days (for local quant testing)
INSERT INTO prices_daily (ticker, date, open, high, low, close, adj_close, volume, source, as_of)
SELECT
  'AAPL',
  (current_date - (n || ' days')::interval)::date,
  220 + (random() * 10 - 5)::numeric(8,2),
  225 + (random() * 5)::numeric(8,2),
  215 + (random() * 5)::numeric(8,2),
  220 + (random() * 10 - 5)::numeric(8,2),
  220 + (random() * 10 - 5)::numeric(8,2),
  (50000000 + random() * 20000000)::bigint,
  'seed',
  now()
FROM generate_series(1, 30) AS n
ON CONFLICT (ticker, date) DO NOTHING;

-- Synthetic MSFT prices
INSERT INTO prices_daily (ticker, date, open, high, low, close, adj_close, volume, source, as_of)
SELECT
  'MSFT',
  (current_date - (n || ' days')::interval)::date,
  415 + (random() * 15 - 7)::numeric(8,2),
  425 + (random() * 8)::numeric(8,2),
  408 + (random() * 8)::numeric(8,2),
  415 + (random() * 15 - 7)::numeric(8,2),
  415 + (random() * 15 - 7)::numeric(8,2),
  (20000000 + random() * 10000000)::bigint,
  'seed',
  now()
FROM generate_series(1, 30) AS n
ON CONFLICT (ticker, date) DO NOTHING;

-- Sample fundamentals for AAPL
INSERT INTO fundamentals (ticker, fiscal_period, revenue, revenue_growth, gross_margin, operating_margin, net_margin, eps, eps_expected, fcf, guidance_revenue, guidance_eps, source, as_of)
VALUES
  ('AAPL', '2026-Q1', 124500000000, 0.062, 0.461, 0.313, 0.238, 2.42, 2.35, 29800000000, 128000000000, 2.50, 'seed', now()),
  ('AAPL', '2025-Q4', 124300000000, 0.041, 0.454, 0.308, 0.233, 2.18, 2.10, 27900000000, NULL, NULL, 'seed', now())
ON CONFLICT (ticker, fiscal_period, source) DO NOTHING;

-- Sample catalyst
INSERT INTO catalysts (ticker, type, description, date, expected_impact, source, as_of)
VALUES
  ('AAPL', 'earnings', 'Q2 FY2026 Earnings Release', current_date + 14, 'positive', 'seed', now()),
  ('MSFT', 'earnings', 'Q3 FY2026 Earnings Release', current_date + 21, 'neutral',  'seed', now())
ON CONFLICT DO NOTHING;
