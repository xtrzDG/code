"""
The starter answers of a niche as the registry keeps them: typical hours,
booking rules, a first resource, tone, frequent questions and offer
examples, in every owner language. None of them is a fact of a business
until its owner accepts it.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.setup.constrained_strings import StarterEntryKey


class StarterOpening(ImmutableDTO):
    """
    Typical opening hours of a niche: one interval on working days and one
    (or none: closed) on the days that are the weekend in the business's
    country, so a clinic in Israel rests on Friday and Saturday and one in
    Germany on Saturday and Sunday.
    """

    workday_opens_at: OpeningMinuteOfDay
    workday_closes_at: ClosingMinuteOfDay
    weekend_opens_at: OpeningMinuteOfDay | None = None
    weekend_closes_at: ClosingMinuteOfDay | None = None


class StarterBookingDefaults(ImmutableDTO):
    """
    Typical booking rules of a niche that takes bookings. `slot_minutes` is
    None for niches booked by nights. No deposit is ever suggested.
    """

    slot_minutes: SlotDurationMinutes | None = None
    max_party_size: PartySize
    min_notice_minutes: MinNoticeMinutes
    cancellation_policies: LocalizedText


class StarterResourceDefaults(ImmutableDTO):
    """The first bookable thing of a niche ("Table", "Standard room")."""

    names: LocalizedText
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount


class StarterFaqDefinition(ImmutableDTO):
    """
    A question customers of the niche often ask. `answers` is a ready
    answer that holds for any business of the niche; None when only the
    owner can answer it (the cabinet then asks for the answer).
    """

    key: StarterEntryKey
    questions: LocalizedText
    answers: LocalizedText | None = None


class StarterOfferDefinition(ImmutableDTO):
    """An example of what the niche sells; never priced (prices come from owners)."""

    key: StarterEntryKey
    kind: KnowledgeItemKind
    titles: LocalizedText
    duration_minutes: ServiceDurationMinutes | None = None


class NicheStarterDefinition(ImmutableDTO):
    """Everything a niche suggests to a new owner."""

    niche_key: NicheKey
    opening: StarterOpening
    booking: StarterBookingDefaults | None = None
    resource: StarterResourceDefaults | None = None
    tones: LocalizedText
    faq: list[StarterFaqDefinition] = Field(default_factory=list[StarterFaqDefinition])
    offers: list[StarterOfferDefinition] = Field(
        default_factory=list[StarterOfferDefinition]
    )


class StarterAnswers(ImmutableDTO):
    """
    The starter answers of a niche for a business's country: the opening
    hours are concrete intervals over the country's working week.
    """

    niche_key: NicheKey
    hours: list[OpeningInterval]
    booking: StarterBookingDefaults | None = None
    resource: StarterResourceDefaults | None = None
    tones: LocalizedText
    faq: list[StarterFaqDefinition] = Field(default_factory=list[StarterFaqDefinition])
    offers: list[StarterOfferDefinition] = Field(
        default_factory=list[StarterOfferDefinition]
    )
