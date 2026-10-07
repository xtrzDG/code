from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    LanguageRegistryContract,
    RequestRateLimitRegistryContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.storage import StorageReadSessionContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import (
    ChannelKind,
    ChannelStatus,
    MessageDirection,
)
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget import (
    WidgetMessagesQuery,
    WidgetMessagesView,
    WidgetMessageView,
)
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.dto.paging import KeysetSlice
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnsupportedLanguageError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.use_cases.channels.open_chat_memory import OpenChatMemory
from app.use_cases.channels.widget_message_window import (
    covers_from_cursor,
    find_latest_visitor_message_id,
    find_position_after,
    message_order,
)
from app.use_cases.shared.storage_transaction import in_read_session
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.widget_rate_limits import (
    WIDGET_POLL_LIMITS,
    refuse_too_frequent_widget_requests,
)

# Messages the widget shows besides the visitor's own.
WIDGET_MESSAGE_AUTHORS: frozenset[MessageAuthor] = frozenset(
    {MessageAuthor.ASSISTANT, MessageAuthor.STAFF}
)
WIDGET_MESSAGE_PAGE_SIZE: int = 50
# The newest messages a poll reads first: a poll every few seconds finds a
# few new ones at most, and the cursor among these settles it.
RECENT_MESSAGE_WINDOW: KeysetReadLimit = KeysetReadLimit(10)


class GetWidgetMessagesUseCase(
    UseCaseContract[WidgetMessagesQuery, WidgetMessagesView]
):
    """
    The website widget polls for answers it has not shown yet: the
    assistant's, staff's and the platform's messages (a booking's written
    confirmation) of its visitor's conversations (the
    visitor is the widget's random session key) after the message `after`,
    oldest first, at most 50 at a time. Staff replies written in the
    cabinet after a handoff reach the visitor this way.

    The business must have the widget switched on, else the chat is
    unavailable (the same answer for an unknown business): its web chat
    channel is connected. A channel exists only for an existing business
    (businesses are never deleted), so the channel alone answers it. A chat
    found open is believed open for `OPEN_CHAT_MEMORY_SECONDS` without
    reading the channel again (`OpenChatMemory`: a widget switched off
    stops answering polls within that time, one switched on answers at
    once), so the use case is a singleton of the container. A
    visitor without a conversation gets nothing and no position. Without
    `after`, or with a position the visitor does not have (erased data), no
    messages come but a position: the visitor's latest own message, so an
    answer the widget missed (the page was left while it was being
    written) comes with the next poll; the widget skips answers it already
    shows by id.

    The endpoint is public, so polls are limited per visitor, per client
    network, per business and for the platform (429 with Retry-After,
    `WIDGET_POLL_LIMITS`), and only the visitor's own conversations and
    messages are read (indexed lookups, not the whole business): first
    where the newest `RECENT_MESSAGE_WINDOW` of them stand (ids and times
    from the index), which settle a poll whose cursor is among them, and
    then in full only the messages after the cursor; only a longer
    backlog, an unknown cursor or none reads the visitor's whole chat
    (`widget_message_window`). The reads share one read session (one
    transaction on Postgres); the count of the poll comes before it, in its
    own statement.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        language_registry: LanguageRegistryContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
        read_session: StorageReadSessionContract | None = None,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._read_session: StorageReadSessionContract | None = read_session
        self._open_chats: OpenChatMemory = OpenChatMemory()

    def run(self, input_data: WidgetMessagesQuery) -> WidgetMessagesView:
        now: Microseconds = self._wall_clock.now_unix()
        self._refuse_too_frequent_polls(input_data, now)
        with in_read_session(self._read_session):
            self._require_open_chat(input_data.business_id, now)
            return self._answer(input_data)

    def _answer(self, input_data: WidgetMessagesQuery) -> WidgetMessagesView:
        conversations: list[ConversationDocument] = [
            conversation
            for conversation in self._conversation_repo.list_by_channel_user(
                input_data.business_id,
                ChannelKind.WEB_CHAT,
                ChannelUserId(str(input_data.session_key)),
            )
            if not conversation.is_sandbox
        ]
        if not conversations:
            return WidgetMessagesView(items=[])

        # Conversations come newest first: the first one is the current one.
        is_handed_off: bool = conversations[0].status is ConversationStatus.HANDOFF
        conversation_ids: list[ConversationId] = [
            conversation.id for conversation in conversations
        ]
        from_newest: tuple[list[MessageDocument], MessageId] | None = (
            self._read_from_newest(
                input_data.business_id, conversation_ids, input_data.after
            )
        )
        if from_newest is not None:
            later, latest_id = from_newest
            return self._build_answer(later, latest_id, is_handed_off)

        messages: list[MessageDocument] = sorted(
            (
                message
                for conversation_id in conversation_ids
                for message in self._message_repo.list_by_conversation(
                    input_data.business_id, conversation_id
                )
            ),
            key=message_order,
        )
        last_id: MessageId | None = messages[-1].id if messages else None
        start: int | None = find_position_after(messages, input_data.after)
        if start is None:
            return WidgetMessagesView(
                items=[],
                cursor=find_latest_visitor_message_id(messages) or last_id,
                is_handed_off=is_handed_off,
            )

        return self._build_answer(messages[start:], last_id, is_handed_off)

    def _read_from_newest(
        self,
        business_id: BusinessId,
        conversation_ids: list[ConversationId],
        after: MessageId | None,
    ) -> tuple[list[MessageDocument], MessageId] | None:
        """
        When the newest few messages hold the cursor and everything from it
        on (a poll that finds nothing new or a few answers): the messages
        after the cursor in answer order, and the latest message's id. Only
        the positions of the newest are read, and in full only the messages
        after the cursor (one erased in between is left out). None when the
        whole chat must be read.
        """

        if after is None:
            return None

        newest: list[MessagePosition] = (
            self._message_repo.page_newest_positions_of_conversations(
                business_id, conversation_ids, KeysetSlice(limit=RECENT_MESSAGE_WINDOW)
            )
        )
        if not covers_from_cursor(newest, after, RECENT_MESSAGE_WINDOW):
            return None

        window: list[MessagePosition] = sorted(newest, key=message_order)
        start: int | None = find_position_after(window, after)
        if start is None:  # a covering window holds the cursor
            return None

        later_ids: list[MessageId] = [position.id for position in window[start:]]
        found: dict[MessageId, MessageDocument] = (
            self._message_repo.get_many(business_id, later_ids) if later_ids else {}
        )
        return (
            [found[message_id] for message_id in later_ids if message_id in found],
            window[-1].id,
        )

    def _build_answer(
        self,
        later: list[MessageDocument],
        latest_id: MessageId | None,
        is_handed_off: bool,
    ) -> WidgetMessagesView:
        """The assistant's and staff's messages after the cursor, a page of them."""

        shown: list[MessageDocument] = [
            message for message in later if is_shown_in_widget(message)
        ]
        page: list[MessageDocument] = shown[:WIDGET_MESSAGE_PAGE_SIZE]
        has_more: bool = len(shown) > len(page)
        return WidgetMessagesView(
            items=[self._build_view(message) for message in page],
            cursor=page[-1].id if has_more else latest_id,
            has_more=has_more,
            is_handed_off=is_handed_off,
        )

    def _refuse_too_frequent_polls(
        self, input_data: WidgetMessagesQuery, now: Microseconds
    ) -> None:
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_POLL_LIMITS,
            business_id=input_data.business_id,
            session_key=input_data.session_key,
            client_ip_address=input_data.client_ip_address,
            now=now,
        )

    def _require_open_chat(self, business_id: BusinessId, now: Microseconds) -> None:
        if self._open_chats.is_open(business_id, now):
            return

        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo, business_id, ChannelKind.WEB_CHAT
        )
        if channel is None or channel.status is not ChannelStatus.CONNECTED:
            self._open_chats.forget(business_id)
            raise NotFoundError("This chat is not available.")

        self._open_chats.remember_open(business_id, now)

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
            choices=[] if message.choices is None else list(message.choices.options),
        )


def is_shown_in_widget(message: MessageDocument) -> bool:
    """
    The assistant's and staff's messages, and the platform's messages to the
    visitor (a booking's written confirmation with its manage link).
    """

    return message.author in WIDGET_MESSAGE_AUTHORS or (
        message.author is MessageAuthor.SYSTEM
        and message.direction is MessageDirection.OUTBOUND
    )
