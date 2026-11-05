"""
Rate limits of the public export feeds (/v1/public/ical/{token}.ics). A
calendar fetches a feed every few hours at most; the limits stop anyone
from guessing tokens or flooding the platform: per client network and for
the platform, in sliding windows of a minute (HTTP 429).
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import (
    describe_client_network,
    refuse_over_limits,
)

KEY_PREFIX: str = "ical-export"
PER_ADDRESS_PER_MINUTE: int = 60
PER_PLATFORM_PER_MINUTE: int = 20_000
REFUSAL: str = "Too many calendar requests; try again in a minute."


def refuse_too_frequent_feed_reads(
    rate_limits: RequestRateLimitRegistryContract,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Raises:
        RateLimitedError: one of the limits is used up (with Retry-After).
    """

    counters: list[RateLimitCounter] = []
    if client_ip_address is not None:
        counters.append(
            RateLimitCounter(
                key=RateLimitKey(
                    f"{KEY_PREFIX}:address:{describe_client_network(client_ip_address)}"
                ),
                limit=RequestsPerWindow(PER_ADDRESS_PER_MINUTE),
            )
        )
    counters.append(
        RateLimitCounter(
            key=RateLimitKey(f"{KEY_PREFIX}:platform"),
            limit=RequestsPerWindow(PER_PLATFORM_PER_MINUTE),
        )
    )
    refuse_over_limits(rate_limits, counters, REFUSAL, now)
