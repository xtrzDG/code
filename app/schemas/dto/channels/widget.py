"""The website chat widget: its configuration, messages, replies and snippet."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import WidgetPosition
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.constants.sharing import ShareLinkKind
from app.schemas.typings.businesses.constrained_strings import WebLink
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
    WidgetStarterQuestionText,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import IsConversationHandedOff
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.schemas.typings.sharing.constrained_strings import ShareLinkUrl
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


class WidgetStarterQuestionView(ImmutableDTO):
    """A question the visitor can send with one tap, in its language."""

    language: LanguageTag
    text: WidgetStarterQuestionText


class WidgetContactLinkView(ImmutableDTO):
    """Another way to reach the business (WhatsApp, Telegram, a call...)."""

    kind: ShareLinkKind
    url: ShareLinkUrl


class WidgetConfigView(ImmutableDTO):
    """
    Public configuration the widget script loads before it shows itself.

    `business_name` is the name visitors see in the widget header.
    `greetings` holds the first message in the languages the live assistant
    answers in (the business languages before anything is published) where
    a text exists; the widget uses its own text for the others. `accent_color`
    and `position` are the owner's choices (None: the widget's defaults); the
    embed tag's data-color and data-position still win.

    `starter_questions` are up to three of the business's FAQ questions per
    language, shown as one-tap chips before the visitor writes;
    `privacy_url` is the business's privacy notice (or the platform's
    default one for it; None without CABINET_BASE_URL), linked from the
    footer; `contact_links` are the other channels, offered on the hosted
    chat page.
    """

    business_id: BusinessId
    business_name: BusinessName
    is_enabled: IsWebChatEnabled
    default_language: LanguageTag
    languages: list[WidgetLanguageView]
    greetings: list[WidgetGreetingView]
    accent_color: WidgetAccentColor | None = None
    position: WidgetPosition | None = None
    starter_questions: list[WidgetStarterQuestionView] = Field(
        default_factory=list[WidgetStarterQuestionView]
    )
    privacy_url: WebLink | None = None
    contact_links: list[WidgetContactLinkView] = Field(
        default_factory=list[WidgetContactLinkView]
    )


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
