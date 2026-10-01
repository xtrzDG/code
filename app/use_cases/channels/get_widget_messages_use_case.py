from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels import (
    WidgetMessagesQuery,
    WidgetMessagesView,
    WidgetMessageView,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnsupportedLanguageError,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.channels.delivery_targets import find_business_channel

# Messages the widget shows besides the visitor's own.
WIDGET_MESSAGE_AUTHORS: frozenset[MessageAuthor] = frozenset(
    {MessageAuthor.ASSISTANT, MessageAuthor.STAFF}
)
WIDGET_MESSAGE_PAGE_SIZE: int = 50


class GetWidgetMessagesUseCase(
    UseCaseContract[WidgetMessagesQuery, WidgetMessagesView]
):
    """
    The website widget polls for answers it has not shown yet: the
    assistant's and staff's messages of its visitor's conversations (the
    visitor is the widget's random session key) after the message `after`,
    oldest first, at most 50 at a time. Staff replies written in the
    cabinet after a handoff reach the visitor this way.

    The business must exist and have the widget switched on, else the chat
    is unavailable (the same answer for both). A visitor without a
    conversation gets nothing and no position; without `after`, or with a
    position the visitor does not have (erased data), only the current
    position is returned, so nothing already shown comes twice.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        language_registry: LanguageRegistryContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._language_registry: LanguageRegistryContract = language_registry

    def run(self, input_data: WidgetMessagesQuery) -> WidgetMessagesView:
        business: BusinessDocument = self._require_open_chat(input_data)
        conversations: list[ConversationDocument] = [
            conversation
            for conversation in self._conversation_repo.list_by_business(business.id)
            if conversation.channel is ChannelKind.WEB_CHAT
            and str(conversation.channel_user_id) == str(input_data.session_key)
            and not conversation.is_sandbox
        ]
        if not conversations:
            return WidgetMessagesView(items=[])

        # Conversations come newest first: the first one is the current one.
        is_handed_off: bool = conversations[0].status is ConversationStatus.HANDOFF
        messages: list[MessageDocument] = sorted(
            (
                message
                for conversation in conversations
                for message in self._message_repo.list_by_conversation(
                    business.id, conversation.id
                )
            ),
            key=lambda message: (int(message.created_at), str(message.id)),
        )
        latest_id: MessageId | None = messages[-1].id if messages else None
        start: int | None = find_position_after(messages, input_data.after)
        if start is None:
            return WidgetMessagesView(
                items=[], cursor=latest_id, is_handed_off=is_handed_off
            )

        shown: list[MessageDocument] = [
            message
            for message in messages[start:]
            if message.author in WIDGET_MESSAGE_AUTHORS
        ]
        page: list[MessageDocument] = shown[:WIDGET_MESSAGE_PAGE_SIZE]
        has_more: bool = len(shown) > len(page)
        return WidgetMessagesView(
            items=[self._build_view(message) for message in page],
            cursor=page[-1].id if has_more else latest_id,
            has_more=has_more,
            is_handed_off=is_handed_off,
        )

    def _require_open_chat(self, input_data: WidgetMessagesQuery) -> BusinessDocument:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        channel: ChannelDocument | None = (
            None
            if business is None
            else find_business_channel(
                self._channel_repo, business.id, ChannelKind.WEB_CHAT
            )
        )
        if (
            business is None
            or channel is None
            or channel.status is not ChannelStatus.CONNECTED
        ):
            raise NotFoundError("This chat is not available.")

        return business

    def _build_view(self, message: MessageDocument) -> WidgetMessageView:
        direction: TextDirection = TextDirection.LEFT_TO_RIGHT
        if message.language is not None:
            try:
                direction = self._language_registry.get(message.language).direction
            except UnsupportedLanguageError:
                direction = TextDirection.LEFT_TO_RIGHT

        return WidgetMessageView(
            id=message.id,
            author=message.author,
            text=message.text,
            language=message.language,
            direction=direction,
            created_at=message.created_at,
        )


def find_position_after(
    messages: list[MessageDocument],
    after: MessageId | None,
) -> int | None:
    """Index of the first message after `after`; None when it is unknown."""

    if after is None:
        return None

    for index, message in enumerate(messages):
        if message.id == after:
            return index + 1

    return None
