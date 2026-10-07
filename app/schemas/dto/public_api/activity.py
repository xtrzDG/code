"""
Conversations, their messages, handoffs to the team and phone calls as the
public API and webhooks show them (frozen within /v1).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import (
    CallOutcome,
    ConversationStatus,
    MessageAuthor,
)
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.dto.public_api.records import PublicContactRef
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.conversations.constrained_integers import CallDurationSeconds
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.prefixed_id import (
    CallId,
    ConversationId,
    MessageId,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.integrations.constrained_strings import PublicTimestamp
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag


class PublicConversation(ImmutableDTO):
    """
    A customer's conversation in one channel: who (`contact`), where
    (`channel`, `acquisition_source`), its state and, once it was quiet for
    a while, what it was about (`summary`).
    """

    id: ConversationId
    channel: ChannelKind
    status: ConversationStatus
    contact: PublicContactRef
    language: LanguageTag | None = None
    acquisition_source: AcquisitionSourceTag | None = None
    summary: ConversationSummaryText | None = None
    started_at: PublicTimestamp
    last_message_at: PublicTimestamp


class PublicMessage(ImmutableDTO):
    """One message of a conversation (`author`: customer, assistant, staff)."""

    id: MessageId
    author: MessageAuthor
    text: MessageText
    created_at: PublicTimestamp


class PublicConversationDetail(PublicConversation):
    """A conversation with its latest messages, oldest first."""

    messages: list[PublicMessage] = Field(default_factory=list[PublicMessage])


class PublicHandoff(ImmutableDTO):
    """A conversation passed to the team: why, how urgent, and its state."""

    id: HandoffId
    status: HandoffStatus
    reason: HandoffReason
    urgency: HandoffUrgency
    summary: HandoffSummary
    conversation_id: ConversationId
    contact: PublicContactRef
    created_at: PublicTimestamp
    resolved_at: PublicTimestamp | None = None


class PublicCall(ImmutableDTO):
    """
    A finished phone call the assistant took: who called which number (the
    caller's customer card, when the call opened a conversation), how long
    and how it ended, with the staff summary when one was written.
    """

    id: CallId
    conversation_id: ConversationId | None = None
    from_phone_number: E164PhoneNumber | None = None
    to_phone_number: E164PhoneNumber | None = None
    started_at: PublicTimestamp
    duration_seconds: CallDurationSeconds
    outcome: CallOutcome | None = None
    summary: CallSummaryText | None = None
    contact: PublicContactRef | None = None
    acquisition_source: AcquisitionSourceTag | None = None
