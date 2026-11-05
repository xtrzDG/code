"""
Widget messages are model calls: a script choosing new session keys and
rotating addresses of one network is still limited per network, per
business and for the platform, and a refused request leaves no state.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.utilities.channels.widget_rate_limits import (
    WIDGET_MESSAGE_LIMITS,
    describe_client_network,
    refuse_too_frequent_widget_requests,
)

NOW: Microseconds = Microseconds(1_790_000_000_000_000)


def send(
    registry: RequestRateLimitRegistry,
    business_id: BusinessId,
    session_key: str,
    address: str,
) -> None:
    refuse_too_frequent_widget_requests(
        registry,
        WIDGET_MESSAGE_LIMITS,
        business_id=business_id,
        session_key=WidgetSessionKey(session_key),
        client_ip_address=ClientIpAddress(address),
        now=NOW,
    )


def test_addresses_of_one_ipv6_network_share_the_limit() -> None:
    registry = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
    business_id = BusinessId()
    limit = WIDGET_MESSAGE_LIMITS.per_address_per_minute

    for index in range(limit):
        send(registry, business_id, f"visitor_{index:012d}", f"2001:db8:1:2::{index:x}")

    with pytest.raises(RateLimitedError):
        send(registry, business_id, "visitor_one_more_0001", "2001:db8:1:2:ffff::1")
    # Another /64 is another network.
    send(registry, business_id, "visitor_elsewhere_001", "2001:db8:1:3::1")


def test_one_business_is_limited_across_networks() -> None:
    registry = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
    business_id = BusinessId()
    limit = WIDGET_MESSAGE_LIMITS.per_business_per_minute

    for index in range(limit):
        send(
            registry,
            business_id,
            f"visitor_{index:012d}",
            f"198.51.{index // 250}.{index % 250}",
        )

    with pytest.raises(RateLimitedError) as refusal:
        send(registry, business_id, "visitor_one_more_0001", "203.0.113.200")
    # NOW is 20 s into a one-minute window: the next window starts in 40 s,
    # and half a second into it this window's weight leaves room for one.
    assert refusal.value.retry_after_seconds == 41
    # The same network still reaches another business.
    send(registry, BusinessId(), "visitor_one_more_0001", "203.0.113.200")


def test_the_platform_is_limited_across_businesses() -> None:
    registry = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
    limit = WIDGET_MESSAGE_LIMITS.per_platform_per_minute

    for index in range(limit):
        send(
            registry,
            BusinessId(),
            f"visitor_{index:012d}",
            f"10.{index // 250 // 250}.{index // 250 % 250}.{index % 250}",
        )

    with pytest.raises(RateLimitedError):
        send(registry, BusinessId(), "visitor_one_more_0001", "203.0.113.200")


def test_a_refused_request_counts_against_no_limit() -> None:
    buckets = InMemoryRateLimitBucketAdapter()
    registry = RequestRateLimitRegistry(buckets)
    business_id = BusinessId()
    for index in range(WIDGET_MESSAGE_LIMITS.per_address_per_minute):
        send(registry, business_id, f"visitor_{index:012d}", "203.0.113.7")
    buckets_before = dict(buckets._buckets)  # pyright: ignore[reportPrivateUsage]

    with pytest.raises(RateLimitedError):
        send(registry, business_id, "visitor_new_000000001", "203.0.113.7")

    assert buckets._buckets == buckets_before  # pyright: ignore[reportPrivateUsage]
    # The refused visitor used none of its own limit.
    for _ in range(WIDGET_MESSAGE_LIMITS.per_visitor_per_minute):
        send(registry, business_id, "visitor_new_000000001", "198.51.100.1")


@pytest.mark.parametrize(
    ("address", "network"),
    [
        ("2001:db8:1:2:aaaa::5", "2001:db8:1:2::/64"),
        ("::ffff:203.0.113.7", "203.0.113.7"),
        ("203.0.113.7", "203.0.113.7"),
        ("testclient", "testclient"),
    ],
)
def test_the_network_of_an_address(address: str, network: str) -> None:
    assert describe_client_network(ClientIpAddress(address)) == network
