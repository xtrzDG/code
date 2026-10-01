"""DTOs of the operations module: cabinet lists and actions for bookings,
leads, handoffs and unanswered questions, the dashboard, Google Calendar,
and the inputs of staff and customer message texts.

Model-tool DTOs (availability, create/cancel/reschedule booking, lead,
handoff, unanswered question) live in `bookings.py` and `handoffs.py`.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import (
    BookingOrder,
    BookingStatus,
    BookingUnit,
    LeadStatus,
    LeadType,
    ResourceKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.bookings import BookingView, LeadView
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.billing.constrained_integers import (
    IncludedDialogs,
    IncludedVoiceMinutes,
    OverageVoiceMinutes,
    PackageUsagePercent,
    UsedDialogs,
)
from app.schemas.typings.billing.constrained_integers import (
    UsedVoiceMinutes as PackageUsedVoiceMinutes,
)
from app.schemas.typings.bookings.booleans import (
    IsSandboxIncluded,
    WasCalendarConnected,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    CalendarTokenLifetimeSeconds,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    CalendarAuthorizationUrl,
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarEventDescription,
    CalendarEventTitle,
    CalendarRefreshToken,
    ExternalCalendarId,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.booleans import (
    IsHandoffOpen,
    IsResolvedIncluded,
    IsUnansweredQuestionResolved,
    RequiresAssistantReassembly,
)
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.insights.constrained_floats import AfterHoursSharePercent
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    UsedVoiceMinutes,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.schemas.typings.users.prefixed_id import UserId

# Bookings in the cabinet


class ListBookingsQuery(ImmutableDTO):
    """
    One page of the bookings of a business for the cabinet, filtered by the
    local start date (inclusive range in the business time zone), status
    and resource, ordered by start time (earliest first by default).
    """

    business_id: BusinessId
    actor_id: UserId
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None
    status: BookingStatus | None = None
    resource_id: ResourceId | None = None
    include_sandbox: IsSandboxIncluded = False
    order: BookingOrder = BookingOrder.EARLIEST_FIRST
    page: PageRequest = PageRequest()


class BookingPage(ImmutableDTO):
    """One page of bookings; `next_cursor` is None on the last page."""

    items: list[BookingView] = Field(default_factory=list[BookingView])
    next_cursor: PageCursor | None = None


class ManualBookingRequest(ImmutableDTO):
    """
    Body of a booking added by staff in the cabinet.

    The phone may be typed in any national or international format; it is
    parsed with `country_hint` (the business country when omitted).
    `language` is the customer's language for the confirmation text
    (business default when omitted). `conversation_id` books for the
    customer of that conversation and links the booking to it.
    """

    contact_name: ContactName
    contact_phone_number: RawPhoneNumberInput | None = None
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    party_size: PartySize
    notes: BookingNote | None = None
    source_channel: ChannelKind = ChannelKind.PHONE
    language: LanguageTag | None = None
    country_hint: CountryCode | None = None
    conversation_id: ConversationId | None = None


class ManualBookingCommand(ImmutableDTO):
    """
    Booking added by staff. Capacity and opening hours are enforced; the
    online-booking limits (minimum notice, maximum party size) are not,
    because staff decide those case by case.
    """

    business_id: BusinessId
    actor_id: UserId
    contact_name: ContactName
    contact_phone_number: RawPhoneNumberInput | None = None
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    party_size: PartySize
    notes: BookingNote | None = None
    source_channel: ChannelKind = ChannelKind.PHONE
    language: LanguageTag | None = None
    country_hint: CountryCode | None = None
    conversation_id: ConversationId | None = None


class RescheduleBookingRequest(ImmutableDTO):
    """Body of a cabinet reschedule: new local date and (for slots) time."""

    new_date: LocalDate
    new_time: LocalTimeOfDay | None = None


class UpdateBookingRequest(ImmutableDTO):
    """
    Body of a cabinet booking change; omitted fields stay as they are.

    `status`: COMPLETED, NO_SHOW or CANCELLED, or CONFIRMED for a PENDING
    booking. `party_size` and `resource_id` must fit the booked time (the
    resource seats the party, is open and has a free unit then). An empty
    `notes` text removes the notes. `contact_name` renames the customer.
    The time is changed by rescheduling.
    """

    status: BookingStatus | None = None
    party_size: PartySize | None = None
    resource_id: ResourceId | None = None
    notes: BookingNote | None = None
    contact_name: ContactName | None = None


class UpdateBookingCommand(ImmutableDTO):
    """Staff changes the status or the details of a booking."""

    business_id: BusinessId
    actor_id: UserId
    booking_id: BookingId
    status: BookingStatus | None = None
    party_size: PartySize | None = None
    resource_id: ResourceId | None = None
    notes: BookingNote | None = None
    contact_name: ContactName | None = None


# Leads in the cabinet


class ListLeadsQuery(ImmutableDTO):
    """One page of the leads of a business for the cabinet, newest first."""

    business_id: BusinessId
    actor_id: UserId
    status: LeadStatus | None = None
    include_sandbox: IsSandboxIncluded = False
    page: PageRequest = PageRequest()


class LeadListItem(ImmutableDTO):
    """Lead with the contact it came from."""

    id: LeadId
    business_id: BusinessId
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    conversation_id: ConversationId | None = None
    lead_type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    source_channel: ChannelKind
    status: LeadStatus
    is_sandbox: IsSandboxConversation = False
    created_at: Microseconds


class LeadStatusCount(ImmutableDTO):
    """How many leads have one status (for the status tabs)."""

    status: LeadStatus
    count: ListItemCount


class LeadPage(ImmutableDTO):
    """
    One page of leads, newest first, and how many leads of each status
    there are (the status filter aside), for the tabs.
    """

    items: list[LeadListItem] = Field(default_factory=list[LeadListItem])
    next_cursor: PageCursor | None = None
    status_counts: list[LeadStatusCount] = Field(default_factory=list[LeadStatusCount])


class UpdateLeadStatusRequest(ImmutableDTO):
    """Body of a cabinet lead status change."""

    status: LeadStatus


class UpdateLeadStatusCommand(ImmutableDTO):
    """Staff moves a lead through NEW, IN_PROGRESS, WON or LOST."""

    business_id: BusinessId
    lead_id: LeadId
    status: LeadStatus


# Handoffs in the cabinet


class ListHandoffsQuery(ImmutableDTO):
    """
    One page of the handoffs of a business for the cabinet.

    `is_open` True keeps the ones still waiting for a person (any status but
    RESOLVED), False the resolved ones. Open handoffs come first, the most
    urgent first, then the one waiting longest; resolved ones follow, the
    most recently resolved first.
    """

    business_id: BusinessId
    actor_id: UserId
    status: HandoffStatus | None = None
    is_open: IsHandoffOpen | None = None
    include_sandbox: IsSandboxIncluded = False
    page: PageRequest = PageRequest()


class HandoffListItem(ImmutableDTO):
    """Handoff with the contact to call back."""

    id: HandoffId
    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    reason: HandoffReason
    summary: HandoffSummary
    urgency: HandoffUrgency
    status: HandoffStatus
    is_sandbox: IsSandboxConversation = False
    created_at: Microseconds
    resolved_at: Microseconds | None = None


class HandoffPage(ImmutableDTO):
    """
    One page of handoffs and how many are open and resolved (the status
    filters aside), for the tabs.
    """

    items: list[HandoffListItem] = Field(default_factory=list[HandoffListItem])
    next_cursor: PageCursor | None = None
    open_count: ListItemCount
    resolved_count: ListItemCount


class ResolveHandoffCommand(ImmutableDTO):
    """Staff closes a handoff; the assistant may answer the conversation again."""

    business_id: BusinessId
    handoff_id: HandoffId


# Unanswered questions in the cabinet


class ListUnansweredQuestionsQuery(ImmutableDTO):
    """Questions the assistant could not answer, most frequent first."""

    business_id: BusinessId
    include_resolved: IsResolvedIncluded = False
    include_sandbox: IsSandboxIncluded = False


class UnansweredQuestionDetails(ImmutableDTO):
    """Unanswered question with how often and when it was last asked."""

    id: UnansweredQuestionId
    business_id: BusinessId
    question: UnansweredQuestionText
    language: LanguageTag
    occurrence_count: QuestionOccurrenceCount
    last_seen_at: Microseconds
    is_resolved: IsUnansweredQuestionResolved
    resolved_knowledge_item_id: KnowledgeItemId | None = None
    is_sandbox: IsSandboxConversation = False


class UnansweredQuestionListView(ImmutableDTO):
    """Questions ordered by occurrence count, then most recent."""

    items: list[UnansweredQuestionDetails] = Field(
        default_factory=list[UnansweredQuestionDetails]
    )


class AnswerUnansweredQuestionRequest(ImmutableDTO):
    """Body of "add answer": the answer and an optional FAQ title."""

    answer: KnowledgeBody
    title: KnowledgeTitle | None = None


class AnswerUnansweredQuestionCommand(ImmutableDTO):
    """
    Owner answers a question; the answer becomes an active FAQ item.

    The FAQ title defaults to the question text.
    """

    business_id: BusinessId
    question_id: UnansweredQuestionId
    answer: KnowledgeBody
    title: KnowledgeTitle | None = None


class AnsweredQuestionResult(ImmutableDTO):
    """
    The resolved question and the new FAQ item. The assistant must be
    reassembled (and autotested) before customers see the answer.
    """

    question: UnansweredQuestionDetails
    knowledge_item_id: KnowledgeItemId
    requires_reassembly: RequiresAssistantReassembly


# Dashboard


class DashboardStatsQuery(ImmutableDTO):
    """
    Dashboard for an inclusive range of local dates in the business time
    zone. Defaults to the last 30 days including today.
    """

    business_id: BusinessId
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None


class BookingStatusCount(ImmutableDTO):
    """Bookings with one status."""

    status: BookingStatus
    count: PeriodItemCount


class HandoffReasonCount(ImmutableDTO):
    """Handoffs with one reason."""

    reason: HandoffReason
    count: PeriodItemCount


class HandoffUrgencyCount(ImmutableDTO):
    """Handoffs with one urgency."""

    urgency: HandoffUrgency
    count: PeriodItemCount


class LanguageCount(ImmutableDTO):
    """Conversations held in one language."""

    language: LanguageTag
    count: PeriodItemCount


class ChannelCount(ImmutableDTO):
    """Conversations started in one channel."""

    channel: ChannelKind
    count: PeriodItemCount


class DashboardDay(ImmutableDTO):
    """What started on one local day of the dashboard period."""

    date: LocalDate
    conversation_count: PeriodItemCount
    booking_count: PeriodItemCount
    handoff_count: PeriodItemCount


class DashboardPackageUsage(ImmutableDTO):
    """
    Use of the plan package in the current billing window, for owners and
    staff alike (no prices). Percents are empty for a package of zero.
    """

    period_start: Microseconds
    period_end: Microseconds
    used_voice_minutes: PackageUsedVoiceMinutes
    included_voice_minutes: IncludedVoiceMinutes
    voice_usage_percent: PackageUsagePercent | None = None
    overage_voice_minutes: OverageVoiceMinutes
    used_dialogs: UsedDialogs
    included_dialogs: IncludedDialogs
    dialog_usage_percent: PackageUsagePercent | None = None


class DashboardStats(ImmutableDTO):
    """
    Cabinet dashboard (concept /dashboard): conversations, customer messages,
    share started outside opening hours, bookings, leads, handoffs, languages,
    channels, open unanswered questions, package minutes used in the period,
    a series per local day, and the package of the current billing window
    (None without a subscription).

    Sandbox (owner test and autotest) activity is excluded. Breakdown lists
    are ordered by count descending; `daily` has every date of the period,
    oldest first.
    """

    business_id: BusinessId
    timezone: TimezoneName
    date_from: LocalDate
    date_to: LocalDate
    conversation_count: PeriodItemCount
    customer_message_count: PeriodItemCount
    after_hours_conversation_count: PeriodItemCount
    after_hours_share_percent: AfterHoursSharePercent
    booking_count: PeriodItemCount
    bookings_by_status: list[BookingStatusCount] = Field(
        default_factory=list[BookingStatusCount]
    )
    lead_count: PeriodItemCount
    handoff_count: PeriodItemCount
    handoffs_by_reason: list[HandoffReasonCount] = Field(
        default_factory=list[HandoffReasonCount]
    )
    handoffs_by_urgency: list[HandoffUrgencyCount] = Field(
        default_factory=list[HandoffUrgencyCount]
    )
    languages: list[LanguageCount] = Field(default_factory=list[LanguageCount])
    channels: list[ChannelCount] = Field(default_factory=list[ChannelCount])
    open_unanswered_question_count: PeriodItemCount
    used_voice_minutes: UsedVoiceMinutes
    daily: list[DashboardDay] = Field(default_factory=list[DashboardDay])
    package: DashboardPackageUsage | None = None


# Google Calendar


class StartCalendarConnectionCommand(ImmutableDTO):
    """Owner starts connecting Google Calendar to a business."""

    business_id: BusinessId
    user_id: UserId


class CalendarConnectUrlView(ImmutableDTO):
    """Consent page to open; the link stops working at `expires_at`."""

    authorization_url: CalendarAuthorizationUrl
    expires_at: Microseconds


class CompleteCalendarConnectionCommand(ImmutableDTO):
    """OAuth callback values: the state we issued and Google's code."""

    state: CalendarAuthorizationState
    code: CalendarAuthorizationCode


class CalendarConnectionView(ImmutableDTO):
    """A connected calendar of a business."""

    business_id: BusinessId
    calendar_id: ExternalCalendarId
    connected_at: Microseconds


class DisconnectCalendarCommand(ImmutableDTO):
    """Owner disconnects Google Calendar; the token is revoked at Google."""

    business_id: BusinessId


class CalendarDisconnectResult(ImmutableDTO):
    """Whether a calendar was connected before the call."""

    business_id: BusinessId
    was_connected: WasCalendarConnected


class CalendarTokenGrant(ImmutableDTO):
    """
    Tokens returned by the provider. A refresh token comes only with the
    first consent (offline access); refreshes return a new access token only.
    """

    access_token: CalendarAccessToken
    refresh_token: CalendarRefreshToken | None = None
    expires_in: CalendarTokenLifetimeSeconds


class CalendarEventText(ImmutableDTO):
    """Owner-language title and description of a booking's calendar event."""

    title: CalendarEventTitle
    description: CalendarEventDescription


class CalendarEventDraft(ImmutableDTO):
    """Event to create or update at the provider; times are UTC seconds."""

    title: CalendarEventTitle
    description: CalendarEventDescription
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    timezone: TimezoneName


# Message texts


class StaffMessage(ImmutableDTO):
    """One notification text for one staff contact, in their language."""

    contact: ManagerContact
    text: MessageText


class BookingMessageInput(ImmutableDTO):
    """
    Customer-facing booking text (confirmation, cancellation, new time).

    `cancellation_policy` is the owner's rule from the profile, quoted as is.
    """

    business_name: BusinessName
    booking: BookingView
    booking_unit: BookingUnit
    language: LanguageTag
    cancellation_policy: CancellationPolicyText | None = None


class BookingStaffNotificationInput(ImmutableDTO):
    """Staff notification about a booking, rendered in the staff language."""

    business_name: BusinessName
    booking: BookingView
    contact_phone_display: FormattedPhoneNumber | None = None
    language: LanguageTag


class LeadStaffNotificationInput(ImmutableDTO):
    """Staff notification about a new lead."""

    business_name: BusinessName
    lead: LeadView
    contact_name: ContactName | None = None
    contact_phone_display: FormattedPhoneNumber | None = None
    language: LanguageTag


class HandoffStaffNotificationInput(ImmutableDTO):
    """Staff notification about a conversation passed to a human."""

    business_name: BusinessName
    reason: HandoffReason
    urgency: HandoffUrgency
    summary: HandoffSummary
    contact_name: ContactName | None = None
    contact_phone_display: FormattedPhoneNumber | None = None
    channel: ChannelKind
    language: LanguageTag


class HandoffCustomerMessageInput(ImmutableDTO):
    """
    What to tell the customer after a handoff. Without a reopening moment the
    business is open now (or its hours are unknown): "a colleague will reply
    soon".
    """

    language: LanguageTag
    reopens_on: LocalDate | None = None
    reopens_at: LocalTimeOfDay | None = None


class CalendarEventTextInput(ImmutableDTO):
    """Booking to describe in the owner's calendar, in the owner's language."""

    booking: BookingView
    contact_phone_display: FormattedPhoneNumber | None = None
    language: LanguageTag
