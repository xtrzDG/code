"""
Widget polls read the newest few messages first: for any chat (creation
times that tie, several conversations, a sandbox one, other visitors) and
any cursor, the answer is the one the whole chat gives, in memory and on
Postgres; a poll that finds nothing new in a long chat reads only the
newest messages.
"""

import random
from collections.abc import Sequence

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.contracts.storage import StorageReadSessionContract
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.registries.localization.language_registry import LanguageRegistry
from app.repositories.business_repositories import ChannelRepository
from app.repositories.conversation_repositories import (
    ConversationRepository,
    MessageRepository,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget import WidgetMessagesQuery, WidgetMessagesView
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.use_cases.channels.get_widget_messages_use_case import (
    GetWidgetMessagesUseCase,
    is_shown_in_widget,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory, PostgresCollectionFactory
from tests.storage.storage_testing import build_ticking_wall_clock

VISITOR: str = "v1_window_visitor_0001"
OTHER_VISITOR: str = "v1_window_visitor_0002"
SECOND: int = 1_000_000
START: int = 1_790_000_000 * SECOND
AUTHORS: tuple[MessageAuthor, ...] = (
    MessageAuthor.CUSTOMER,
    MessageAuthor.ASSISTANT,
    MessageAuthor.STAFF,
    MessageAuthor.SYSTEM,
)


class PollWorld:
    """One business with its widget on, its repositories and the poll."""

    def __init__(
        self,
        collections: CollectionFactory,
        read_session: StorageReadSessionContract | None = None,
    ) -> None:
        self.business_id = BusinessId()
        self.channels = ChannelRepository(collections(ChannelDocument, "channels"))
        self.conversations = ConversationRepository(
            collections(ConversationDocument, "conversations")
        )
        self.messages = MessageRepository(collections(MessageDocument, "messages"))
        # A poll every 5 s of the clock: far below the visitor's limit.
        self.poll_use_case = GetWidgetMessagesUseCase(
            self.channels,
            self.conversations,
            self.messages,
            LanguageRegistry(),
            RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter()),
            build_ticking_wall_clock(5 * SECOND),
            read_session,
        )

    def open_widget(self) -> None:
        self.channels.save(
            ChannelDocument(
                business_id=self.business_id,
                kind=ChannelKind.WEB_CHAT,
                status=ChannelStatus.CONNECTED,
            )
        )

    def add_conversation(
        self, visitor: str, is_sandbox: bool = False, is_handed_off: bool = False
    ) -> ConversationDocument:
        conversation = ConversationDocument(
            business_id=self.business_id,
            contact_id=ContactId(),
            assistant_version_id=AssistantVersionId(),
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId(visitor),
            is_sandbox=is_sandbox,
            status=(
                ConversationStatus.HANDOFF if is_handed_off else ConversationStatus.OPEN
            ),
            last_message_at=Microseconds(START),
            created_at=Microseconds(START),
            updated_at=Microseconds(START),
        )
        self.conversations.save(conversation)
        return conversation

    def add_message(
        self,
        conversation: ConversationDocument,
        author: MessageAuthor,
        created_at: int,
    ) -> MessageDocument:
        message = MessageDocument(
            conversation_id=conversation.id,
            business_id=self.business_id,
            direction=(
                MessageDirection.INBOUND
                if author is MessageAuthor.CUSTOMER
                else MessageDirection.OUTBOUND
            ),
            author=author,
            text=MessageText(f"{author.value} at {created_at}"),
            created_at=Microseconds(created_at),
            updated_at=Microseconds(created_at),
        )
        self.messages.save(message)
        return message

    def poll(self, after: MessageId | None) -> WidgetMessagesView:
        return self.poll_use_case.run(
            WidgetMessagesQuery(
                business_id=self.business_id,
                session_key=WidgetSessionKey(VISITOR),
                after=after,
            )
        )


def whole_chat_answer(
    conversations: Sequence[ConversationDocument],
    messages: Sequence[MessageDocument],
    after: MessageId | None,
) -> tuple[list[str], str | None, bool, bool]:
    """The answer computed from every message of the visitor's chat."""

    shown_conversations = [c for c in conversations if not c.is_sandbox]
    if not shown_conversations:
        return [], None, False, False

    newest = max(shown_conversations, key=lambda c: int(c.last_message_at))
    is_handed_off = newest.status is ConversationStatus.HANDOFF
    ids = {conversation.id for conversation in shown_conversations}
    chat = sorted(
        (message for message in messages if message.conversation_id in ids),
        key=lambda message: (int(message.created_at), str(message.id)),
    )
    latest = str(chat[-1].id) if chat else None
    positions = [index for index, message in enumerate(chat) if message.id == after]
    if not positions:
        customer = [m for m in chat if m.author is MessageAuthor.CUSTOMER]
        cursor = str(customer[-1].id) if customer else latest
        return [], cursor, False, is_handed_off

    shown = [m for m in chat[positions[0] + 1 :] if is_shown_in_widget(m)]
    page = shown[:50]
    has_more = len(shown) > len(page)
    cursor = str(page[-1].id) if has_more else latest
    return [str(m.id) for m in page], cursor, has_more, is_handed_off


def build_random_chat(
    world: PollWorld, chance: random.Random
) -> tuple[list[ConversationDocument], list[MessageDocument]]:
    """A visitor's chat whose creation times often tie, plus noise."""

    conversations = [
        world.add_conversation(VISITOR, is_handed_off=chance.random() < 0.3)
        for _ in range(chance.randint(1, 3))
    ]
    if chance.random() < 0.5:
        conversations.append(world.add_conversation(VISITOR, is_sandbox=True))
    noise = world.add_conversation(OTHER_VISITOR)
    messages: list[MessageDocument] = []
    for _ in range(chance.randint(0, 28)):
        conversation = chance.choice([*conversations, noise])
        moment = START + chance.randint(0, 12) * SECOND
        messages.append(world.add_message(conversation, chance.choice(AUTHORS), moment))
    return conversations, messages


@pytest.fixture
def read_session(
    collections: CollectionFactory, request: pytest.FixtureRequest
) -> StorageReadSessionContract | None:
    """On Postgres the polls read in a read session, as in the API."""

    if not isinstance(collections, PostgresCollectionFactory):
        return None

    return PostgresReadSessionAdapter(
        request.getfixturevalue("connection_pool"),
        request.getfixturevalue("storage_scope"),
    )


def test_every_cursor_gets_the_whole_chats_answer(
    collections: CollectionFactory,
    storage_scope: StorageScopeContext,
    read_session: StorageReadSessionContract | None,
) -> None:
    for seed in range(8):
        chance = random.Random(seed)
        world = PollWorld(collections, read_session)
        with storage_scope.scoped_to_business(world.business_id):
            world.open_widget()
            conversations, messages = build_random_chat(world, chance)
            # The current conversation is the one written to last.
            for conversation, offset in zip(
                conversations,
                chance.sample(range(1_000), len(conversations)),
                strict=True,
            ):
                conversation.last_message_at = Microseconds(START + offset)
                world.conversations.save(conversation)
            cursors: list[MessageId | None] = [
                None,
                MessageId(),
                *(message.id for message in messages),
            ]
            for after in cursors:
                answer = world.poll(after)

                assert (
                    [str(item.id) for item in answer.items],
                    None if answer.cursor is None else str(answer.cursor),
                    bool(answer.has_more),
                    bool(answer.is_handed_off),
                ) == whole_chat_answer(conversations, messages, after), (seed, after)


def test_a_caught_up_poll_of_a_long_chat_reads_only_the_newest(
    collections: CollectionFactory,
    storage_scope: StorageScopeContext,
    read_session: StorageReadSessionContract | None,
) -> None:
    world = PollWorld(collections, read_session)
    with storage_scope.scoped_to_business(world.business_id):
        world.open_widget()
        conversation = world.add_conversation(VISITOR)
        chat = [
            world.add_message(
                conversation,
                MessageAuthor.CUSTOMER if number % 2 == 0 else MessageAuthor.ASSISTANT,
                START + number * SECOND,
            )
            for number in range(120)
        ]
        positions = world.messages.page_newest_positions_of_conversations(
            world.business_id, [conversation.id, conversation.id], window_of(3)
        )
        no_positions = world.messages.page_newest_positions_of_conversations(
            world.business_id, [], window_of(3)
        )
        caught_up = world.poll(chat[-1].id)
        two_new = world.poll(chat[-3].id)

    assert [(p.id, p.created_at) for p in positions] == [
        (m.id, m.created_at) for m in reversed(chat[-3:])
    ]
    assert no_positions == []
    assert caught_up.items == []
    assert caught_up.cursor == chat[-1].id
    assert [item.id for item in two_new.items] == [chat[-1].id]
    assert two_new.cursor == chat[-1].id


def window_of(size: int) -> KeysetSlice:
    return KeysetSlice(limit=KeysetReadLimit(size))
