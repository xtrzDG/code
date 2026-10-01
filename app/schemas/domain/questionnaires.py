from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import BookableResourceKind, NicheKey
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.questionnaires.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.questionnaires.constrained_strings import QuestionKey
from app.schemas.typings.questionnaires.strings import (
    AnswerText,
    FaqAnswerText,
    FaqQuestionText,
    OfferingDescription,
    OfferingName,
    ResourceName,
)


class QuestionAnswer(PersistentDocument):
    """Owner's answer to one question of the niche questionnaire."""

    question_key: QuestionKey
    answer: AnswerText


class OpeningInterval(PersistentDocument):
    """One opening interval in the business time zone (closing may be 24:00)."""

    weekday: Weekday
    opens_at: OpeningMinuteOfDay
    closes_at: ClosingMinuteOfDay


class OfferingItem(PersistentDocument):
    """Menu item, room type, service, or product with an optional price."""

    name: OfferingName
    description: OfferingDescription | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None


class BookableResource(PersistentDocument):
    """Thing the assistant books: tables, rooms, VR rooms, masters, cars."""

    name: ResourceName
    kind: BookableResourceKind
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount = ResourceUnitCount(1)
    slot_duration_minutes: SlotDurationMinutes


class FaqEntry(PersistentDocument):
    """Frequent question and the owner-approved answer."""

    question: FaqQuestionText
    answer: FaqAnswerText


class QuestionnaireDocument(BaseDocument):
    """
    The business profile filled by the owner (one per business).

    It is the single source of business facts: the assistant answers only from
    what is written here.
    """

    business_id: BusinessId
    niche_key: NicheKey
    answers_language: LanguageTag
    answers: list[QuestionAnswer] = Field(default_factory=list[QuestionAnswer])
    opening_hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    offerings: list[OfferingItem] = Field(default_factory=list[OfferingItem])
    bookable_resources: list[BookableResource] = Field(
        default_factory=list[BookableResource]
    )
    faq_entries: list[FaqEntry] = Field(default_factory=list[FaqEntry])
