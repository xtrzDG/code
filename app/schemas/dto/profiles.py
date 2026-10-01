"""Niche catalog, the six-step profile wizard and the "what to add" list.

Display texts (labels, hints, titles) are resolved to one language for the
caller: requested tag, then its base language, then English.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import (
    LaunchWave,
    NicheKey,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    OpeningInterval,
    ProfileAnswer,
)
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemDetails,
    KnowledgeItemUpsertInput,
)
from app.schemas.typings.assistants.strings import GapDescription
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.booleans import IsRecordingNoticeEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.constrained_integers import (
    QuestionOccurrenceCount,
)
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    LocalizedTextValue,
    RawPhoneNumberInput,
)
from app.schemas.typings.niches.booleans import (
    IsQuestionRequired,
    RequiresLegalReview,
    TakesBookings,
)
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.profiles.booleans import (
    IsProfileGapBlocking,
    IsProfileReady,
    IsProfileSaved,
    IsWizardStepComplete,
)
from app.schemas.typings.profiles.constrained_integers import WizardStepNumber
from app.schemas.typings.profiles.constrained_strings import (
    FactKey,
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    ProfileAnswerText,
    RawProfileAnswerText,
    ToneText,
)
from app.schemas.typings.users.prefixed_id import UserId

# --- Niche catalog -----------------------------------------------------------


class NicheCatalogQuery(ImmutableDTO):
    """List the niches with texts in `language` (English when None)."""

    language: LanguageTag | None = None


class NicheTemplateQuery(ImmutableDTO):
    """One niche with its questions in `language` (English when None)."""

    niche_key: NicheKey
    language: LanguageTag | None = None


class LocalizedChoiceView(ImmutableDTO):
    """A predefined answer with its label in one language."""

    key: QuestionChoiceKey
    label: LocalizedTextValue


class LocalizedQuestionView(ImmutableDTO):
    """A niche question with its texts in one language."""

    key: QuestionKey
    fact_key: FactKey
    step: ProfileWizardStep
    answer_type: QuestionAnswerType
    is_required: IsQuestionRequired
    label: LocalizedTextValue
    hint: LocalizedTextValue | None = None
    choices: list[LocalizedChoiceView] = Field(
        default_factory=list[LocalizedChoiceView]
    )


class NicheSummaryView(ImmutableDTO):
    """What a niche is and what it books, in one language."""

    key: NicheKey
    wave: LaunchWave
    name: LocalizedTextValue
    description: LocalizedTextValue
    recommended_plans: list[PlanKey]
    resource_kind: ResourceKind
    booking_unit: BookingUnit
    takes_bookings: TakesBookings
    resource_noun: LocalizedTextValue
    requires_legal_review: RequiresLegalReview
    integrations: list[IntegrationName] = Field(default_factory=list[IntegrationName])


class NicheCatalogView(ImmutableDTO):
    """Every niche the platform supports."""

    language: LanguageTag
    niches: list[NicheSummaryView]


class NicheDetailsView(ImmutableDTO):
    """
    A niche with everything the owner sees before signing up.

    Default handoff and forbidden rules pre-fill the profile; prompt rules
    stay internal to assistant assembly.
    """

    language: LanguageTag
    niche: NicheSummaryView
    knowledge_kinds: list[KnowledgeItemKind]
    questions: list[LocalizedQuestionView]
    default_handoff_rules: list[HandoffRuleText]
    default_forbidden_rules: list[ForbiddenRuleText]
    autotest_kinds: list[AutotestScenarioKind]


# --- Business profile ---------------------------------------------------------


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


class NicheAndLanguagesStepInput(ImmutableDTO):
    """
    Step 1: the language the owner answers in and the niche's first questions.

    The niche and the customer languages are business settings and are
    changed there; this step shows them and asks the niche questions.
    """

    answers_language: LanguageTag | None = None
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])


class ContactsAndHoursStepInput(ImmutableDTO):
    """
    Step 2: address with a maps link, phones and opening hours.

    Hours are local minutes of the day; 1440 closes at midnight, and an
    overnight opening is two intervals (until 1440, then from 0 next day).
    """

    address: BusinessAddress | None = None
    hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    contacts: ContactsInput = Field(default_factory=ContactsInput)
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])


class OfferStepInput(ImmutableDTO):
    """
    Step 3: what the business sells, with prices in its currency.

    Items are upserted into the knowledge base; items left out are kept
    (remove them in the knowledge base).
    """

    items: list[KnowledgeItemUpsertInput] = Field(
        default_factory=list[KnowledgeItemUpsertInput]
    )
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])


class BookingRulesStepInput(ImmutableDTO):
    """Step 4: booking rules; None for niches that take no bookings."""

    booking_rules: BookingRulesInput | None = None
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])


class FaqAndHandoffStepInput(ImmutableDTO):
    """
    Step 5: frequent questions, handoff rules, forbidden topics and tone.

    FAQ entries are upserted into the knowledge base as FAQ items.
    """

    faq: list[FaqEntryInput] = Field(default_factory=list[FaqEntryInput])
    handoff_rules: list[HandoffRuleText] = Field(default_factory=list[HandoffRuleText])
    forbidden: list[ForbiddenRuleText] = Field(default_factory=list[ForbiddenRuleText])
    tone: ToneText | None = None
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])


class ChannelsStepInput(ImmutableDTO):
    """
    Step 6: links the assistant may send and the call recording notice.

    Channels themselves are connected in the channels section.
    """

    links: list[BusinessLink] = Field(default_factory=list[BusinessLink])
    is_recording_notice_enabled: IsRecordingNoticeEnabled = True
    answers: list[ProfileAnswerInput] = Field(default_factory=list[ProfileAnswerInput])


type ProfileStepInput = (
    NicheAndLanguagesStepInput
    | ContactsAndHoursStepInput
    | OfferStepInput
    | BookingRulesStepInput
    | FaqAndHandoffStepInput
    | ChannelsStepInput
)


class SaveProfileStepCommand(ImmutableDTO):
    """
    Save one wizard step; other steps keep their data (partial progress).

    `actor_id` is the signed-in user, recorded when contact phones change.
    """

    business_id: BusinessId
    actor_id: UserId
    step_input: ProfileStepInput


class ProfileStepSaveResult(ImmutableDTO):
    """The saved profile and the knowledge items the step created or updated."""

    step: ProfileWizardStep
    profile: BusinessProfileView
    saved_knowledge_items: list[KnowledgeItemDetails] = Field(
        default_factory=list[KnowledgeItemDetails]
    )


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


# --- Wizard ------------------------------------------------------------------


class ProfileWizardQuery(ImmutableDTO):
    """The wizard of a business in `language` (owner language when None)."""

    business_id: BusinessId
    language: LanguageTag | None = None


class WizardQuestionView(ImmutableDTO):
    """A niche question with the current answer."""

    question: LocalizedQuestionView
    answer: ProfileAnswerText | None = None
    selected_choice_keys: list[QuestionChoiceKey] = Field(
        default_factory=list[QuestionChoiceKey]
    )


class WizardStepView(ImmutableDTO):
    """
    One of the six wizard steps.

    `is_complete` means nothing required is missing in this step.
    """

    step: ProfileWizardStep
    number: WizardStepNumber
    title: LocalizedTextValue
    description: LocalizedTextValue
    questions: list[WizardQuestionView] = Field(
        default_factory=list[WizardQuestionView]
    )
    is_complete: IsWizardStepComplete


class ProfileWizardView(ImmutableDTO):
    """
    The six-step wizard (concept section 3) for one business.

    Country-dependent values (currency, time zone, customer languages) come
    from the business, so the same wizard works in any country.
    """

    business_id: BusinessId
    language: LanguageTag
    niche: NicheSummaryView
    country_code: CountryCode
    currency_code: CurrencyCode
    timezone: TimezoneName
    customer_languages: list[LanguageTag]
    default_language: LanguageTag
    knowledge_kinds: list[KnowledgeItemKind]
    default_handoff_rules: list[HandoffRuleText]
    default_forbidden_rules: list[ForbiddenRuleText]
    steps: list[WizardStepView]
    profile: BusinessProfileView


# --- What to add ---------------------------------------------------------------


class ProfileGapsQuery(ImmutableDTO):
    """The "what to add" list in `language` (owner language when None)."""

    business_id: BusinessId
    language: LanguageTag | None = None


class ProfileGapFinding(ImmutableDTO):
    """A gap found in the profile data, before it is worded for the owner."""

    kind: ProfileGapKind
    step: ProfileWizardStep
    is_blocking: IsProfileGapBlocking
    question_key: QuestionKey | None = None


class ProfileGap(ImmutableDTO):
    """
    One item of the "what to add" list.

    Blocking gaps stop the assistant from being assembled; the others make it
    answer better.
    """

    kind: ProfileGapKind
    step: ProfileWizardStep
    is_blocking: IsProfileGapBlocking
    description: GapDescription
    question_key: QuestionKey | None = None
    unanswered_question_id: UnansweredQuestionId | None = None
    unanswered_question: UnansweredQuestionText | None = None
    occurrence_count: QuestionOccurrenceCount | None = None


class ProfileGapsView(ImmutableDTO):
    """Blocking gaps first, then advice, then customers' unanswered questions."""

    business_id: BusinessId
    language: LanguageTag
    gaps: list[ProfileGap] = Field(default_factory=list[ProfileGap])
    is_ready_for_assembly: IsProfileReady
