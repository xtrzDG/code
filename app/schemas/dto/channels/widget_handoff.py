"""A website visitor asks for a person ("Talk to a person" in the widget)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.localization import TextDirection
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WidgetSessionKey,
    WidgetSourceInput,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsConversationHandedOff
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag


class WidgetHandoffRequest(ImmutableDTO):
    """
    HTTP body of "Talk to a person": the visitor's key and the widget's
    interface language (the language staff's notice to the visitor is in
    when the visitor has not written yet), and where the visitor came from
    (a conversation the request opens keeps it).
    """

    session_key: WidgetSessionKey
    language: LanguageTag | None = None
    source: WidgetSourceInput | None = None


class WidgetHandoffCommand(ImmutableDTO):
    """A visitor of one business's widget asks for a person."""

    business_id: BusinessId
    request: WidgetHandoffRequest
    client_ip_address: ClientIpAddress | None = None


class WidgetHandoffTarget(ImmutableDTO):
    """
    The visitor's conversation a handoff goes to (opened now when the
    visitor had none), in the visitor's language, and what staff read.
    `is_already_handed_off`: staff already own it, nothing new is created.
    """

    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    language: LanguageTag
    summary: HandoffSummary
    is_already_handed_off: IsConversationHandedOff


class WidgetHandoffNotice(ImmutableDTO):
    """
    What the visitor is told after a new handoff, to store in the chat
    (`text` None: staff already had the conversation, nothing is stored).
    """

    business_id: BusinessId
    conversation_id: ConversationId
    text: MessageText | None = None
    language: LanguageTag


class WidgetHandoffView(ImmutableDTO):
    """
    The widget's answer to "Talk to a person": the conversation now with
    staff and, for a new handoff, the message telling the visitor when
    they hear back (stored in the chat, so polling skips it by
    `message_id`). `text` is None when staff already had the conversation.
    """

    conversation_id: ConversationId
    is_handed_off: IsConversationHandedOff
    message_id: MessageId | None = None
    text: MessageText | None = None
    language: LanguageTag
    direction: TextDirection
