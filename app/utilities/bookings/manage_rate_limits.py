"""
Rate limits of a guest's manage page (/r/{token}). Its routes are public:
the token proves the link, but the page must not become a free way to
query a business's calendar or to flood its staff with changes. Each kind
of request is limited per link, per client network and for the platform,
in sliding windows of a minute (`refuse_over_limits`, HTTP 429).
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import (
    describe_client_network,
    refuse_over_limits,
)


@dataclass(frozen=True)
class ManageRateLimits:
    """Requests of one kind per minute, and the English text of a refusal."""

    key_prefix: str
    per_booking_per_minute: int
    per_address_per_minute: int
    per_platform_per_minute: int
    refusal: str


# Opening the page or its calendar file: a guest reloads now and then.
MANAGE_VIEW_LIMITS: ManageRateLimits = ManageRateLimits(
    key_prefix="booking-manage-view",
    per_booking_per_minute=60,
    per_address_per_minute=240,
    per_platform_per_minute=30_000,
    refusal="Too many requests; try again in a minute.",
)
# The free times of a day: each date the guest picks is one request.
MANAGE_SLOT_LIMITS: ManageRateLimits = ManageRateLimits(
    key_prefix="booking-manage-slots",
    per_booking_per_minute=30,
    per_address_per_minute=120,
    per_platform_per_minute=10_000,
    refusal="Too many requests for free times; try again in a minute.",
)
# A cancellation or a move notifies staff: a few a minute at most.
MANAGE_CHANGE_LIMITS: ManageRateLimits = ManageRateLimits(
    key_prefix="booking-manage-change",
    per_booking_per_minute=5,
    per_address_per_minute=20,
    per_platform_per_minute=2_000,
    refusal="Too many changes; wait a moment and try again.",
)


def refuse_too_frequent_manage_requests(
    rate_limit_registry: RequestRateLimitRegistryContract,
    limits: ManageRateLimits,
    booking_id: BookingId,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count the request for its booking, its network (when known) and the
    platform, or for none of them.

    Raises:
        RateLimitedError: one of the limits is used up (with Retry-After).
    """

    counters: list[RateLimitCounter] = [
        RateLimitCounter(
            key=RateLimitKey(f"{limits.key_prefix}:booking:{booking_id}"),
            limit=RequestsPerWindow(limits.per_booking_per_minute),
        )
    ]
    if client_ip_address is not None:
        counters.append(
            RateLimitCounter(
                key=RateLimitKey(
                    f"{limits.key_prefix}:address:"
                    f"{describe_client_network(client_ip_address)}"
                ),
                limit=RequestsPerWindow(limits.per_address_per_minute),
            )
        )
    counters.append(
        RateLimitCounter(
            key=RateLimitKey(f"{limits.key_prefix}:platform"),
            limit=RequestsPerWindow(limits.per_platform_per_minute),
        )
    )
    refuse_over_limits(rate_limit_registry, counters, limits.refusal, now)
