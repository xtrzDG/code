"""
Rate limits of the website widget's error beacon (POST /v1/widget/errors).
Anyone can call it, so reports are limited per client network (an IPv4
address or an IPv6 /64), per business and for the whole platform, in
sliding windows of a minute: a broken page cannot flood the error reports,
and a script cannot either.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import (
    describe_client_network,
    refuse_over_limits,
)

KEY_PREFIX: str = "widget-error"
# A page load reports a few errors at most (the widget sends at most three).
PER_ADDRESS_PER_MINUTE: int = 10
PER_BUSINESS_PER_MINUTE: int = 120
PER_PLATFORM_PER_MINUTE: int = 600
REFUSAL: str = "Too many error reports; the rest are dropped for a minute."


def refuse_too_many_error_reports(
    rate_limit_registry: RequestRateLimitRegistryContract,
    business_id: BusinessId | None,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count one report for its network, its business and the platform, or for
    none of them.

    Raises:
        RateLimitedError: one of the limits is used up (HTTP 429).
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
    if business_id is not None:
        counters.append(
            RateLimitCounter(
                key=RateLimitKey(f"{KEY_PREFIX}:business:{business_id}"),
                limit=RequestsPerWindow(PER_BUSINESS_PER_MINUTE),
            )
        )
    counters.append(
        RateLimitCounter(
            key=RateLimitKey(f"{KEY_PREFIX}:platform"),
            limit=RequestsPerWindow(PER_PLATFORM_PER_MINUTE),
        )
    )
    refuse_over_limits(rate_limit_registry, counters, REFUSAL, now)
