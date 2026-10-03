"""Shared request rate limits: the counters a request counts against."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.platform.constrained_integers import (
    RateLimitRequestCount,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey


class RateLimitCounter(ImmutableDTO):
    """One limit a request counts against: `limit` requests of `key` per window."""

    key: RateLimitKey
    limit: RequestsPerWindow


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
