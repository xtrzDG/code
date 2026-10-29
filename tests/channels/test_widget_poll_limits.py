"""
Widget polls across several API processes (here: one registry per process
over one set of shared counters). One visitor and one client network are
held to their limits exactly, whichever process each poll reaches; one
business and the platform never pass theirs either, though each process
takes their counters in leases (1% of the limit at a time) and admits from
them without counting every poll in the shared row. A refused poll counts
nowhere, and the shared rows see one count per lease, not per poll.
"""

from collections.abc import Sequence

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseGrant,
    RateLimitLeaseSize,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import (
    WIDGET_POLL_LIMITS,
    refuse_too_frequent_widget_requests,
)

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
PROCESSES: int = 4


class CountingBuckets(InMemoryRateLimitBucketAdapter):
    """Shared counters that count how often each kind of statement ran."""

    def __init__(self) -> None:
        super().__init__()
        self.counts: int = 0
        self.leases: int = 0

    def count_if_within(
        self, counters: Sequence[RateLimitCounter], window: RateLimitWindow
    ) -> RateLimitKey | None:
        self.counts += 1
        return super().count_if_within(counters, window)

    def lease_within(
        self,
        counter: RateLimitCounter,
        units: RateLimitLeaseSize,
        window: RateLimitWindow,
    ) -> RateLimitLeaseGrant:
        self.leases += 1
        return super().lease_within(counter, units, window)


def processes(
    buckets: InMemoryRateLimitBucketAdapter,
) -> list[RequestRateLimitRegistry]:
    return [RequestRateLimitRegistry(buckets) for _ in range(PROCESSES)]


def poll(
    registry: RequestRateLimitRegistry,
    business_id: BusinessId,
    session_key: str,
    address: str,
) -> None:
    refuse_too_frequent_widget_requests(
        registry,
        WIDGET_POLL_LIMITS,
        business_id=business_id,
        session_key=WidgetSessionKey(session_key),
        client_ip_address=ClientIpAddress(address),
        now=NOW,
    )


def test_one_visitor_is_held_to_its_limit_across_processes() -> None:
    registries = processes(InMemoryRateLimitBucketAdapter())
    business_id = BusinessId()
    limit = WIDGET_POLL_LIMITS.per_visitor_per_minute

    for index in range(limit):
        poll(
            registries[index % PROCESSES],
            business_id,
            "visitor_000000000001",
            "10.0.0.1",
        )

    for registry in registries:
        with pytest.raises(RateLimitedError):
            poll(
                registry,
                business_id,
                "visitor_000000000001",
                f"10.0.1.{len(registries)}",
            )
    # Another visitor of the same network still polls.
    poll(registries[0], business_id, "visitor_000000000002", "10.0.0.1")


def test_one_network_is_held_to_its_limit_across_processes() -> None:
    registries = processes(InMemoryRateLimitBucketAdapter())
    business_id = BusinessId()
    limit = WIDGET_POLL_LIMITS.per_address_per_minute

    for index in range(limit):
        poll(
            registries[index % PROCESSES],
            business_id,
            f"visitor_{index:012d}",
            "203.0.113.7",
        )

    for registry in registries:
        with pytest.raises(RateLimitedError):
            poll(registry, BusinessId(), "visitor_new_000000001", "203.0.113.7")


def test_one_business_never_passes_its_limit_across_processes() -> None:
    buckets = CountingBuckets()
    registries = processes(buckets)
    business_id = BusinessId()
    limit = WIDGET_POLL_LIMITS.per_business_per_minute
    lease = int(WIDGET_POLL_LIMITS.business_lease_size or 1)
    admitted: int = 0

    for index in range(limit + 1):
        try:
            poll(
                registries[index % PROCESSES],
                business_id,
                f"visitor_{index:012d}",
                f"10.{index // 250 // 250}.{index // 250 % 250}.{index % 250}",
            )
        except RateLimitedError:
            break
        admitted += 1

    # Never more than the limit; less by at most what processes hold (what
    # was left of a lease when it was topped up ahead, and the new one).
    assert limit - PROCESSES * (lease + lease // 5) < admitted <= limit
    # Per poll one count of the visitor and network; per lease one statement
    # on the business's row (and fewer on the platform's).
    assert buckets.counts == admitted
    assert buckets.leases <= 2 * (admitted // lease + 2 * PROCESSES)
    # Every process refuses now, whichever of its counters it asks.
    for registry in registries:
        with pytest.raises(RateLimitedError):
            poll(registry, business_id, "visitor_late_00000001", "198.51.100.9")


def test_a_poll_refused_by_its_visitor_gives_its_leased_units_back() -> None:
    buckets = CountingBuckets()
    registry = RequestRateLimitRegistry(buckets)
    business_id = BusinessId()
    for _ in range(WIDGET_POLL_LIMITS.per_visitor_per_minute):
        poll(registry, business_id, "visitor_000000000001", "10.0.0.1")
    leases_before_refusals = buckets.leases

    for _ in range(200):
        with pytest.raises(RateLimitedError):
            poll(registry, business_id, "visitor_000000000001", "10.0.0.1")

    # Every refusal took a unit and gave it back: the leases never ran low
    # enough for another top-up.
    assert buckets.leases == leases_before_refusals
