"""
A keyset walk (`page_by`, newest first) while documents are written
between its pages, by another thread: every document that was there when
the walk began is visited exactly once, none twice, in order; a document
written behind the walk's position is visited, one written ahead of it is
not. The in-memory store and Postgres walk the very same way.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import InMemoryCollectionFactory, PostgresCollectionFactory
from tests.storage.test_document_pages import conversation, feed_query

pytestmark = pytest.mark.usefixtures("platform_scope")

type Conversations = DocumentCollectionAdapterContract[ConversationDocument]


@dataclass(frozen=True)
class Plan:
    """Documents at the start, the page size, and (after page, time) writes."""

    initial: list[int]
    page_size: int
    writes: list[tuple[int, int]]


plans = st.builds(
    Plan,
    initial=st.lists(st.integers(min_value=10, max_value=60), max_size=24),
    page_size=st.integers(min_value=1, max_value=6),
    writes=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=8),
            st.integers(min_value=1, max_value=70),
        ),
        max_size=10,
    ),
)


class Writer:
    """Another thread that writes a document each time the walk asks it to."""

    def __init__(self, write: Callable[[ConversationDocument], None]) -> None:
        self._write = write
        self._lock = threading.Lock()

    def write_from_another_thread(self, document: ConversationDocument) -> None:
        with self._lock:
            done = threading.Event()

            def run() -> None:
                self._write(document)
                done.set()

            thread = threading.Thread(target=run)
            thread.start()
            thread.join()
            assert done.is_set()


@dataclass(frozen=True)
class Walk:
    visited: list[ConversationId]
    behind: set[ConversationId]
    ahead: set[ConversationId]


def walk(
    conversations: Conversations,
    writer: Writer,
    business_id: BusinessId,
    plan: Plan,
    written: list[ConversationDocument],
) -> Walk:
    """Page through; after page n, the writes planned for n happen elsewhere."""

    visited: list[ConversationId] = []
    behind: set[ConversationId] = set()
    ahead: set[ConversationId] = set()
    after: ConversationDocument | None = None
    planned = list(zip((page for page, _ in plan.writes), written, strict=True))
    page_index = 0
    while True:
        page = conversations.page_by(feed_query(business_id, plan.page_size, after))
        visited.extend(document.id for document in page)
        if len(page) < plan.page_size:
            return Walk(visited, behind, ahead)
        after = page[-1]
        for document in [doc for page_of, doc in planned if page_of == page_index]:
            writer.write_from_another_thread(document)
            if document.last_message_at < after.last_message_at:
                behind.add(document.id)
            elif document.last_message_at > after.last_message_at:
                ahead.add(document.id)
        page_index += 1


def run_plan(
    conversations: Conversations,
    scope: StorageScopeContext | None,
    plan: Plan,
    business_id: BusinessId,
    initial: list[ConversationDocument],
    written: list[ConversationDocument],
) -> Walk:
    for document in initial:
        conversations.upsert(str(document.id), document)

    def write(document: ConversationDocument) -> None:
        if scope is None:
            conversations.upsert(str(document.id), document)
            return
        with scope.platform_wide():
            conversations.upsert(str(document.id), document)

    return walk(conversations, Writer(write), business_id, plan, written)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=40)
@given(plans)
def test_a_walk_visits_every_document_once_while_others_are_written(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
    plan: Plan,
) -> None:
    business_id = BusinessId()
    initial = [conversation(business_id, at) for at in plan.initial]
    written = [conversation(business_id, at) for _, at in plan.writes]
    stores = {
        "in_memory": InMemoryCollectionFactory()(ConversationDocument, "conversations"),
        "postgres": postgres_collections(ConversationDocument, "conversations"),
    }

    walks = {
        name: run_plan(
            store,
            storage_scope if name == "postgres" else None,
            plan,
            business_id,
            initial,
            written,
        )
        for name, store in stores.items()
    }

    for name, result in walks.items():
        assert len(result.visited) == len(set(result.visited)), name
        assert {document.id for document in initial} <= set(result.visited), name
        assert result.behind <= set(result.visited), name
        assert not (result.ahead & set(result.visited)), name
        times = {
            document.id: int(document.last_message_at)
            for document in [*initial, *written]
        }
        assert [times[i] for i in result.visited] == sorted(
            (times[i] for i in result.visited), reverse=True
        ), name
    assert walks["in_memory"].visited == walks["postgres"].visited
