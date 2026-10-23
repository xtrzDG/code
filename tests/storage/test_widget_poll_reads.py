"""
The widget poll's one-statement read (`PostgresWidgetPollReadAdapter`):
only the asked business's rows reach it and row-level security binds it in
the ambient scope (another business's scope reads nothing, no scope is
refused); its scope ends with its pipelined transaction, so the pooled
connection keeps none; inside a unit of work it runs in a savepoint, inside
a read session in the session's transaction. A poll from a website the
business does not allow is refused, through the repositories and through
the one statement alike.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.adapters.storage.postgres.postgres_widget_poll_read_adapter import (
    PostgresWidgetPollReadAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.channels.widget_poll_reads import WidgetPollRead
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
)
from app.schemas.exceptions.storage_errors import UnscopedStorageAccessError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.spend.spend_keys import business_limits_id_of
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import (
    CollectionFactory,
    InMemoryCollectionFactory,
    PostgresCollectionFactory,
)
from tests.storage.postgres_roles import RoleDatabase
from tests.storage.widget_poll_world import SECOND, START, VISITOR, PollWorld

WINDOW: KeysetReadLimit = KeysetReadLimit(10)
ALLOWED: str = "https://cafe.example"


def chat_of(
    world: PollWorld, storage_scope: StorageScopeContext
) -> list[MessageDocument]:
    """The visitor asked, was answered twice; the business allows one site."""

    with storage_scope.scoped_to_business(world.business_id):
        world.open_widget()
        world.limits.save(
            BusinessLimitsDocument(
                id=business_limits_id_of(world.business_id),
                business_id=world.business_id,
                widget_allowed_origins=[PublicBaseUrl(ALLOWED)],
            )
        )
        conversation = world.add_conversation(VISITOR)
        return [
            world.add_message(conversation, author, START + number * SECOND)
            for number, author in enumerate(
                [MessageAuthor.CUSTOMER, MessageAuthor.ASSISTANT, MessageAuthor.STAFF]
            )
        ]


def read(
    reader: PostgresWidgetPollReadAdapter, world: PollWorld, chat: list[MessageDocument]
) -> WidgetPollRead:
    return reader.read_poll(
        world.business_id, ChannelUserId(VISITOR), chat[0].id, WINDOW
    )


def test_a_poll_reads_only_its_business_in_its_scope(
    postgres_collections: PostgresCollectionFactory,
    connection_pools: PostgresConnectionPools,
    storage_scope: StorageScopeContext,
) -> None:
    reader = PostgresWidgetPollReadAdapter(connection_pools, storage_scope)
    ours, theirs = PollWorld(postgres_collections), PollWorld(postgres_collections)
    our_chat, their_chat = chat_of(ours, storage_scope), chat_of(theirs, storage_scope)

    with storage_scope.scoped_to_business(ours.business_id):
        own = read(reader, ours, our_chat)
        # Their visitor key is the same; their rows stay theirs.
        foreign = read(reader, theirs, their_chat)
    with storage_scope.platform_wide():
        across = read(reader, ours, our_chat)

    assert [str(origin) for origin in own.allowed_origins] == [ALLOWED]
    assert [c.business_id for c in own.conversations] == [ours.business_id]
    assert {p.id for p in own.newest or []} == {m.id for m in our_chat}
    assert [m.id for m in own.after_cursor] == [m.id for m in our_chat[1:]]
    assert foreign == WidgetPollRead(newest=[])
    # Platform-wide, the explicit business filter still holds.
    assert across == own
    with pytest.raises(UnscopedStorageAccessError):
        read(reader, ours, our_chat)


def test_the_pipelined_scope_ends_with_the_read(
    postgres_collections: PostgresCollectionFactory,
    role_urls: RoleDatabase,
    storage_scope: StorageScopeContext,
) -> None:
    world = PollWorld(postgres_collections)
    chat = chat_of(world, storage_scope)
    # One connection per pool: the read's own is the one checked after it.
    pools = role_urls.pools(max_size=1)
    reader = PostgresWidgetPollReadAdapter(pools, storage_scope)
    try:
        with storage_scope.scoped_to_business(world.business_id):
            found = read(reader, world, chat)
        with pools.tenant.connection() as connection:
            settings = connection.execute(
                "select coalesce(current_setting('app.business_id', true), ''), "
                "coalesce(current_setting('app.bypass_rls', true), '')"
            ).fetchone()
            visible = connection.execute(
                "select count(*) from workshop.messages"
            ).fetchone()
    finally:
        pools.close()

    assert len(found.after_cursor) == 2
    assert settings == ("", "")
    # Without a scope the tenant role's connection sees no business's row.
    assert visible == (0,)


def test_inside_a_unit_of_work_or_a_read_session_it_reads_the_same(
    postgres_collections: PostgresCollectionFactory,
    connection_pools: PostgresConnectionPools,
    storage_scope: StorageScopeContext,
) -> None:
    world = PollWorld(postgres_collections)
    chat = chat_of(world, storage_scope)
    reader = PostgresWidgetPollReadAdapter(connection_pools, storage_scope)
    unit_of_work = PostgresUnitOfWorkAdapter(connection_pools, storage_scope)
    read_session = PostgresReadSessionAdapter(connection_pools, storage_scope)

    with storage_scope.scoped_to_business(world.business_id):
        alone = read(reader, world, chat)
        with unit_of_work.unit_of_work():
            in_unit = read(reader, world, chat)
            world.add_message(
                world.conversations.get(world.business_id, chat[0].conversation_id)
                or pytest.fail("no conversation"),
                MessageAuthor.ASSISTANT,
                START + 9 * SECOND,
            )
        with read_session.read_session():
            in_session = read(reader, world, chat)
            in_session_again = read(reader, world, chat)

    assert in_unit == alone
    # The unit of work went on after the read and committed its write.
    assert len(in_session.after_cursor) == 3
    assert in_session_again == in_session


@pytest.mark.parametrize("is_one_statement", [False, True])
def test_a_poll_from_a_website_the_business_does_not_allow_is_refused(
    collections: CollectionFactory,
    request: pytest.FixtureRequest,
    storage_scope: StorageScopeContext,
    is_one_statement: bool,
) -> None:
    reader: PostgresWidgetPollReadAdapter | None = None
    if is_one_statement and isinstance(collections, PostgresCollectionFactory):
        reader = PostgresWidgetPollReadAdapter(
            request.getfixturevalue("connection_pools"), storage_scope
        )
    world = PollWorld(collections, poll_reads=reader)
    chat = chat_of(world, storage_scope)

    with storage_scope.scoped_to_business(world.business_id):
        with pytest.raises(AccessDeniedError):
            world.poll(chat[0].id, page_origin="https://copycat.example")
        own_site = world.poll(chat[0].id, page_origin="https://www.cafe.example")
        no_page = world.poll(chat[0].id)

    assert [item.id for item in own_site.items] == [m.id for m in chat[1:]]
    assert no_page == own_site


def test_rows_whose_shown_conversations_disagree_read_the_whole_chat(
    connection_pools: PostgresConnectionPools,
    storage_scope: StorageScopeContext,
) -> None:
    reader = PostgresWidgetPollReadAdapter(connection_pools, storage_scope)
    world = PollWorld(InMemoryCollectionFactory())
    sandbox = world.add_conversation(VISITOR, is_sandbox=True)
    position = MessagePosition(id=MessageId(), created_at=Microseconds(START))
    rows: list[tuple[object, ...]] = [
        # The statement took the sandbox conversation for a shown one.
        ("conversation", 1, str(sandbox.id), True, sandbox.model_dump_json()),
        ("message", int(position.created_at), str(position.id), None, None),
    ]

    read_back = reader._decode(rows)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    assert read_back == WidgetPollRead(newest=None)
    with pytest.raises(ExternalServiceError):
        reader._decode([("message", "late", str(position.id), None, None)])  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
