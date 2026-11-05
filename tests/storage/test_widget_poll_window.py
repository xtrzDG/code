"""
Widget polls read the newest few messages first: for any chat (creation
times that tie, several conversations, a sandbox one, other visitors) and
any cursor, the answer is the one the whole chat gives, in memory and on
Postgres, through the repositories and through the one-statement read the
API uses on Postgres; a poll that finds nothing new in a long chat reads
only the newest messages.
"""

import random

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.postgres_widget_poll_read_adapter import (
    PostgresWidgetPollReadAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.storage import StorageReadSessionContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory, PostgresCollectionFactory
from tests.storage.widget_poll_world import (
    SECOND,
    START,
    VISITOR,
    PollWorld,
    build_random_chat,
    whole_chat_answer,
)


@pytest.fixture
def read_session(
    collections: CollectionFactory,
    request: pytest.FixtureRequest,
    storage_scope: StorageScopeContext,
) -> StorageReadSessionContract | None:
    """On Postgres the polls read in a read session, as in the API."""

    if not isinstance(collections, PostgresCollectionFactory):
        return None

    return PostgresReadSessionAdapter(
        request.getfixturevalue("connection_pools"), storage_scope
    )


def check_every_cursor(
    worlds: list[PollWorld], storage_scope: StorageScopeContext
) -> None:
    """Random chats (one per world), each polled from every cursor."""

    for seed, world in enumerate(worlds):
        chance = random.Random(seed)
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


def test_every_cursor_gets_the_whole_chats_answer(
    collections: CollectionFactory,
    storage_scope: StorageScopeContext,
    read_session: StorageReadSessionContract | None,
) -> None:
    check_every_cursor(
        [PollWorld(collections, read_session) for _ in range(8)], storage_scope
    )


def test_the_one_statement_read_gives_every_cursor_the_whole_chats_answer(
    postgres_collections: PostgresCollectionFactory,
    connection_pools: PostgresConnectionPools,
    storage_scope: StorageScopeContext,
) -> None:
    session = PostgresReadSessionAdapter(connection_pools, storage_scope)
    poll_reads = PostgresWidgetPollReadAdapter(connection_pools, storage_scope)

    check_every_cursor(
        [PollWorld(postgres_collections, session, poll_reads) for _ in range(8)],
        storage_scope,
    )


def test_a_caught_up_poll_of_a_long_chat_reads_only_the_newest(
    collections: CollectionFactory,
    storage_scope: StorageScopeContext,
    read_session: StorageReadSessionContract | None,
) -> None:
    check_long_chat(PollWorld(collections, read_session), storage_scope)


def test_a_caught_up_one_statement_poll_of_a_long_chat(
    postgres_collections: PostgresCollectionFactory,
    connection_pools: PostgresConnectionPools,
    storage_scope: StorageScopeContext,
) -> None:
    world = PollWorld(
        postgres_collections,
        PostgresReadSessionAdapter(connection_pools, storage_scope),
        PostgresWidgetPollReadAdapter(connection_pools, storage_scope),
    )

    check_long_chat(world, storage_scope)


def check_long_chat(world: PollWorld, storage_scope: StorageScopeContext) -> None:
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
