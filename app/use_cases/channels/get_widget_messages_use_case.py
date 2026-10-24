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
from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
)
from app.contracts.storage import StorageReadSessionContract
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.widget_poll_reads import WidgetPollReadAdapterContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.channels.widget import WidgetMessagesQuery, WidgetMessagesView
from app.schemas.dto.channels.widget_poll_reads import WidgetPollRead
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.use_cases.channels.open_chat_memory import OpenChatMemory
from app.use_cases.channels.widget_message_window import (
    covers_from_cursor,
    find_latest_visitor_message_id,
    find_position_after,
    ids_after_cursor,
    message_order,
)
from app.use_cases.channels.widget_poll_answers import build_widget_answer
from app.use_cases.channels.widget_poll_reading import read_poll_through_repositories
from app.use_cases.shared.storage_transaction import in_read_session
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.widget_rate_limits import (
    WIDGET_POLL_LIMITS,
    refuse_too_frequent_widget_requests,
)
from app.utilities.spend.widget_origins import is_origin_allowed

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

    The endpoint is public, so polls are limited first, per visitor, per
    client network, per business and for the platform (429 with
    Retry-After, `WIDGET_POLL_LIMITS`; the visitor and network counts are
    one statement, the business and platform counters come from this
    process's leases). Then one read (`WidgetPollReadAdapterContract`: one
    statement and one round trip on Postgres; the repositories without it)
    brings the business's allowed websites, the visitor's conversations
    and where their newest `RECENT_MESSAGE_WINDOW` messages stand, with the
    messages after the cursor among them in full. A page the business does
    not allow is refused (403, as for every widget route; a request that
    names no page passes), then a chat that is not switched on (404, the
    same for an unknown business): its web chat channel is connected. A
    chat found open is believed open for `OPEN_CHAT_MEMORY_SECONDS` without
    reading the channel again (`OpenChatMemory`: a widget switched off
    stops answering polls within that time, one switched on answers at
    once), so the use case is a singleton of the container.

    A visitor without a conversation gets nothing and no position. When
    the newest messages hold the cursor and reach back past it, the answer
    is the whole chat's (`widget_message_window`); only a longer backlog,
    an unknown cursor or none reads the whole chat (in a read session).
    Without `after`, or with a position the visitor does not have (erased
    data), no messages come but a position: the visitor's latest own
    message, so an answer the widget missed (the page was left while it
    was being written) comes with the next poll; the widget skips answers
    it already shows by id. Only the visitor's own conversations and
    messages are read, by indexed lookups.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        business_limits_repo: BusinessLimitsRepoContract,
        language_registry: LanguageRegistryContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
        platform_origins: list[PublicBaseUrl],
        read_session: StorageReadSessionContract | None = None,
        poll_reads: WidgetPollReadAdapterContract | None = None,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._business_limits_repo: BusinessLimitsRepoContract = business_limits_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._platform_origins: list[str] = [str(o) for o in platform_origins]
        self._read_session: StorageReadSessionContract | None = read_session
        self._poll_reads: WidgetPollReadAdapterContract | None = poll_reads
        self._open_chats: OpenChatMemory = OpenChatMemory()

    def run(self, input_data: WidgetMessagesQuery) -> WidgetMessagesView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_POLL_LIMITS,
            business_id=input_data.business_id,
            session_key=input_data.session_key,
            client_ip_address=input_data.client_ip_address,
            now=now,
        )
        read: WidgetPollRead = self._read(input_data)
        if not is_origin_allowed(
            input_data.page_origin, read.allowed_origins, self._platform_origins
        ):
            raise AccessDeniedError("This chat is not available on this website.")

        self._require_open_chat(input_data.business_id, now)
        return self._answer(input_data, read)

    def _read(self, input_data: WidgetMessagesQuery) -> WidgetPollRead:
        visitor = ChannelUserId(str(input_data.session_key))
        if self._poll_reads is not None:
            return self._poll_reads.read_poll(
                input_data.business_id, visitor, input_data.after, RECENT_MESSAGE_WINDOW
            )

        with in_read_session(self._read_session):
            return read_poll_through_repositories(
                self._conversation_repo,
                self._message_repo,
                self._business_limits_repo,
                input_data.business_id,
                visitor,
                input_data.after,
                RECENT_MESSAGE_WINDOW,
            )

    def _answer(
        self, input_data: WidgetMessagesQuery, read: WidgetPollRead
    ) -> WidgetMessagesView:
        if not read.conversations:
            return WidgetMessagesView(items=[])

        # Conversations come newest first: the first one is the current one.
        is_handed_off: bool = read.conversations[0].status is ConversationStatus.HANDOFF
        settled: tuple[list[MessageDocument], MessageId] | None = settle_from_newest(
            read, input_data.after
        )
        if settled is not None:
            later, latest_id = settled
            return build_widget_answer(
                later, latest_id, is_handed_off, self._language_registry
            )

        with in_read_session(self._read_session):
            messages: list[MessageDocument] = sorted(
                (
                    message
                    for conversation in read.conversations
                    for message in self._message_repo.list_by_conversation(
                        input_data.business_id, conversation.id
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

        return build_widget_answer(
            messages[start:], last_id, is_handed_off, self._language_registry
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


def settle_from_newest(
    read: WidgetPollRead,
    after: MessageId | None,
) -> tuple[list[MessageDocument], MessageId] | None:
    """
    When the newest messages hold the cursor and everything from it on (a
    poll that finds nothing new or a few answers): the messages after the
    cursor in answer order (one erased meanwhile is left out), and the
    latest message's id. None when the whole chat must be read.
    """

    newest: list[MessagePosition] | None = read.newest
    if (
        after is None
        or not newest
        or not covers_from_cursor(newest, after, RECENT_MESSAGE_WINDOW)
    ):
        return None

    found: dict[MessageId, MessageDocument] = {
        message.id: message for message in read.after_cursor
    }
    later: list[MessageDocument] = [
        found[message_id]
        for message_id in ids_after_cursor(newest, after)
        if message_id in found
    ]
    return later, max(newest, key=message_order).id
