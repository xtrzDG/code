"""
What a booking is worth.

A stay of a room type is worth its nights at their seasonal rates; a
booking of a service or package is worth the item's price (per booking).
A booking without a priced offer has no value: the value model then counts
it at the average check. A room booked without naming its type is valued
by the room type the room belongs to.
"""

from collections.abc import Sequence
from datetime import date

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookable_offers import BookingPrice, StayQuote
from app.schemas.typings.bookings.constrained_integers import (
    BookingValueMinor,
    NightCount,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.bookings.bookable_offers import is_bookable_item
from app.utilities.bookings.stay_quotes import quote_stay
from app.utilities.scheduling.booking_placement import DEFAULT_NIGHT_COUNT


def offer_of_booking(
    service: KnowledgeItemDocument | None,
    resource: ResourceDocument,
    items: Sequence[KnowledgeItemDocument],
) -> KnowledgeItemDocument | None:
    """The booked offer: the one asked for, else the room's room type."""

    if service is not None or resource.room_type_item_id is None:
        return service

    for item in items:
        if item.id == resource.room_type_item_id and is_bookable_item(item):
            return item

    return None


def price_booking(
    offer: KnowledgeItemDocument | None,
    booking_unit: BookingUnit,
    check_in: date,
    nights: NightCount | None,
    business_currency_code: CurrencyCode,
) -> BookingPrice | None:
    """
    The value of a booking of `offer` (see the module); None without a
    price. A stay is priced for its `nights` (one when not given).
    """

    if offer is None:
        return None

    if booking_unit is BookingUnit.NIGHT:
        quote: StayQuote | None = quote_stay(
            offer,
            check_in,
            NightCount(DEFAULT_NIGHT_COUNT) if nights is None else nights,
            business_currency_code,
        )
        if quote is None:
            return None

        return BookingPrice(
            value_minor=BookingValueMinor(int(quote.total_minor)),
            currency_code=quote.currency_code,
        )

    if offer.price_minor is None:
        return None

    return BookingPrice(
        value_minor=BookingValueMinor(int(offer.price_minor)),
        currency_code=offer.currency_code or business_currency_code,
    )
