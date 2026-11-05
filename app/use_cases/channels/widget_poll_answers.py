"""What a widget poll answers: which messages it shows, and how."""

from app.contracts.registries import LanguageRegistryContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.channels.widget import WidgetMessagesView, WidgetMessageView
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.conversations.rating_invitations import invites_rating

# Messages the widget shows besides the visitor's own.
WIDGET_MESSAGE_AUTHORS: frozenset[MessageAuthor] = frozenset(
    {MessageAuthor.ASSISTANT, MessageAuthor.STAFF}
)
WIDGET_MESSAGE_PAGE_SIZE: int = 50


def is_shown_in_widget(message: MessageDocument) -> bool:
    """
    The assistant's and staff's messages, and the platform's messages to the
    visitor (a booking's written confirmation with its manage link).
    """

    return message.author in WIDGET_MESSAGE_AUTHORS or (
        message.author is MessageAuthor.SYSTEM
        and message.direction is MessageDirection.OUTBOUND
    )


def build_widget_answer(
    later: list[MessageDocument],
    latest_id: MessageId | None,
    is_handed_off: bool,
    language_registry: LanguageRegistryContract,
) -> WidgetMessagesView:
    """The assistant's and staff's messages after the cursor, a page of them."""

    shown: list[MessageDocument] = [
        message for message in later if is_shown_in_widget(message)
    ]
    page: list[MessageDocument] = shown[:WIDGET_MESSAGE_PAGE_SIZE]
    has_more: bool = len(shown) > len(page)
    return WidgetMessagesView(
        items=[build_message_view(message, language_registry) for message in page],
        cursor=page[-1].id if has_more else latest_id,
        has_more=has_more,
        is_handed_off=is_handed_off,
    )


def build_message_view(
    message: MessageDocument,
    language_registry: LanguageRegistryContract,
) -> WidgetMessageView:
    direction: TextDirection = TextDirection.LEFT_TO_RIGHT
    if message.language is not None:
        try:
            direction = language_registry.get(message.language).direction
        except UnsupportedLanguageError:
            direction = TextDirection.LEFT_TO_RIGHT

    return WidgetMessageView(
        id=message.id,
        author=message.author,
        text=message.text,
        language=message.language,
        direction=direction,
        created_at=message.created_at,
        choices=[] if message.choices is None else list(message.choices.options),
        invites_rating=invites_rating(message),
    )
