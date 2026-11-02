"""
How far ahead, and how often, customers may book (the model tools and the
guest's own pages; staff in the cabinet are not limited).

- The horizon: no customer booking, move or free-time search more than
  MAX_BOOKING_HORIZON_DAYS ahead, so nobody fills a calendar years out.
- A contact makes at most MAX_BOOKINGS_PER_CONTACT_PER_DAY bookings a day.
- Bookings without a proven identity (a web chat visitor, a caller id)
  are anonymous: at most MAX_ANONYMOUS_BOOKINGS_PER_NETWORK_PER_DAY from
  one client network, and MAX_ANONYMOUS_BOOKINGS_PER_BUSINESS_PER_DAY for
  the business, so a script cannot flood a calendar with fake bookings.

The daily caps are sliding 24-hour windows of the shared rate-limit
counters, taken only for a booking about to be saved (a taken time costs
nothing); an owner's test (sandbox) counts against none of them.
"""

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import (
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import describe_client_network
from app.utilities.scheduling.zoned_time import to_local_moment

MAX_BOOKING_HORIZON_DAYS: int = 365
MAX_BOOKINGS_PER_CONTACT_PER_DAY: int = 5
MAX_ANONYMOUS_BOOKINGS_PER_NETWORK_PER_DAY: int = 10
MAX_ANONYMOUS_BOOKINGS_PER_BUSINESS_PER_DAY: int = 200
DAY_WINDOW: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)
# Channels where a customer proves no account of their own.
ANONYMOUS_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.WEB_CHAT, ChannelKind.PHONE}
)
HORIZON_MESSAGE: str = (
    f"Bookings open at most {MAX_BOOKING_HORIZON_DAYS} days ahead; ask for an "
    "earlier date or pass the request to a colleague."
)
DAILY_CAP_MESSAGE: str = (
    "Too many bookings were made from here today; pass the request to a "
    "colleague instead."
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomerBooking:
    """A customer booking about to be saved, as the daily caps count it."""

    business_id: BusinessId
    contact_id: ContactId
    source_channel: ChannelKind
    client_ip_address: ClientIpAddress | None = None


def refuse_beyond_horizon(local_date: date, zone: ZoneInfo, now_seconds: int) -> None:
    """
    Raises:
        ValidationFailedError: the date is more than the horizon ahead.
    """

    today: date = to_local_moment(now_seconds, zone).date()
    if (local_date - today).days > MAX_BOOKING_HORIZON_DAYS:
        raise ValidationFailedError(HORIZON_MESSAGE)


def daily_counters(booking: CustomerBooking) -> list[RateLimitCounter]:
    """The contact's counter, and for an anonymous booking its network's and the business's."""

    counters: list[RateLimitCounter] = [
        RateLimitCounter(
            key=RateLimitKey(f"booking-create:contact:{booking.contact_id}"),
            limit=RequestsPerWindow(MAX_BOOKINGS_PER_CONTACT_PER_DAY),
        )
    ]
    if booking.source_channel not in ANONYMOUS_CHANNELS:
        return counters

    if booking.client_ip_address is not None:
        network: str = describe_client_network(booking.client_ip_address)
        counters.append(
            RateLimitCounter(
                key=RateLimitKey(f"booking-create:anonymous:network:{network}"),
                limit=RequestsPerWindow(MAX_ANONYMOUS_BOOKINGS_PER_NETWORK_PER_DAY),
            )
        )

    counters.append(
        RateLimitCounter(
            key=RateLimitKey(f"booking-create:anonymous:business:{booking.business_id}"),
            limit=RequestsPerWindow(MAX_ANONYMOUS_BOOKINGS_PER_BUSINESS_PER_DAY),
        )
    )
    return counters


def count_customer_booking(
    rate_limits: RequestRateLimitRegistryContract,
    booking: CustomerBooking,
    now: Microseconds,
) -> None:
    """
    Count the booking against every daily cap it falls under, or none.

    Raises:
        RateLimitedError: a cap is used up (with the seconds until a place
            frees up).
    """

    counters: list[RateLimitCounter] = daily_counters(booking)
    refused_key: RateLimitKey | None = rate_limits.try_acquire_all(
        counters, DAY_WINDOW, now
    )
    if refused_key is None:
        return

    refused: RateLimitCounter = next(
        counter for counter in counters if counter.key == refused_key
    )
    raise RateLimitedError(
        DAILY_CAP_MESSAGE,
        retry_after_seconds=rate_limits.seconds_until_free(refused, DAY_WINDOW, now),
    )
