"""
Owner cabinet: the conversation feed and one conversation with its
messages, calls and staff replies (concept section 8).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    CallGuardVerdict,
    CallOutcome,
    ConversationRating,
    ConversationStatus,
    MessageAuthor,
    StaffMessageDelivery,
    StaffReplyBlock,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.conversation_feed.message_tallies import (
    ConversationMessageTally,
    ConversationUsageView,
)
from app.schemas.dto.inbox.assignment import ConversationAssignmentView
from app.schemas.dto.media import MessageAttachmentView
from app.schemas.dto.operations.handoffs import HandoffListItem
from app.schemas.dto.operations.leads import LeadListItem
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.staff_reply_templates import StaffReplyTemplateView
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import (
    IncludeSandboxConversations,
    IsAfterHours,
    IsLlmToolError,
    IsSandboxConversation,
    IsStaffReplyAvailable,
)
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
    ConversationMessageCount,
    LlmTokenCount,
)
from app.schemas.typings.conversations.constrained_strings import ConversationSearchText
from app.schemas.typings.conversations.prefixed_id import (
    CallId,
    ConversationId,
    MessageId,
)
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    LlmToolInputJson,
    LlmToolResultJson,
    MessagePreview,
    MessageText,
    RecordingStoragePath,
    UnverifiedReplyValue,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class ConversationListQuery(ImmutableDTO):
    """
    One page of the conversations of a business, the latest message first.

    Sandbox conversations (owner test chat, autotests) are hidden unless
    `include_sandbox` is set. `date_from` / `date_to` are local dates of the
    business time zone (inclusive) and keep conversations that were going on
    then (started before the end, last message after the start). `search`
    matches the customer's name, the phone by its digits in any format, and
    the words of any message, ignoring case and accents in every script.
    """

    user_id: UserId
    business_id: BusinessId
    channel: ChannelKind | None = None
    status: ConversationStatus | None = None
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None
    search: ConversationSearchText | None = None
    include_sandbox: IncludeSandboxConversations = False
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class ConversationQuery(ImmutableDTO):
    """One conversation with its messages; the view is written to the audit log."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    client_ip_address: ClientIpAddress | None = None


class ConversationMessagesQuery(ImmutableDTO):
    """
    Earlier messages of a conversation: the page before the cursor the card
    or the previous page gave (audited like the card).
    """

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    page: PageRequest = Field(default_factory=PageRequest)
    client_ip_address: ClientIpAddress | None = None


class ConversationSummaryView(ImmutableDTO):
    """
    A conversation row in the feed: who, where, flags, how many messages
    (all and the customer's) and the beginning of the last one.
    """

    id: ConversationId
    business_id: BusinessId
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    assistant_version_id: AssistantVersionId
    channel: ChannelKind
    language: LanguageTag | None = None
    status: ConversationStatus
    is_after_hours: IsAfterHours
    is_sandbox: IsSandboxConversation
    message_count: ConversationMessageCount
    customer_message_count: ConversationMessageCount
    last_message_text: MessagePreview | None = None
    last_message_author: MessageAuthor | None = None
    last_message_at: Microseconds
    created_at: Microseconds
    rating: ConversationRating | None = None


class ConversationPage(ImmutableDTO):
    """One page of the feed; `next_cursor` is None on the last page."""

    items: list[ConversationSummaryView] = Field(
        default_factory=list[ConversationSummaryView]
    )
    next_cursor: PageCursor | None = None


class ToolCallView(ImmutableDTO):
    """One tool call made while producing a message."""

    tool_name: AssistantToolName
    input_json: LlmToolInputJson
    result_json: LlmToolResultJson
    is_error: IsLlmToolError


class MessageView(ImmutableDTO):
    """
    A message with the model usage behind it; `sent_by` is the owner or
    staff member who wrote a staff message from the cabinet; `attachments`
    are a customer's voice notes, photos and places.
    """

    id: MessageId
    direction: MessageDirection
    author: MessageAuthor
    text: MessageText
    language: LanguageTag | None = None
    sent_by: UserId | None = None
    tool_calls: list[ToolCallView] = Field(default_factory=list[ToolCallView])
    model_id: LlmModelId | None = None
    input_tokens: LlmTokenCount
    output_tokens: LlmTokenCount
    cost_micro_usd: CostMicroUsd
    created_at: Microseconds
    attachments: list[MessageAttachmentView] = Field(
        default_factory=list[MessageAttachmentView]
    )


class CallSummaryView(ImmutableDTO):
    """The short summary of a call for staff, in one language."""

    language: LanguageTag
    text: CallSummaryText


class CallView(ImmutableDTO):
    """
    A phone call of the conversation: its transcript, duration, outcome and
    where its recording is kept (the platform reference; reading it is
    audited with the card), what the after-call check of the assistant's
    spoken values found (`guard_verdict`, None while unchecked), and its
    summary for staff in the owner's and the staff's languages (empty until
    the call is summarized).
    """

    id: CallId
    from_phone_number: E164PhoneNumber | None = None
    to_phone_number: E164PhoneNumber | None = None
    started_at: Microseconds
    duration_seconds: CallDurationSeconds
    outcome: CallOutcome | None = None
    transcript: CallTranscriptText | None = None
    recording_path: RecordingStoragePath | None = None
    guard_verdict: CallGuardVerdict | None = None
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    summaries: list[CallSummaryView] = Field(default_factory=list[CallSummaryView])


class StaffReplyView(ImmutableDTO):
    """
    Whether staff can write to the customer from the card now, why not
    (`block`), how the message would travel, and until when a 24-hour
    messaging window stays open (WhatsApp, Instagram, Messenger). When the
    WhatsApp window has closed and the owner set a message template for
    staff replies, `template` offers sending the text in it instead.
    """

    is_available: IsStaffReplyAvailable
    block: StaffReplyBlock | None = None
    delivery: StaffMessageDelivery | None = None
    window_closes_at: Microseconds | None = None
    template: StaffReplyTemplateView | None = None


class ConversationDetailView(ImmutableDTO):
    """
    Conversation card: summary, the newest part of the transcript with tool
    calls (oldest first; `earlier_messages_cursor` pages back through
    `GET .../messages` when there is more), the model usage of the whole
    conversation, for phone conversations the calls with their transcripts
    and recordings, the bookings, leads and handoffs made in it, whether
    staff can reply, and who of the team is assigned to it (its
    `assignment_revision` is what an assignment from the card must name).
    """

    conversation: ConversationSummaryView
    messages: list[MessageView] = Field(default_factory=list[MessageView])
    earlier_messages_cursor: PageCursor | None = None
    usage: ConversationUsageView = Field(default_factory=ConversationUsageView)
    calls: list[CallView] = Field(default_factory=list[CallView])
    bookings: list[BookingView] = Field(default_factory=list[BookingView])
    leads: list[LeadListItem] = Field(default_factory=list[LeadListItem])
    handoffs: list[HandoffListItem] = Field(default_factory=list[HandoffListItem])
    reply: StaffReplyView | None = None
    assignment: ConversationAssignmentView | None = None


class ConversationViewSource(ImmutableDTO):
    """
    A conversation with its contact, its message counts and the newest
    message someone wrote (the preview), ready to be rendered as a row.
    """

    conversation: ConversationDocument
    contact: ContactDocument | None = None
    tally: ConversationMessageTally = Field(default_factory=ConversationMessageTally)
    last_written: MessageDocument | None = None


class MessagePage(ImmutableDTO):
    """
    Earlier messages of a conversation, oldest first; `next_cursor` asks for
    the ones before them (None when the transcript starts here).
    """

    items: list[MessageView] = Field(default_factory=list[MessageView])
    next_cursor: PageCursor | None = None
