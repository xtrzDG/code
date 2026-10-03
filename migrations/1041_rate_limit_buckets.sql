-- 1041_rate_limit_buckets
--
-- Request rate limits shared by every API instance (the website widget's
-- messages, polling and error reports, login code checks). One row counts
-- the requests of one key in one fixed window; a request is allowed while
--
--   previous window's count * (part of it still inside the sliding window)
--   + current window's count
--
-- stays within the limit (app/utilities/limits/sliding_window_limits.py).
-- A request is one statement: insert ... on conflict do update set
-- request_count = request_count + 1 returning, joined with the previous
-- window's row; a request over a limit is rolled back
-- (app/adapters/rate_limits/postgres_rate_limit_bucket_adapter.py).
--
-- Times are UNIX microseconds. A row is needed until the end of the window
-- after its own (expires_at); the sweep_rate_limit_buckets job deletes the
-- rest every ten minutes.
--
-- UNLOGGED: the counters are short-lived and written on every public
-- request, so they skip the write-ahead log; a crash or a failover empties
-- the table, which only resets the limits. The fill factor leaves room on
-- each page for HOT updates of the hot rows (a business's and the
-- platform's counters).
--
-- A platform table (business_id is always null): row-level security as on
-- every table of the schema; the adapter runs platform-wide.

create unlogged table if not exists workshop.rate_limit_buckets (
    bucket_key text not null,
    window_seconds integer not null,
    window_start bigint not null,
    request_count integer not null,
    expires_at bigint not null,
    business_id text,
    primary key (bucket_key, window_seconds, window_start)
) with (fillfactor = 70);

create index if not exists rate_limit_buckets_expires_at_idx
    on workshop.rate_limit_buckets (expires_at);

alter table workshop.rate_limit_buckets enable row level security;
alter table workshop.rate_limit_buckets force row level security;
drop policy if exists business_isolation on workshop.rate_limit_buckets;
create policy business_isolation on workshop.rate_limit_buckets
    using (
        business_id = current_setting('app.business_id', true)
        or current_setting('app.bypass_rls', true) = 'on'
    )
    with check (
        business_id = current_setting('app.business_id', true)
        or current_setting('app.bypass_rls', true) = 'on'
    );
