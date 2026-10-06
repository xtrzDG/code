"""
Inputs of the model tools (concept section 5) and their execution.

Tool inputs hold only what the language model may decide. The business,
contact, conversation and channel always come from the server-side
`AssistantToolContext`, never from model output, so a customer cannot reach
another tenant's data by asking (prompt-injection safety).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import LeadType, ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.reply_choices import MAX_CHOICES, MIN_CHOICES, ReplyChoices
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
    ResourceReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import (
    CanTextCaller,
    IsSandboxConversation,
)
from app.schemas.typings.conversations.constrained_strings import (
    ChoiceLabel,
    ChoicePromptText,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.knowledge.strings import (
    KnowledgeSearchQuery,
    KnowledgeTitle,
    ServiceReference,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput


class SearchKnowledgeToolInput(ImmutableDTO):
    """search_knowledge: free-text query; language defaults to the conversation's."""

    query: KnowledgeSearchQuery
    language: LanguageTag | None = None


class GetPriceToolInput(ImmutableDTO):
    """
    get_price: name of a menu item, service, room or package; for a room,
    the check-in date and nights quote the stay at its seasonal rates.
    """

    item_name: KnowledgeTitle
    check_in_date: LocalDate | None = None
    nights: NightCount | None = None


class CheckAvailabilityToolInput(ImmutableDTO):
    """
    check_availability: a local date (and time) in the business time zone;
    a service and a resource by id or by name in any script.
    """

    service_id: ServiceReference | None = None
    resource_id: ResourceReference | None = None
    resource_type: ResourceKind | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    party_size: PartySize | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None


class CreateBookingToolInput(ImmutableDTO):
    """
    create_booking: the confirmed details. A missing phone falls back to the
    phone the customer contacted us from. A service and a resource may be
    named by id or by name in any script.
    """

    name: ContactName
    phone: RawPhoneNumberInput | None = None
    service_id: ServiceReference | None = None
    resource_id: ResourceReference | None = None
    resource_type: ResourceKind | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    party_size: PartySize
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    notes: BookingNote | None = None


class CancelBookingToolInput(ImmutableDTO):
    """cancel_booking: a booking id, or the customer's phone and booking date."""

    booking_id: BookingId | None = None
    phone: RawPhoneNumberInput | None = None
    date: LocalDate | None = None


class RescheduleBookingToolInput(ImmutableDTO):
    """reschedule_booking: the booking (id, or phone and old date) and the new time."""

    booking_id: BookingId | None = None
    phone: RawPhoneNumberInput | None = None
    old_date: LocalDate | None = None
    new_date: LocalDate
    new_time: LocalTimeOfDay | None = None


class ListMyBookingsToolInput(ImmutableDTO):
    """list_my_bookings: no input; the customer comes from the conversation."""


class CreateLeadToolInput(ImmutableDTO):
    """create_lead: a request for a manager (banquet, group, corporate, ...)."""

    lead_type: LeadType
    details: LeadDetails
    name: ContactName | None = None
    phone: RawPhoneNumberInput | None = None
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None


class HandoffToHumanToolInput(ImmutableDTO):
    """handoff_to_human: why, a short summary for staff, and how urgent."""

    reason: HandoffReason
    summary: HandoffSummary
    urgency: HandoffUrgency


class SendLinkToolInput(ImmutableDTO):
    """send_link: which profile link to send."""

    kind: BusinessLinkKind


class RecordUnansweredQuestionToolInput(ImmutableDTO):
    """record_unanswered_question: the customer's question in their words."""

    question: UnansweredQuestionText


class JoinWaitlistToolInput(ImmutableDTO):
    """
    join_waitlist: the date the customer wants and, as far as they said, a
    time window, the party, a stay's nights, the service and the resource
    (by id or by name in any script) and a note.
    """

    name: ContactName | None = None
    service_id: ServiceReference | None = None
    resource_id: ResourceReference | None = None
    resource_type: ResourceKind | None = None
    date: LocalDate
    time_from: LocalTimeOfDay | None = None
    time_to: LocalTimeOfDay | None = None
    party_size: PartySize | None = None
    nights: NightCount | None = None
    notes: BookingNote | None = None


class OfferChoicesToolInput(ImmutableDTO):
    """
    offer_choices: the question shown with the options, and 2 to 10 short
    options the customer can tap (the handler refuses repeated ones).
    """

    prompt_text: ChoicePromptText
    options: list[ChoiceLabel] = Field(min_length=MIN_CHOICES, max_length=MAX_CHOICES)


class AssistantToolContext(ImmutableDTO):
    """
    Server-side facts a tool call runs with.

    `available_tools` are the tools offered in this conversation; a call of
    any other tool is answered with an error result. Phones the model passes
    are parsed with the business country as the hint. `verified_phone_number`
    is the phone the channel proved for this customer (never one the model
    or the customer typed); only it can prove that a booking made under a
    phone belongs to the customer.
    """

    business_id: BusinessId
    business_country_code: CountryCode
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    verified_phone_number: E164PhoneNumber | None = None
    conversation_id: ConversationId
    channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False
    available_tools: list[AssistantToolName]
    # Scheduling results state today in this zone (None: not stated).
    business_timezone: TimezoneName | None = None
    # On the phone: a connected messenger reaches the caller, so the links
    # the agent promises are texted after the call.
    can_text_caller: CanTextCaller = False


class AssistantToolInvocation(ImmutableDTO):
    """One tool call requested by the model (or the voice agent) in a context."""

    context: AssistantToolContext
    call: LlmToolCall


class AssistantToolOutcome(ImmutableDTO):
    """
    Result returned to the model plus what the call created.

    `booking_id` is set only for a new booking, `lead_id` for a new lead and
    `handoff_id` for a new handoff. `confirmed_booking_id` names the booking
    a call made or moved: its guest gets a written confirmation. `choices`
    are the options offer_choices put under the reply.
    """

    tool_name: AssistantToolName
    result: LlmToolResult
    booking_id: BookingId | None = None
    confirmed_booking_id: BookingId | None = None
    lead_id: LeadId | None = None
    handoff_id: HandoffId | None = None
    choices: ReplyChoices | None = None
