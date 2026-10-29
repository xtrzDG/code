"""Statements on `workshop.rate_limit_buckets` (migrations 1041, 1135, 1215)."""

from typing import LiteralString

RATE_LIMIT_BUCKETS_TABLE: str = "rate_limit_buckets"

# One request more for every key when every counter stays within its
# limit, decided by `workshop.count_request_within_limits` (1135) in this
# one statement: the counter rows are locked only while it runs, never
# across a round trip to the application. Returns the refused counter's key
# or NULL.
COUNT_REQUEST_WITHIN_LIMITS: LiteralString = """
select workshop.count_request_within_limits(
    %(bucket_keys)s::text[],
    %(counter_keys)s::text[],
    %(counter_limits)s::integer[],
    %(window_seconds)s::integer,
    %(window_start)s::bigint,
    %(previous_start)s::bigint,
    %(expires_at)s::bigint,
    %(window_microseconds)s::bigint,
    %(elapsed_microseconds)s::bigint
)
"""
# Up to `lease_units` requests of one key at once, as many as its limit
# still holds (`workshop.lease_requests_within_limit`, 1215): returns how
# many it counted, which the process then admits on its own.
LEASE_REQUESTS_WITHIN_LIMIT: LiteralString = """
select workshop.lease_requests_within_limit(
    %(key)s::text,
    %(request_limit)s::integer,
    %(lease_units)s::integer,
    %(window_seconds)s::integer,
    %(window_start)s::bigint,
    %(previous_start)s::bigint,
    %(expires_at)s::bigint,
    %(window_microseconds)s::bigint,
    %(elapsed_microseconds)s::bigint
)
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
