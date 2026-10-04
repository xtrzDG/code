"""
Where a moved booking may go and what it is worth there: its own resource
first, then the other performers of its service (or same-kind resources);
a stay is priced again for its new nights.
"""

from collections.abc import Sequence
from datetime import date

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookable_offers import BookingPrice
from app.schemas.typings.bookings.constrained_integers import BookingDurationMinutes
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.bookings.bookable_offers import is_bookable_item, performers_of
from app.utilities.bookings.booking_values import price_booking
from app.utilities.scheduling.resource_selection import seating_resources
from app.utilities.scheduling.zoned_time import SECONDS_PER_MINUTE


def booked_offer(
    booking: BookingDocument,
    items: Sequence[KnowledgeItemDocument],
) -> KnowledgeItemDocument | None:
    """The service the booking books, while it is still offered."""

    if booking.service_item_id is None:
        return None

    for item in items:
        if item.id == booking.service_item_id and is_bookable_item(item):
            return item

    return None


def reschedule_candidates(
    resources: Sequence[ResourceDocument],
    booking: BookingDocument,
    current: ResourceDocument,
    offer: KnowledgeItemDocument | None,
    items: Sequence[KnowledgeItemDocument],
) -> list[ResourceDocument]:
    """
    The booked resource first (if active), then the other performers of
    the booked service, or without one the same-kind alternatives.
    """

    if offer is not None:
        alternatives: list[ResourceDocument] = seating_resources(
            [
                resource
                for resource in performers_of(offer, resources, items)
                if resource.id != current.id
            ],
            booking.party_size,
        )
    else:
        alternatives = seating_resources(
            [
                resource
                for resource in resources
                if resource.is_active
                and resource.id != current.id
                and resource.kind is current.kind
                and resource.booking_unit is current.booking_unit
            ],
            booking.party_size,
        )

    if not current.is_active:
        return alternatives

    return [current, *alternatives]


def booked_length(
    booking: BookingDocument,
    current: ResourceDocument,
) -> BookingDurationMinutes | None:
    """The length a moved time-slot booking keeps (None for stays)."""

    if current.booking_unit is not BookingUnit.TIME_SLOT:
        return None

    return BookingDurationMinutes(
        (int(booking.ends_at) - int(booking.starts_at)) // SECONDS_PER_MINUTE
    )


def reprice_stay(
    booking: BookingDocument,
    offer: KnowledgeItemDocument | None,
    booking_unit: BookingUnit,
    check_in: date,
    nights: int,
    business_currency_code: CurrencyCode,
) -> None:
    """A moved stay costs its new nights at their seasonal rates."""

    if offer is None or booking_unit is not BookingUnit.NIGHT:
        return

    price: BookingPrice | None = price_booking(
        offer, booking_unit, check_in, nights, business_currency_code
    )
    if price is not None:
        booking.value_minor = price.value_minor
        booking.currency_code = price.currency_code
