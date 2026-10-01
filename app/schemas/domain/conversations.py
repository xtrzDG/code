from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import (
    ConversationStatus,
    LlmTurnRole,
    MessageAuthor,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.constrained_integers import (
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.prefixed_id import (
    ConversationId,
    ConversationMessageId,
    LlmTurnId,
)
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    CustomerName,
    LlmProviderPayload,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)


class ConversationDocument(BaseDocument):
    """Customer conversation in one channel, pinned to one assistant version."""

    id: ConversationId = Field(default_factory=ConversationId)
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    channel: ChannelKind
    channel_user_id: ChannelUserId
    customer_name: CustomerName | None = None
    customer_phone_number: E164PhoneNumber | None = None
    language: LanguageTag | None = None
    status: ConversationStatus = ConversationStatus.OPEN
    is_sandbox: IsSandboxConversation = False
    last_message_at: Microseconds


class ConversationMessageDocument(BaseDocument):
    """Customer-visible message shown in the owner's conversation feed."""

    id: ConversationMessageId = Field(default_factory=ConversationMessageId)
    conversation_id: ConversationId
    business_id: BusinessId
    author: MessageAuthor
    text: MessageText
    language: LanguageTag | None = None


class LlmTurnDocument(BaseDocument):
    """
    One raw language-model turn, stored verbatim and only ever appended.

    The sequence of turns of a conversation is replayed to the model as-is.
    """

    id: LlmTurnId = Field(default_factory=LlmTurnId)
    conversation_id: ConversationId
    sequence_number: LlmTurnSequenceNumber
    role: LlmTurnRole
    payload: LlmProviderPayload
