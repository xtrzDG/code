"""Inputs of the six steps of the profile wizard and saving one step."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.domain.profiles import BusinessAddress, BusinessLink, OpeningInterval
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemDetails,
    KnowledgeItemUpsertInput,
)
from app.schemas.dto.profiles.business_profile import (
    BookingRulesInput,
    BusinessProfileView,
    ContactsInput,
    FaqEntryInput,
    ProfileAnswerInput,
)
from app.schemas.typings.businesses.booleans import IsRecordingNoticeEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)
from app.schemas.typings.users.prefixed_id import UserId


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
