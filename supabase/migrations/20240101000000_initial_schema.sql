-- StockIntel initial schema
-- All user-owned tables have RLS enabled; service-owned tables (prices, fundamentals) are readable by authed users.
-- Every row carries source + as_of per CLAUDE.md §5.

-- ─── Extensions ─────────────────────────────────────────────────────────────
create extension if not exists "pg_cron";
create extension if not exists "pg_net";

-- ─── Profiles ────────────────────────────────────────────────────────────────
create table public.profiles (
  id                       uuid primary key default gen_random_uuid(),
  user_id                  uuid not null references auth.users on delete cascade,
  display_name             text,
  risk_tolerance           text not null default 'moderate' check (risk_tolerance in ('conservative','moderate','aggressive')),
  target_cagr              numeric(6,4) not null default 0.10,
  horizon_years            int not null default 3,
  brief_time               text not null default '06:00',
  telegram_chat_id         text,
  notifications_enabled    boolean not null default true,
  disclaimer_acknowledged  boolean not null default false,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  unique (user_id)
);
alter table public.profiles enable row level security;
create policy "Users see own profile" on public.profiles for all using (auth.uid() = user_id);

-- ─── Portfolios & Positions ──────────────────────────────────────────────────
create table public.portfolios (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users on delete cascade,
  name       text not null default 'My Portfolio',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.portfolios enable row level security;
create policy "Users manage own portfolios" on public.portfolios for all using (auth.uid() = user_id);

create table public.positions (
  id           uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.portfolios on delete cascade,
  ticker       text not null,
  quantity     numeric(18,6) not null,
  cost_basis   numeric(18,4) not null,
  opened_at    date not null default current_date,
  notes        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
alter table public.positions enable row level security;
create policy "Users manage own positions" on public.positions for all
  using (exists (select 1 from public.portfolios p where p.id = portfolio_id and p.user_id = auth.uid()));

-- ─── Watchlists ──────────────────────────────────────────────────────────────
create table public.watchlists (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users on delete cascade,
  name       text not null default 'Watchlist',
  created_at timestamptz not null default now()
);
alter table public.watchlists enable row level security;
create policy "Users manage own watchlists" on public.watchlists for all using (auth.uid() = user_id);

create table public.watchlist_items (
  id           uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references public.watchlists on delete cascade,
  ticker       text not null,
  added_at     timestamptz not null default now(),
  unique (watchlist_id, ticker)
);
alter table public.watchlist_items enable row level security;
create policy "Users manage own watchlist items" on public.watchlist_items for all
  using (exists (select 1 from public.watchlists w where w.id = watchlist_id and w.user_id = auth.uid()));

-- ─── Tickers (reference) ─────────────────────────────────────────────────────
create table public.tickers (
  symbol    text primary key,
  name      text not null,
  sector    text,
  industry  text,
  exchange  text not null default 'NASDAQ',
  updated_at timestamptz not null default now()
);
alter table public.tickers enable row level security;
create policy "Authenticated users read tickers" on public.tickers for select using (auth.role() = 'authenticated');

-- ─── Prices (partitioned by year) ────────────────────────────────────────────
create table public.prices_daily (
  ticker    text not null,
  date      date not null,
  open      numeric(18,4),
  high      numeric(18,4),
  low       numeric(18,4),
  close     numeric(18,4) not null,
  adj_close numeric(18,4) not null,
  volume    bigint,
  source    text not null default 'unknown',
  primary key (ticker, date)
) partition by range (date);

create table public.prices_daily_2023 partition of public.prices_daily
  for values from ('2023-01-01') to ('2024-01-01');
create table public.prices_daily_2024 partition of public.prices_daily
  for values from ('2024-01-01') to ('2025-01-01');
create table public.prices_daily_2025 partition of public.prices_daily
  for values from ('2025-01-01') to ('2026-01-01');
create table public.prices_daily_2026 partition of public.prices_daily
  for values from ('2026-01-01') to ('2027-01-01');

alter table public.prices_daily enable row level security;
create policy "Authenticated users read prices" on public.prices_daily for select using (auth.role() = 'authenticated');

-- ─── Fundamentals & Estimates ────────────────────────────────────────────────
create table public.fundamentals (
  id               uuid primary key default gen_random_uuid(),
  ticker           text not null,
  fiscal_period    text not null,
  revenue          numeric(20,2),
  revenue_growth   numeric(8,4),
  gross_margin     numeric(8,4),
  operating_margin numeric(8,4),
  net_margin       numeric(8,4),
  eps              numeric(12,4),
  eps_expected     numeric(12,4),
  fcf              numeric(20,2),
  guidance_revenue numeric(20,2),
  guidance_eps     numeric(12,4),
  source           text not null,
  as_of            date not null,
  created_at       timestamptz not null default now(),
  unique (ticker, fiscal_period, source)
);
alter table public.fundamentals enable row level security;
create policy "Authenticated users read fundamentals" on public.fundamentals for select using (auth.role() = 'authenticated');

create table public.estimates (
  id              uuid primary key default gen_random_uuid(),
  ticker          text not null,
  fiscal_period   text not null,
  revenue_est     numeric(20,2),
  eps_est         numeric(12,4),
  guidance_est    numeric(20,2),
  source          text not null,
  as_of           date not null,
  created_at      timestamptz not null default now()
);
alter table public.estimates enable row level security;
create policy "Authenticated users read estimates" on public.estimates for select using (auth.role() = 'authenticated');

-- ─── News Events & Catalysts ─────────────────────────────────────────────────
create table public.news_events (
  id                 uuid primary key default gen_random_uuid(),
  tickers            text[],
  source             text not null,
  headline           text not null,
  url                text,
  materiality_score  numeric(4,3) not null default 0 check (materiality_score between 0 and 1),
  sentiment          text not null default 'neutral' check (sentiment in ('positive','negative','neutral')),
  affects_earnings   boolean not null default false,
  affects_valuation  boolean not null default false,
  affects_thesis     boolean not null default false,
  as_of              timestamptz not null default now(),
  created_at         timestamptz not null default now()
);
alter table public.news_events enable row level security;
create policy "Authenticated users read news" on public.news_events for select using (auth.role() = 'authenticated');

create table public.catalysts (
  id              uuid primary key default gen_random_uuid(),
  ticker          text not null,
  type            text not null check (type in ('earnings','filing','fda','macro','dividend','guidance','other')),
  description     text not null,
  date            date not null,
  expected_impact text not null default 'neutral' check (expected_impact in ('positive','negative','neutral')),
  created_at      timestamptz not null default now()
);
alter table public.catalysts enable row level security;
create policy "Authenticated users read catalysts" on public.catalysts for select using (auth.role() = 'authenticated');

-- ─── Portfolio Snapshots & Changes ───────────────────────────────────────────
create table public.portfolio_snapshots (
  id                    uuid primary key default gen_random_uuid(),
  portfolio_id          uuid not null references public.portfolios on delete cascade,
  date                  date not null,
  total_value           numeric(20,2) not null,
  day_return            numeric(8,4) not null default 0,
  period_return         numeric(8,4) not null default 0,
  health_score          int not null default 75 check (health_score between 0 and 100),
  diversification_score int not null default 75 check (diversification_score between 0 and 100),
  risk_score            int not null default 75 check (risk_score between 0 and 100),
  quality_score         int not null default 75 check (quality_score between 0 and 100),
  risk_level            text not null default 'moderate' check (risk_level in ('low','moderate','elevated','high')),
  exposures             jsonb not null default '{}',
  risk_metrics          jsonb not null default '{}',
  target_probability    numeric(6,4) not null default 0.5,
  target_probability_delta numeric(6,4) not null default 0,
  created_at            timestamptz not null default now(),
  unique (portfolio_id, date)
);
alter table public.portfolio_snapshots enable row level security;
create policy "Users read own snapshots" on public.portfolio_snapshots for all
  using (exists (select 1 from public.portfolios p where p.id = portfolio_id and p.user_id = auth.uid()));

create table public.portfolio_changes (
  id           uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.portfolios on delete cascade,
  date         date not null,
  ticker       text,
  change_type  text not null check (change_type in ('price','news','fundamental','risk','graph','ml','target_probability')),
  summary      text not null,
  detail       text,
  evidence_url text,
  created_at   timestamptz not null default now()
);
alter table public.portfolio_changes enable row level security;
create policy "Users read own changes" on public.portfolio_changes for all
  using (exists (select 1 from public.portfolios p where p.id = portfolio_id and p.user_id = auth.uid()));

-- ─── ML Signals ──────────────────────────────────────────────────────────────
create table public.signals (
  id            uuid primary key default gen_random_uuid(),
  ticker        text not null,
  date          date not null,
  model_version text not null,
  probability   numeric(6,4) not null,
  rank_score    numeric(6,2) not null,
  confidence    numeric(6,4) not null,
  is_forecast   boolean not null default true,
  created_at    timestamptz not null default now(),
  unique (ticker, date, model_version)
);
alter table public.signals enable row level security;
create policy "Authenticated users read signals" on public.signals for select using (auth.role() = 'authenticated');

-- ─── Analysis Runs ───────────────────────────────────────────────────────────
create table public.analysis_runs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users,
  ticker        text not null,
  portfolio_id  uuid references public.portfolios,
  inputs        jsonb not null default '{}',
  tool_results  jsonb not null default '{}',
  final_report  text,
  latency_ms    int,
  token_usage   jsonb,
  created_at    timestamptz not null default now()
);
alter table public.analysis_runs enable row level security;
create policy "Users read own analysis runs" on public.analysis_runs for all using (auth.uid() = user_id);

-- ─── Alerts ──────────────────────────────────────────────────────────────────
create table public.alerts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users on delete cascade,
  type         text not null check (type in ('risk','catalyst','news','thesis','price')),
  tickers      text[] not null default '{}',
  title        text not null,
  body         text not null,
  evidence     text,
  delivered_at timestamptz,
  read_at      timestamptz,
  created_at   timestamptz not null default now()
);
alter table public.alerts enable row level security;
create policy "Users manage own alerts" on public.alerts for all using (auth.uid() = user_id);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
create index on public.prices_daily (ticker, date desc);
create index on public.fundamentals (ticker, as_of desc);
create index on public.news_events using gin (tickers);
create index on public.news_events (as_of desc);
create index on public.catalysts (ticker, date);
create index on public.signals (ticker, date desc);
create index on public.alerts (user_id, created_at desc);
create index on public.portfolio_snapshots (portfolio_id, date desc);
create index on public.portfolio_changes (portfolio_id, date desc);
