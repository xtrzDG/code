"""Statements on `workshop.rate_limit_buckets` (migration 1041)."""

from typing import LiteralString

RATE_LIMIT_BUCKETS_TABLE: str = "rate_limit_buckets"

# One request more for every key, in key order (concurrent requests lock
# the same rows in the same order), with each key's count in the window
# before. The rows stay locked until the transaction ends, so a request
# that turns out to be over a limit is rolled back before anyone else
# counts on top of it.
COUNT_REQUESTS: LiteralString = """
with counted as (
    insert into workshop.rate_limit_buckets as bucket
        (bucket_key, window_seconds, window_start, request_count, expires_at)
    select incoming.key, %(window_seconds)s, %(window_start)s, 1, %(expires_at)s
    from unnest(%(keys)s::text[]) as incoming(key)
    order by incoming.key
    on conflict (bucket_key, window_seconds, window_start)
    do update set request_count = bucket.request_count + 1
    returning bucket.bucket_key, bucket.request_count
)
select counted.bucket_key, counted.request_count, coalesce(previous.request_count, 0)
from counted
left join workshop.rate_limit_buckets as previous
    on previous.bucket_key = counted.bucket_key
    and previous.window_seconds = %(window_seconds)s
    and previous.window_start = %(previous_start)s
"""
READ_COUNTS: LiteralString = """
select
    coalesce(sum(request_count) filter (where window_start = %(window_start)s), 0),
    coalesce(sum(request_count) filter (where window_start = %(previous_start)s), 0)
from workshop.rate_limit_buckets
where bucket_key = %(key)s
    and window_seconds = %(window_seconds)s
    and window_start in (%(window_start)s, %(previous_start)s)
"""
# Small batches keep the sweep's locks short next to the hot rows.
DELETE_EXPIRED_BATCH: LiteralString = """
delete from workshop.rate_limit_buckets
where ctid in (
    select ctid from workshop.rate_limit_buckets
    where expires_at <= %(now)s
    limit %(batch_size)s
)
"""
