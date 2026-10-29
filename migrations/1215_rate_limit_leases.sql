-- 1215_rate_limit_leases
--
-- A process takes several requests of one rate-limit counter at a time
-- (a lease) and admits them on its own.
--
-- Every widget poll counted its business's row and the platform's row of
-- rate_limit_buckets (`widget-poll:business:<id>`, `widget-poll:platform`)
-- in its own statement: 250 polls a second queued on one row lock, and on
-- a saturated runner a holder descheduled in the middle of its statement
-- held every other poll for that long (the k6 widget scenario's poll p95
-- of 2026-10-19/20, docs/operations/capacity.md). These two counters are
-- now leased: a process counts `lease_units` requests on the row in one
-- statement and admits them without touching it again, so the row sees
-- one statement per lease instead of one per poll. Each unit is counted
-- before it admits a request, so all processes together never admit more
-- than the limit (units a process leaves unused stay counted).
--
-- workshop.lease_requests_within_limit(...) counts `lease_units` more on
-- the window's row of the key (an upsert that locks it until the
-- statement ends), weighs the counter like
-- app/utilities/limits/sliding_window_limits.lease_grant:
--
--   the most requests the window may hold =
--     floor((limit * window - previous * (window - elapsed)) / window)
--
-- and keeps only as many of the units as fit (0 to lease_units): the rest
-- is taken back at once, and a row the call created that holds none is
-- deleted, so a refused lease leaves nothing behind. Returns the units it
-- kept. It sets no scope: like the request rate limits, it runs on the
-- platform pool, whose group (workshop_platform) sees every row of the
-- platform table through its `platform_access` policy (1200), and only
-- that group may call it. The previous release never calls it.
--
-- workshop.count_request_within_limits (1135) is replaced by the same
-- function with its two scope switches written as PL/pgSQL expressions
-- (`scope_switched := set_config(...)`) instead of `perform` queries:
-- every request counted pays two executor runs less, and the counts,
-- refusals and scope handling stay exactly as they were (the previous
-- release calls the same signature and gets the same answers). No policy
-- reads app.bypass_rls since 1200; the switch stays only for a release
-- before 1200 after a rollback past it (workshop.
-- revert_tenant_and_platform_roles brings back the policies that read it).
-- Its privileges stay as 1200 left them (create or replace keeps them, and
-- they are stated again below): workshop_platform alone may call it.
-- Functions only: no table is rewritten or locked.

create or replace function workshop.lease_requests_within_limit(
    lease_key text,
    request_limit integer,
    lease_units integer,
    window_length_seconds integer,
    current_window_start bigint,
    previous_window_start bigint,
    bucket_expires_at bigint,
    window_length_microseconds bigint,
    elapsed_microseconds bigint
) returns integer
language plpgsql
volatile
as $function$
declare
    counted integer;
    earlier integer;
    most_in_window numeric;
    granted integer;
begin
    insert into workshop.rate_limit_buckets as bucket
        (bucket_key, window_seconds, window_start, request_count, expires_at)
    values (lease_key, window_length_seconds, current_window_start,
        lease_units, bucket_expires_at)
    on conflict (bucket_key, window_seconds, window_start)
    do update set request_count = bucket.request_count + lease_units
    returning bucket.request_count into counted;

    select coalesce(max(previous.request_count), 0) into earlier
    from workshop.rate_limit_buckets as previous
    where previous.bucket_key = lease_key
        and previous.window_seconds = window_length_seconds
        and previous.window_start = previous_window_start;

    most_in_window := floor(
        (request_limit::numeric * window_length_microseconds
            - earlier::numeric
                * (window_length_microseconds - elapsed_microseconds))
        / window_length_microseconds
    );
    granted := greatest(
        0,
        least(lease_units::numeric, most_in_window - (counted - lease_units))
    )::integer;

    if granted < lease_units then
        if counted - lease_units + granted = 0 then
            -- The row holds only this call's units: it created it.
            delete from workshop.rate_limit_buckets as bucket
            where bucket.bucket_key = lease_key
                and bucket.window_seconds = window_length_seconds
                and bucket.window_start = current_window_start;
        else
            update workshop.rate_limit_buckets as bucket
            set request_count = counted - lease_units + granted
            where bucket.bucket_key = lease_key
                and bucket.window_seconds = window_length_seconds
                and bucket.window_start = current_window_start;
        end if;
    end if;

    return granted;
end;
$function$;

comment on function workshop.lease_requests_within_limit(
    text, integer, integer, integer, bigint, bigint, bigint, bigint, bigint
) is
    'Count up to lease_units requests of one key in its sliding-window '
    'limit and return how many were counted; a process admits that many '
    'on its own (migration 1215).';

create or replace function workshop.count_request_within_limits(
    bucket_keys text[],
    counter_keys text[],
    counter_limits integer[],
    window_length_seconds integer,
    current_window_start bigint,
    previous_window_start bigint,
    bucket_expires_at bigint,
    window_length_microseconds bigint,
    elapsed_microseconds bigint
) returns text
language plpgsql
volatile
as $function$
declare
    caller_bypass text := current_setting('app.bypass_rls', true);
    scope_switched text;
    refused_key text;
begin
    scope_switched := set_config('app.bypass_rls', 'on', true);

    with counted as (
        insert into workshop.rate_limit_buckets as bucket
            (bucket_key, window_seconds, window_start, request_count, expires_at)
        select incoming.key, window_length_seconds, current_window_start, 1,
            bucket_expires_at
        from unnest(bucket_keys) as incoming(key)
        order by incoming.key
        on conflict (bucket_key, window_seconds, window_start)
        do update set request_count = bucket.request_count + 1
        returning bucket.bucket_key, bucket.request_count
    )
    select checked.counter_key into refused_key
    from unnest(counter_keys, counter_limits) with ordinality
        as checked(counter_key, counter_limit, counter_order)
    join counted on counted.bucket_key = checked.counter_key
    left join workshop.rate_limit_buckets as earlier
        on earlier.bucket_key = checked.counter_key
        and earlier.window_seconds = window_length_seconds
        and earlier.window_start = previous_window_start
    where coalesce(earlier.request_count, 0)::numeric
            * (window_length_microseconds - elapsed_microseconds)
        + counted.request_count::numeric * window_length_microseconds
        > checked.counter_limit::numeric * window_length_microseconds
    order by checked.counter_order
    limit 1;

    if refused_key is not null then
        -- Rows of this window with a count of 1 hold only this request.
        delete from workshop.rate_limit_buckets as bucket
        where bucket.bucket_key = any(bucket_keys)
            and bucket.window_seconds = window_length_seconds
            and bucket.window_start = current_window_start
            and bucket.request_count = 1;
        update workshop.rate_limit_buckets as bucket
        set request_count = bucket.request_count - 1
        where bucket.bucket_key = any(bucket_keys)
            and bucket.window_seconds = window_length_seconds
            and bucket.window_start = current_window_start;
    end if;

    scope_switched := set_config(
        'app.bypass_rls', coalesce(caller_bypass, ''), true
    );
    return refused_key;
end;
$function$;

comment on function workshop.count_request_within_limits(
    text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
) is
    'Count one request for every key when every counter stays within its '
    'sliding-window limit; otherwise count none and return the first '
    'counter key over its limit (migrations 1135, 1215).';

revoke all on function workshop.lease_requests_within_limit(
    text, integer, integer, integer, bigint, bigint, bigint, bigint, bigint
) from public;
grant execute on function workshop.lease_requests_within_limit(
    text, integer, integer, integer, bigint, bigint, bigint, bigint, bigint
) to workshop_platform;
revoke all on function workshop.count_request_within_limits(
    text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
) from public;
grant execute on function workshop.count_request_within_limits(
    text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
) to workshop_platform;
