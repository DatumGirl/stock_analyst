-- Additive migration: tables not present in the initial schema.
-- Safe to run after 20240101000000_initial_schema.sql.

-- ─── raw provider payloads (append-only audit trail) ─────────────────────────
create table if not exists public.raw_prices (
    id          uuid primary key default gen_random_uuid(),
    created_at  timestamptz not null default now(),
    ticker      text not null,
    provider    text not null,
    payload     jsonb not null,
    as_of       date not null
);

create table if not exists public.raw_fundamentals (
    id          uuid primary key default gen_random_uuid(),
    created_at  timestamptz not null default now(),
    ticker      text not null,
    provider    text not null,
    payload     jsonb not null,
    as_of       date not null
);

-- ─── model_assumptions (versioned — never overwrite, always insert) ───────────
create table if not exists public.model_assumptions (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    ticker          text not null,
    version         integer not null,
    forecast_years  integer[] not null,
    revenue         numeric(20,2)[] not null,
    revenue_growth  numeric(8,6)[],
    gross_margin    numeric(8,6)[],
    operating_margin numeric(8,6)[],
    eps             numeric(10,4)[],
    free_cash_flow  numeric(20,2)[],
    trigger_type    text not null check (trigger_type in ('earnings','news_event','manual','init')),
    trigger_ref     uuid,
    notes           text,
    source          text not null,
    as_of           date not null,
    unique (ticker, version)
);

alter table public.model_assumptions enable row level security;
create policy "model_assumptions: public read" on public.model_assumptions for select using (true);

-- ─── valuations (always low/base/high — never a single point) ─────────────────
create table if not exists public.valuations (
    id                  uuid primary key default gen_random_uuid(),
    created_at          timestamptz not null default now(),
    ticker              text not null,
    method              text not null check (method in ('pe','fwd_pe','peg','ps','ev_ebitda','p_fcf','dcf','historical','peers')),
    assumptions_version integer,
    value_low           numeric(18,4) not null,
    value_base          numeric(18,4) not null,
    value_high          numeric(18,4) not null,
    is_forecast         boolean not null default true,
    source              text not null,
    as_of               date not null
);

alter table public.valuations enable row level security;
create policy "valuations: public read" on public.valuations for select using (true);
