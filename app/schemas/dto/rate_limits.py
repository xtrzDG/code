"""Shared request rate limits: the counters a request counts against."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseSize,
    RateLimitRequestCount,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey


class RateLimitCounter(ImmutableDTO):
    """
    One limit a request counts against: `limit` requests of `key` per window.

    `lease_size`: None counts every request in the shared counter (one
    statement for all such counters of a request). A size makes each
    process take that many requests from the shared counter at a time and
    admit them on its own (`RequestRateLimitRegistry`): for a counter every
    request of a busy endpoint shares (a business's or the platform's
    widget polls), so they do not all queue on one row.
    """

    key: RateLimitKey
    limit: RequestsPerWindow
    lease_size: RateLimitLeaseSize | None = None


class RateLimitWindow(ImmutableDTO):
    """
    Where a moment falls in the fixed windows of one length: the window
    that holds it starts at `started_at`; the one before it started one
    length earlier.
    """

    length_seconds: RateWindowSeconds
    started_at: Microseconds
    now: Microseconds


class RateLimitBucketCounts(ImmutableDTO):
    """The requests of one key in the current window and in the one before."""

    key: RateLimitKey
    current_count: RateLimitRequestCount
    previous_count: RateLimitRequestCount
