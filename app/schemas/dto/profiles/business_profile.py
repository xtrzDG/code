"""The business profile: its view, the answers and inputs it is saved from."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    OpeningInterval,
    ProfileAnswer,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.booleans import IsRecordingNoticeEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.booleans import IsProfileSaved
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    RawProfileAnswerText,
    ToneText,
)
from app.schemas.typings.users.prefixed_id import UserId


class BusinessProfileQuery(ImmutableDTO):
    """Read the profile of a business."""

    business_id: BusinessId


class BusinessProfileView(ImmutableDTO):
    """
    The business profile (concept section 3) without the knowledge base.

    Before the first save the view is a blank profile with `is_saved` False.
    Phone numbers are stored in E.164 only.
    """

    business_id: BusinessId
    niche_key: NicheKey
    answers_language: LanguageTag
    address: BusinessAddress | None = None
    hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    contacts: BusinessContacts
    booking_rules: BookingRules | None = None
    handoff_rules: list[HandoffRuleText] = Field(default_factory=list[HandoffRuleText])
    forbidden: list[ForbiddenRuleText] = Field(default_factory=list[ForbiddenRuleText])
    tone: ToneText | None = None
    links: list[BusinessLink] = Field(default_factory=list[BusinessLink])
    niche_answers: list[ProfileAnswer] = Field(default_factory=list[ProfileAnswer])
    is_recording_notice_enabled: IsRecordingNoticeEnabled
    is_saved: IsProfileSaved
    updated_at: Microseconds | None = None


class ProfileAnswerInput(ImmutableDTO):
    """
    Answer to one niche question.

    Text, number, URL and phone questions use `answer`; choice questions use
    `choice_keys` (YES_NO accepts "yes"/"no" in either field). An empty
    answer clears the question.
    """

    question_key: QuestionKey
    answer: RawProfileAnswerText | None = None
    choice_keys: list[QuestionChoiceKey] = Field(
        default_factory=list[QuestionChoiceKey]
    )


class ContactsInput(ImmutableDTO):
    """Phones typed in any national or international format."""

    public_phone_number: RawPhoneNumberInput | None = None
    handoff_phone_number: RawPhoneNumberInput | None = None


class BookingRulesInput(ImmutableDTO):
    """
    Booking rules (concept profile `booking`).

    `resource_kind` defaults to the niche. `slot_minutes` defaults to one day
    for night bookings and to an hour otherwise. The deposit is in minor
    units of the business currency; zero means no deposit.
    """

    resource_kind: ResourceKind | None = None
    slot_minutes: SlotDurationMinutes | None = None
    max_party_size: PartySize
    min_notice_minutes: MinNoticeMinutes = MinNoticeMinutes(0)
    deposit_minor: MoneyAmountMinor | None = None
    deposit_currency_code: CurrencyCode | None = None
    cancellation_policy: CancellationPolicyText | None = None


class FaqEntryInput(ImmutableDTO):
    """A frequent question and its answer; stored as a FAQ knowledge item."""

    id: KnowledgeItemId | None = None
    question: KnowledgeTitle
    answer: KnowledgeBody
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])


class ProfileInput(ImmutableDTO):
    """
    The whole profile without the knowledge base (PUT replaces everything).

    Offer items and FAQ are managed in the knowledge base.
    """

    answers_language: LanguageTag | None = None
    address: BusinessAddress | None = None
    hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    contacts: ContactsInput = Field(default_factory=ContactsInput)
    booking_rules: BookingRulesInput | None = None
    handoff_rules: list[HandoffRuleText] = Field(default_factory=list[HandoffRuleText])
    forbidden: list[ForbiddenRuleText] = Field(default_factory=list[ForbiddenRuleText])
    tone: ToneText | None = None
    links: list[BusinessLink] = Field(default_factory=list[BusinessLink])
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])
    is_recording_notice_enabled: IsRecordingNoticeEnabled = True


class SaveProfileCommand(ImmutableDTO):
    """Replace the profile of a business."""

    business_id: BusinessId
    actor_id: UserId
    profile: ProfileInput
