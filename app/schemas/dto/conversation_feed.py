"""Owner cabinet: conversation feed and the owner's test chat (concept section 8)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    CallOutcome,
    ConversationRating,
    ConversationStatus,
    MessageAuthor,
    StaffMessageDelivery,
    StaffReplyBlock,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    ConversationDocument,
    MessageDocument,
)
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.handoffs import HandoffListItem
from app.schemas.dto.operations.leads import LeadListItem
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.staff_reply_templates import StaffReplyTemplateView
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import (
    IncludeSandboxConversations,
    IsAfterHours,
    IsLlmToolError,
    IsSandboxConversation,
    IsStaffReplyAvailable,
    SendAsTemplate,
)
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
    ConversationMessageCount,
    LlmTokenCount,
)
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSearchText,
    OwnerTestChatSessionKey,
    StaffReplyText,
)
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
    staff member who wrote a staff message from the cabinet.
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


class CallView(ImmutableDTO):
    """
    A phone call of the conversation: its transcript, duration, outcome and
    where its recording is kept (the platform reference; reading it is
    audited with the card).
    """

    id: CallId
    from_phone_number: E164PhoneNumber | None = None
    to_phone_number: E164PhoneNumber | None = None
    started_at: Microseconds
    duration_seconds: CallDurationSeconds
    outcome: CallOutcome | None = None
    transcript: CallTranscriptText | None = None
    recording_path: RecordingStoragePath | None = None


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
    Conversation card: summary, the full transcript with tool calls, for
    phone conversations the calls with their transcripts and recordings,
    the bookings, leads and handoffs made in it, and whether staff can reply.
    """

    conversation: ConversationSummaryView
    messages: list[MessageView] = Field(default_factory=list[MessageView])
    calls: list[CallView] = Field(default_factory=list[CallView])
    bookings: list[BookingView] = Field(default_factory=list[BookingView])
    leads: list[LeadListItem] = Field(default_factory=list[LeadListItem])
    handoffs: list[HandoffListItem] = Field(default_factory=list[HandoffListItem])
    reply: StaffReplyView | None = None


class ConversationRatingRequest(ImmutableDTO):
    """HTTP body of rating a conversation; null clears the rating."""

    rating: ConversationRating | None


class RateConversationCommand(ImmutableDTO):
    """Owner or staff rates how the assistant handled a conversation."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    rating: ConversationRating | None


class StaffMessageRequest(ImmutableDTO):
    """
    HTTP body of a staff message to the customer of a conversation;
    `as_template` sends it in the WhatsApp template the card offers once the
    24-hour window has closed (while the window is open it travels as an
    ordinary message).
    """

    text: StaffReplyText
    as_template: SendAsTemplate = False


class SendStaffMessageCommand(ImmutableDTO):
    """An owner or staff member writes to the customer from the cabinet."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    text: StaffReplyText
    as_template: SendAsTemplate = False
    client_ip_address: ClientIpAddress | None = None


class StaffMessageResult(ImmutableDTO):
    """The stored staff message and how it reaches the customer."""

    message: MessageView
    delivery: StaffMessageDelivery


class ConversationViewSource(ImmutableDTO):
    """A conversation with its contact and messages, ready to be rendered."""

    conversation: ConversationDocument
    contact: ContactDocument | None = None
    messages: list[MessageDocument] = Field(default_factory=list[MessageDocument])


class OwnerTestChatRequest(ImmutableDTO):
    """
    HTTP body of the owner's test chat.

    Without `assistant_version_id` the published version answers, or the
    newest ready (then draft) version before the first publication.
    `session_key` keeps parallel test chats apart.
    """

    text: MessageText
    session_key: OwnerTestChatSessionKey | None = None
    assistant_version_id: AssistantVersionId | None = None


class OwnerTestChatCommand(ImmutableDTO):
    """A signed-in owner or staff member writes to the assistant from the cabinet."""

    user_id: UserId
    business_id: BusinessId
    request: OwnerTestChatRequest


class OwnerTestChatVersionQuery(ImmutableDTO):
    """
    Which assistant version answers a test chat message: the requested one,
    else the published one, else the newest ready (then draft) version.
    """

    business_id: BusinessId
    requested_version_id: AssistantVersionId | None = None
    published_version_id: AssistantVersionId | None = None
