-- Raw provider payload tables (append-only audit trail for ingest debugging)
-- Separate from raw_price_ingest (which only stores price payloads)

CREATE TABLE IF NOT EXISTS public.raw_prices (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    ticker     text NOT NULL,
    provider   text NOT NULL,
    payload    jsonb NOT NULL,
    as_of      date NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_prices_ticker ON public.raw_prices (ticker, as_of DESC);

CREATE TABLE IF NOT EXISTS public.raw_fundamentals (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    ticker     text NOT NULL,
    provider   text NOT NULL,
    payload    jsonb NOT NULL,
    as_of      date NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_fundamentals_ticker ON public.raw_fundamentals (ticker, as_of DESC);
