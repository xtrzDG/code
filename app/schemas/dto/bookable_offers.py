"""
Bookable offers (services, packages, room types): what a booking of one
takes and costs, as the booking use cases and the model tools see it.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    BookingValueMinor,
    NightCount,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    NightlyRateMinor,
    ServiceDurationMinutes,
    StayPriceMinor,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle, SeasonName
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class StayNightPrice(ImmutableDTO):
    """The rate of one night of a stay (the night that starts on `date`)."""

    date: LocalDate
    nightly_rate_minor: NightlyRateMinor
    season_name: SeasonName | None = None


class StayQuote(ImmutableDTO):
    """
    What a stay in a room type costs: every night at the rate of its season
    (or the item's price outside the seasons), summed.
    """

    item_id: KnowledgeItemId
    item_title: KnowledgeTitle
    check_in: LocalDate
    check_out: LocalDate
    nights: NightCount
    currency_code: CurrencyCode
    total_minor: StayPriceMinor
    night_prices: list[StayNightPrice] = Field(default_factory=list[StayNightPrice])


class BookingPrice(ImmutableDTO):
    """What one booking is worth, in the currency of its offer."""

    value_minor: BookingValueMinor
    currency_code: CurrencyCode


class OfferPerformer(ImmutableDTO):
    """A resource that performs or provides an offer."""

    resource_id: ResourceId
    resource_name: ResourceName


class BookableOfferView(ImmutableDTO):
    """
    One bookable offer as the model tools list it: how long a booking of it
    lasts (with the time its performer stays blocked after it), its price
    and who performs it.
    """

    id: KnowledgeItemId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    duration_minutes: ServiceDurationMinutes | None = None
    buffer_minutes: BufferMinutes | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    performers: list[OfferPerformer] = Field(default_factory=list[OfferPerformer])
