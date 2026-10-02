"""Starter answers as an owner sees them, and applying them to the profile."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.setup import StarterSection, StarterSectionState
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.dto.profiles.business_profile import (
    BookingRulesInput,
    BusinessProfileView,
)
from app.schemas.dto.resources import ResourceView
from app.schemas.typings.bookings.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)
from app.schemas.typings.setup.booleans import IsStarterAnswerReady
from app.schemas.typings.setup.constrained_strings import StarterEntryKey
from app.schemas.typings.users.prefixed_id import UserId


class StarterAnswersQuery(ImmutableDTO):
    """Read the starter answers of a business in a language (owner's by default)."""

    user_id: UserId
    business_id: BusinessId
    language: LanguageTag | None = None


class StarterSectionView(ImmutableDTO):
    """Whether applying would fill a profile section or leave the owner's data."""

    section: StarterSection
    state: StarterSectionState


class StarterFaqView(ImmutableDTO):
    """
    A frequent question of the niche. `is_ready` is True when it comes with
    an answer that holds for any business of the niche; otherwise the owner
    writes the answer (applying the suggestions skips it).
    """

    key: StarterEntryKey
    question: KnowledgeTitle
    answer: KnowledgeBody | None = None
    is_ready: IsStarterAnswerReady


class StarterOfferView(ImmutableDTO):
    """
    An example of what such a business sells, to prefill the offer table.
    It never carries a price: the owner adds the price, and until then the
    profile keeps asking for prices.
    """

    key: StarterEntryKey
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    duration_minutes: ServiceDurationMinutes | None = None


class StarterResourceView(ImmutableDTO):
    """The first bookable thing the niche suggests, in the owner's language."""

    kind: ResourceKind
    booking_unit: BookingUnit
    name: ResourceName
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount
    slot_minutes: SlotDurationMinutes | None = None


class StarterAnswersView(ImmutableDTO):
    """
    Suggestions for a new business, clearly not its facts yet: typical
    hours over the country's working week, booking rules and a first
    resource (niches that take bookings), handoff and forbidden rules, a
    tone, frequent questions and offer examples. `sections` tells which
    profile sections are still empty (SUGGESTED) and which the owner has
    already filled (ALREADY_SET, applying leaves them).
    """

    business_id: BusinessId
    niche_key: NicheKey
    language: LanguageTag
    sections: list[StarterSectionView]
    hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    booking_rules: BookingRulesInput | None = None
    resource: StarterResourceView | None = None
    handoff_rules: list[HandoffRuleText] = Field(default_factory=list[HandoffRuleText])
    forbidden_rules: list[ForbiddenRuleText] = Field(
        default_factory=list[ForbiddenRuleText]
    )
    tone: ToneText | None = None
    faq: list[StarterFaqView] = Field(default_factory=list[StarterFaqView])
    offer_examples: list[StarterOfferView] = Field(
        default_factory=list[StarterOfferView]
    )


class ApplyStarterAnswersRequest(ImmutableDTO):
    """
    Accept starter answers in one call.

    `sections` defaults to every section; `faq_keys` (default: every
    question with a ready answer) narrows the questions taken. Sections the
    owner has already filled are never overwritten. `language` is the
    language the texts are written in (the owner's by default).

    Example: {"sections": ["hours", "booking_rules", "faq"]}.
    """

    sections: list[StarterSection] | None = None
    faq_keys: list[StarterEntryKey] | None = None
    language: LanguageTag | None = None


class ApplyStarterAnswersCommand(ImmutableDTO):
    """The owner accepts starter answers for their business."""

    user_id: UserId
    business_id: BusinessId
    request: ApplyStarterAnswersRequest


class StarterAnswersApplied(ImmutableDTO):
    """
    What applying changed: the sections filled, the ones left as the owner
    had them, the profile, the frequent questions saved and the resource
    created.
    """

    applied_sections: list[StarterSection] = Field(
        default_factory=list[StarterSection]
    )
    kept_sections: list[StarterSection] = Field(default_factory=list[StarterSection])
    profile: BusinessProfileView
    saved_knowledge_items: list[KnowledgeItemDetails] = Field(
        default_factory=list[KnowledgeItemDetails]
    )
    resource: ResourceView | None = None
