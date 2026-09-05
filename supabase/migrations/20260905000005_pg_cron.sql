-- ─── Scheduled pipeline jobs ─────────────────────────────────────────────────
-- Requires: pg_cron + pg_net extensions (both available on Supabase Pro/Team).
-- Before running, set these GUC parameters in the Supabase dashboard
-- (Settings → Database → Configuration) or via ALTER ROLE:
--
--   app.supabase_url     = 'https://<project_ref>.supabase.co'
--   app.service_role_key = '<service_role_key>'
--   app.portfolio_id     = '<default_portfolio_uuid>'   -- for Telegram delivery

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- ─── Helper: call a Supabase Edge Function ────────────────────────────────────
create or replace function _private.call_edge_function(
    fn_name text,
    payload  jsonb default '{}'::jsonb
)
returns bigint           -- returns net request id
language plpgsql
security definer
set search_path = ''
as $$
declare
    _url     text := current_setting('app.supabase_url', true)
                     || '/functions/v1/' || fn_name;
    _key     text := current_setting('app.service_role_key', true);
    _req_id  bigint;
begin
    if _url is null or _key is null then
        raise warning 'app.supabase_url / app.service_role_key not configured — skipping %', fn_name;
        return null;
    end if;

    select net.http_post(
        url     := _url,
        headers := jsonb_build_object(
            'Authorization',  'Bearer ' || _key,
            'Content-Type',   'application/json'
        ),
        body    := payload
    ) into _req_id;

    return _req_id;
end;
$$;

-- ─── Premarket pipeline — 5:30 AM ET (10:30 UTC) Mon–Fri ─────────────────────
-- Triggers daily-brief Edge Function which calls /brief/{portfolio_id} on the
-- orchestrator, which auto-ingests stale prices, computes signals, and refreshes
-- the portfolio snapshot before serving the brief.
select cron.schedule(
    'premarket-pipeline',
    '30 10 * * 1-5',
    $$
    select _private.call_edge_function(
        'daily-brief',
        jsonb_build_object('portfolio_id', current_setting('app.portfolio_id', true))
    );
    $$
);

-- ─── EOD snapshot refresh — 4:15 PM ET (21:15 UTC) Mon–Fri ───────────────────
-- Re-runs the brief to capture closing prices and update the portfolio snapshot.
select cron.schedule(
    'eod-snapshot',
    '15 21 * * 1-5',
    $$
    select _private.call_edge_function(
        'daily-brief',
        jsonb_build_object('portfolio_id', current_setting('app.portfolio_id', true))
    );
    $$
);

-- ─── Telegram daily brief — 6:00 PM ET (23:00 UTC) Mon–Fri ───────────────────
-- Sends the formatted daily brief to the configured Telegram chat.
select cron.schedule(
    'telegram-daily-brief',
    '0 23 * * 1-5',
    $$
    select _private.call_edge_function(
        'telegram-brief',
        jsonb_build_object('portfolio_id', current_setting('app.portfolio_id', true))
    );
    $$
);
