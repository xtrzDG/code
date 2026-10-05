"""
The cabinet's keyset pages and the dashboard's counts use their indexes on
tables of realistic size under forced row-level security: the statements
the repositories really run are recorded and replayed with EXPLAIN.
"""

from collections.abc import Callable, Generator
from contextlib import suppress

import pytest
from pydantic import ValidationError
from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.conversation_repositories import ContactRepository
from app.repositories.knowledge_repositories import KnowledgeItemRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName, FoldedContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.paging.keyset_paging import single_value_position
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory
from tests.storage.hot_path_queries import INDEX_NODE_TYPES
from tests.storage.hot_path_seeding import (
    RecordingConnectionPool,
    analyze,
    explain,
    plan_nodes,
)
from tests.storage.list_query_plans import (
    BUSINESS,
    LIST_BUSINESS_IDS,
    LIST_QUERIES,
    ListQuery,
    ListRepositories,
)
from tests.storage.list_query_rows import seed_list_tables
from tests.storage.lookup_list_query_plans import LOOKUP_LIST_QUERIES
from tests.storage.postgres_server import ThrowawayPostgresServer


@pytest.fixture(scope="module")
def list_database_url(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
) -> Generator[DatabaseUrl]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(database_name), max_size=1
    )
    try:
        seed_list_tables(connection_pool, LIST_BUSINESS_IDS)
        analyze(connection_pool)
        connection_pool.close()
        yield postgres_server.app_database_url(database_name)
    finally:
        connection_pool.close()
        postgres_server.drop_database(database_name)


@pytest.mark.parametrize(
    "query", LIST_QUERIES + LOOKUP_LIST_QUERIES, ids=lambda query: query.name
)
def test_list_query_uses_its_index(
    list_database_url: DatabaseUrl, query: ListQuery
) -> None:
    recording_pool = RecordingConnectionPool(list_database_url)
    explaining_pool = PostgresConnectionPoolClient(list_database_url, max_size=1)
    storage_scope = StorageScopeContext()
    repositories = ListRepositories(recording_pool, storage_scope)
    try:
        # The seeded rows carry only their lookup fields and do not decode;
        # the recorded SQL is what this test checks.
        with (
            storage_scope.platform_wide()
            if query.is_platform_wide
            else storage_scope.scoped_to_business(BUSINESS),
            suppress(ValidationError, ApplicationError),
        ):
            query.run(repositories)

        plans = [
            plan
            for transaction in recording_pool.transactions
            for plan in explain(explaining_pool, transaction)
        ]
    finally:
        recording_pool.close()
        explaining_pool.close()

    assert plans, "the repository ran no query"
    summary = [describe(plan) for plan in plans]
    for plan in plans:
        nodes = plan_nodes(plan)
        assert not [
            node
            for node in nodes
            if node["Node Type"] == "Seq Scan"
            and node.get("Relation Name") in (query.table, *query.also_tables)
        ], f"{query.name}: sequential scan of {query.table}: {plan}"
        assert any(
            node["Node Type"] in INDEX_NODE_TYPES
            and node.get("Index Name") in (query.index, *query.alternatives)
            for node in nodes
        ), f"{query.name}: {query.index} is not used: {summary}"


def describe(plan: dict[str, object]) -> list[str]:
    """The node types and indexes of a plan, for a readable failure."""

    return [
        f"{node['Node Type']}:{node.get('Index Name') or node.get('Relation Name')}"
        for node in plan_nodes(plan)
    ]


def walk_pages[Item](
    read: Callable[[KeysetSlice], list[Item]],
    position: Callable[[Item], KeysetPosition],
    size: int,
) -> list[list[Item]]:
    """Every keyset page of a repository list, `size` at a time."""

    pages: list[list[Item]] = []
    after: KeysetPosition | None = None
    while True:
        page: list[Item] = read(KeysetSlice(after=after, limit=KeysetReadLimit(size)))
        if not page:
            return pages

        pages.append(page)
        after = position(page[-1])


@pytest.mark.usefixtures("platform_scope")
def test_customers_page_most_recently_active_first(
    collections: CollectionFactory,
) -> None:
    contacts = ContactRepository(collections(ContactDocument, "contacts"))
    business_id = BusinessId()
    seen = [5, 9, 9, 2, 7, 9, 1]
    for index, moment in enumerate(seen):
        contacts.save(
            ContactDocument(
                business_id=business_id,
                name=ContactName(f"Guest {index}"),
                last_seen_at=Microseconds(moment),
            )
        )
    contacts.save(
        ContactDocument(
            business_id=business_id,
            channel_identities=[
                ChannelIdentity(
                    channel=ChannelKind.OWNER_TEST,
                    channel_user_id=ChannelUserId("owner:1:default"),
                )
            ],
        )
    )
    contacts.save(
        ContactDocument(business_id=BusinessId(), last_seen_at=Microseconds(10))
    )

    pages = walk_pages(
        lambda window: contacts.page_by_last_seen(business_id, window),
        lambda contact: single_value_position(
            int(contact.last_seen_at or 0), str(contact.id)
        ),
        3,
    )

    # Ties keep the order they were written in, latest first.
    assert [[str(contact.name) for contact in page] for page in pages] == [
        ["Guest 5", "Guest 2", "Guest 1"],
        ["Guest 4", "Guest 0", "Guest 3"],
        ["Guest 6"],
    ]
    assert [
        str(contact.name)
        for contact in contacts.list_by_folded_name(
            business_id, FoldedContactName("guest 4")
        )
    ] == ["Guest 4"]


@pytest.mark.usefixtures("platform_scope")
def test_knowledge_pages_last_changed_first_of_one_kind(
    collections: CollectionFactory,
) -> None:
    knowledge = KnowledgeItemRepository(
        collections(KnowledgeItemDocument, "knowledge_items")
    )
    business_id = BusinessId()
    for index in range(7):
        knowledge.save(
            KnowledgeItemDocument(
                business_id=business_id,
                kind=KnowledgeItemKind.FAQ
                if index % 2
                else KnowledgeItemKind.MENU_ITEM,
                title=KnowledgeTitle(f"Item {index}"),
                is_active=index != 3,
                updated_at=Microseconds(100 - index * 10 if index != 4 else 500),
            )
        )

    def titles(kind: KnowledgeItemKind | None, is_active: bool | None) -> list[str]:
        pages = walk_pages(
            lambda window: knowledge.page_by_business(
                business_id, window, kind, is_active
            ),
            lambda item: single_value_position(int(item.updated_at), str(item.id)),
            2,
        )
        return [str(item.title) for page in pages for item in page]

    assert titles(None, None) == [f"Item {index}" for index in (4, 0, 1, 2, 3, 5, 6)]
    assert titles(KnowledgeItemKind.FAQ, None) == ["Item 1", "Item 3", "Item 5"]
    assert titles(None, False) == ["Item 3"]
    assert titles(KnowledgeItemKind.MENU_ITEM, True) == [
        "Item 4",
        "Item 0",
        "Item 2",
        "Item 6",
    ]
