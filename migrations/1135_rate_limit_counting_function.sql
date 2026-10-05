-- 1125_rate_limit_counting_function
--
-- A request's rate limits are counted and checked in one statement, inside
-- the database, so the counter rows are locked only while it runs.
--
-- Until now the adapter upserted the counters in a transaction, read the
-- counts back into Python, compared them with the limits there and only
-- then committed (or rolled back a refused request). The rows stayed
-- locked across that round trip, and every widget poll counts the same
-- two rows (its business and `widget-poll:platform`): under load each poll
-- waited for the Python threads of the polls before it, and the k6 widget
-- scenario's poll p95 grew to over a second (docs/operations/capacity.md).
--
-- workshop.count_request_within_limits(...) counts one request for every
-- key (an upsert in key order, so concurrent calls lock the rows in one
-- order), weighs each counter like
-- app/utilities/limits/sliding_window_limits.is_within_limit:
--
--   previous * (window - elapsed) + current * window <= limit * window
--
-- and, when a counter is over its limit, takes the request back out of
-- every key (deleting a bucket it created) and returns the first such
-- counter's key (in the given order); NULL when the request counted. The
-- rows stay locked until the statement's transaction ends, so a
-- concurrent request waits for the final counts: no two requests take the
-- last place, and a refused request counts nowhere.
--
-- Row-level security of the table wants app.bypass_rls = 'on' (a platform
-- table): the function turns it on for its own statements and gives the
-- caller's value back. A new function only: nothing existing is rewritten
-- or locked, and the previous release keeps its own statement on the same
-- rows while both serve.

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
    refused_key text;
begin
    perform set_config('app.bypass_rls', 'on', true);

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

    perform set_config('app.bypass_rls', coalesce(caller_bypass, ''), true);
    return refused_key;
end;
$function$;

comment on function workshop.count_request_within_limits(
    text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
) is
    'Count one request for every key when every counter stays within its '
    'sliding-window limit; otherwise count none and return the first '
    'counter key over its limit (migration 1125).';
