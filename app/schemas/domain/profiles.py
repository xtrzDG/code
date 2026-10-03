from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.booleans import IsRecordingNoticeEnabled
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    ProfileAnswerText,
    ToneText,
)


class OpeningInterval(PersistentDocument):
    """One opening interval in the business time zone (closing may be 24:00)."""

    weekday: Weekday
    opens_at: OpeningMinuteOfDay
    closes_at: ClosingMinuteOfDay


class BusinessAddress(PersistentDocument):
    """Address text and an optional maps link (concept profile `address`)."""

    text: AddressText
    maps_url: WebLink | None = None


class BusinessContacts(PersistentDocument):
    """Public and handoff phones (concept profile `contacts`)."""

    public_phone_number: E164PhoneNumber | None = None
    handoff_phone_number: E164PhoneNumber | None = None


class BookingRules(PersistentDocument):
    """
    Booking rules (concept profile `booking`).

    The deposit is in the business currency; null means no deposit.
    """

    resource_kind: ResourceKind
    slot_minutes: SlotDurationMinutes
    max_party_size: PartySize
    min_notice_minutes: MinNoticeMinutes = MinNoticeMinutes(0)
    deposit_minor: MoneyAmountMinor | None = None
    deposit_currency_code: CurrencyCode | None = None
    cancellation_policy: CancellationPolicyText | None = None


class BusinessLink(PersistentDocument):
    """A link the assistant may send (menu, map, payment, booking page)."""

    kind: BusinessLinkKind
    url: WebLink


class ProfileAnswer(PersistentDocument):
    """Owner's answer to one niche-specific profile question."""

    question_key: QuestionKey
    answer: ProfileAnswerText


class BusinessProfileDocument(BaseDocument):
    """
    Business profile filled in the six-step wizard (concept section 3).

    Offerings and FAQ live in the knowledge base (`KnowledgeItemDocument`),
    bookable things in `ResourceDocument`; everything else is here.

    Version 2: `privacy_notice_url`, the business's own privacy notice
    (optional, so version 1 rows read as they are). The cabinet and the
    assistant see it as the link of kind `BusinessLinkKind.PRIVACY`; it is
    kept apart from `links` so a release that does not know that kind
    still reads every profile (docs/operations/deploys.md, enum values).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    business_id: BusinessId
    niche_key: NicheKey
    answers_language: LanguageTag
    address: BusinessAddress | None = None
    hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    contacts: BusinessContacts = Field(default_factory=BusinessContacts)
    booking_rules: BookingRules | None = None
    handoff_rules: list[HandoffRuleText] = Field(default_factory=list[HandoffRuleText])
    forbidden: list[ForbiddenRuleText] = Field(default_factory=list[ForbiddenRuleText])
    tone: ToneText | None = None
    links: list[BusinessLink] = Field(default_factory=list[BusinessLink])
    privacy_notice_url: WebLink | None = None
    niche_answers: list[ProfileAnswer] = Field(default_factory=list[ProfileAnswer])
    is_recording_notice_enabled: IsRecordingNoticeEnabled = True
