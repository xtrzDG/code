"""
Polls racing the answers of their chat miss none: while the answers are
written one after another (as a chat's are: one turn at a time), widgets
polling at the same moment through the one-statement read, each from its
own cursor, see every answer exactly once and in order. A poll reads one
snapshot, so an answer committed meanwhile is either in it or after the
cursor it returns.
"""

import threading

from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.postgres_widget_poll_read_adapter import (
    PostgresWidgetPollReadAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.widget_poll_world import SECOND, START, VISITOR, PollWorld

ANSWERS: int = 40
WIDGETS: int = 4


def test_polls_racing_the_answers_see_each_once_in_order(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
    storage_scope: StorageScopeContext,
) -> None:
    world = PollWorld(
        postgres_collections,
        PostgresReadSessionAdapter(connection_pool),
        PostgresWidgetPollReadAdapter(connection_pool, storage_scope),
    )
    with storage_scope.scoped_to_business(world.business_id):
        world.open_widget()
        conversation = world.add_conversation(VISITOR)
        question = world.add_message(conversation, MessageAuthor.CUSTOMER, START)
    start = threading.Barrier(WIDGETS + 1)
    written: list[MessageId] = []
    all_written = threading.Event()
    seen: dict[int, list[MessageId]] = {}

    def answer() -> None:
        with storage_scope.scoped_to_business(world.business_id):
            start.wait()
            for number in range(1, ANSWERS + 1):
                written.append(
                    world.add_message(
                        conversation,
                        MessageAuthor.ASSISTANT,
                        START + number * SECOND,
                    ).id
                )
        all_written.set()

    def poll(widget: int) -> None:
        shown: list[MessageId] = []
        cursor: MessageId = question.id
        with storage_scope.scoped_to_business(world.business_id):
            start.wait()
            while True:
                # A poll that began after the last answer was written and
                # brings nothing new means the widget has caught up.
                was_written = all_written.is_set()
                view = world.poll(cursor)
                shown.extend(item.id for item in view.items)
                cursor = view.cursor or cursor
                if was_written and not view.items and not view.has_more:
                    break
        seen[widget] = shown

    threads = [threading.Thread(target=answer)] + [
        threading.Thread(target=poll, args=(widget,)) for widget in range(WIDGETS)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(written) == ANSWERS
    assert seen == dict.fromkeys(range(WIDGETS), written)
