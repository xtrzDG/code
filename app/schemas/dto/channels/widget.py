"""The website chat widget: its configuration, messages, replies and snippet."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channels import WidgetPosition
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.booleans import (
    HasMoreWidgetMessages,
    IsWebChatEnabled,
)
from app.schemas.typings.channels.constrained_strings import (
    WidgetAccentColor,
    WidgetDemoUrl,
    WidgetMessageText,
    WidgetScriptUrl,
    WidgetSessionKey,
)
from app.schemas.typings.channels.strings import (
    WidgetContactNameInput,
    WidgetEmbedSnippet,
    WidgetGreetingText,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import IsConversationHandedOff
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.schemas.typings.users.prefixed_id import UserId


class WidgetLanguageView(ImmutableDTO):
    """A customer language of the widget with its writing direction."""

    tag: LanguageTag
    native_name: LanguageDisplayName
    direction: TextDirection


class WidgetGreetingView(ImmutableDTO):
    """The widget's first message in one customer language."""

    language: LanguageTag
    text: WidgetGreetingText
    direction: TextDirection


class WidgetConfigView(ImmutableDTO):
    """
    Public configuration the widget script loads before it shows itself.

    `business_name` is the name visitors see in the widget header.
    `greetings` holds the first message in the languages the live assistant
    answers in (the business languages before anything is published) where
    a text exists; the widget uses its own text for the others. `accent_color`
    and `position` are the owner's choices (None: the widget's defaults); the
    embed tag's data-color and data-position still win.
    """

    business_id: BusinessId
    business_name: BusinessName
    is_enabled: IsWebChatEnabled
    default_language: LanguageTag
    languages: list[WidgetLanguageView]
    greetings: list[WidgetGreetingView]
    accent_color: WidgetAccentColor | None = None
    position: WidgetPosition | None = None


class WidgetMessageRequest(ImmutableDTO):
    """HTTP body of a visitor message typed into the widget."""

    session_key: WidgetSessionKey
    text: WidgetMessageText
    contact_name: WidgetContactNameInput | None = None


class WidgetMessageCommand(ImmutableDTO):
    """A visitor message for one business's widget, and where it came from."""

    business_id: BusinessId
    request: WidgetMessageRequest
    client_ip_address: ClientIpAddress | None = None


class WidgetReplyView(ImmutableDTO):
    """
    The assistant's answer in the widget.

    `text` is None while staff handle the conversation; `direction` tells the
    widget how to lay the answer out (right-to-left for Hebrew, Arabic, ...).
    `message_id` is the stored answer (None without one); `cursor` is the
    visitor's message, so polling GET .../messages?after=<cursor> returns
    the answer again (skip it by id) and every staff message written since.
    """

    conversation_id: ConversationId
    text: MessageText | None
    language: LanguageTag
    direction: TextDirection
    is_handed_off: IsConversationHandedOff
    message_id: MessageId | None = None
    cursor: MessageId | None = None


class WidgetReplyInput(ImmutableDTO):
    """The assistant's answer to a widget visitor of one business."""

    business_id: BusinessId
    reply: AssistantReply


class WidgetMessagesQuery(ImmutableDTO):
    """
    A widget polls for new answers of its visitor's conversations: the
    assistant's and staff's messages after the message `after`. Without
    `after` nothing is returned but the current position (a widget that has
    shown everything starts from there).
    """

    business_id: BusinessId
    session_key: WidgetSessionKey
    after: MessageId | None = None
    client_ip_address: ClientIpAddress | None = None


class WidgetMessageView(ImmutableDTO):
    """An assistant or staff message as the widget shows it."""

    id: MessageId
    author: MessageAuthor
    text: MessageText
    language: LanguageTag | None = None
    direction: TextDirection
    created_at: Microseconds


class WidgetMessagesView(ImmutableDTO):
    """
    New assistant and staff messages, oldest first (at most a page; poll
    again with `cursor` while `has_more`). `cursor` is the position to poll
    after next time (None while the visitor has no conversation);
    `is_handed_off` tells whether staff currently handle the conversation.
    """

    items: list[WidgetMessageView]
    cursor: MessageId | None = None
    has_more: HasMoreWidgetMessages = False
    is_handed_off: IsConversationHandedOff = False


class WidgetSnippetQuery(ImmutableDTO):
    """Ask for the embed code of a business's widget."""

    user_id: UserId
    business_id: BusinessId


class WidgetSnippetView(ImmutableDTO):
    """
    Embed code the owner pastes into the website, and the page that shows
    the widget as visitors see it (it accepts `color`, `position` and
    `language` to preview unsaved choices).
    """

    business_id: BusinessId
    script_url: WidgetScriptUrl
    snippet: WidgetEmbedSnippet
    demo_url: WidgetDemoUrl
