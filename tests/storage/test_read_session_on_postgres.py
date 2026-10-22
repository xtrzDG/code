"""
Read sessions on Postgres: the reads of a block share one pinned connection
and one transaction, begun at the first read with its scope; each read
binds row-level security in its own scope; other threads, units of work
and unscoped code run as they do without a session.
"""

import contextvars
import threading
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import pq

from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.adapters.storage.postgres.read_sessions import read_session_of
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.exceptions.storage_errors import UnscopedStorageAccessError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_owner
from tests.storage.read_session_world import (
    CountingPool,
    ReadSessionWorld,
    scope_settings,
    transaction_status,
    visible_channel_count,
)


@pytest.fixture
def world(database_url: DatabaseUrl) -> Iterator[ReadSessionWorld]:
    pool = CountingPool(database_url, max_size=4)
    try:
        yield ReadSessionWorld(pool, StorageScopeContext())
    finally:
        pool.close()


def test_the_reads_of_a_session_share_one_connection(world: ReadSessionWorld) -> None:
    with world.scope.scoped_to_business(world.business_id):
        world.pool.borrowed = 0
        with world.sessions.read_session():
            first = world.channels.get(str(world.channel.id))
            listed = world.channels.list_all()
            foreign = world.channels.get(str(world.other_channel.id))
        in_session = world.pool.borrowed
        world.pool.borrowed = 0
        world.channels.get(str(world.channel.id))
        world.channels.list_all()

    assert first == world.channel
    assert listed == [world.channel]
    assert foreign is None
    assert (in_session, world.pool.borrowed) == (1, 2)


def test_the_transaction_begins_at_the_first_read_in_its_scope(
    world: ReadSessionWorld,
) -> None:
    with (
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        connection = world.session().connection
        before_read = transaction_status(connection)
        world.channels.get(str(world.channel.id))
        settings = scope_settings(connection)
        # Row-level security alone hides the other business's rows here.
        visible = visible_channel_count(connection)
        in_read = transaction_status(connection)

    assert before_read is pq.TransactionStatus.IDLE
    assert in_read is pq.TransactionStatus.INTRANS
    assert settings == (str(world.business_id), "off")
    assert visible == 1
    # The session committed its reads and gave the connection back.
    assert transaction_status(connection) is pq.TransactionStatus.IDLE
    assert world.pool.idle_connection_count() == 1


def test_a_read_in_another_scope_rescopes_the_transaction_and_back(
    world: ReadSessionWorld,
) -> None:
    owner = build_owner(COUNTRY_SAMPLES[0])
    with world.scope.platform_wide():
        world.users.upsert(str(owner.id), owner)

    with (
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        world.pool.borrowed = 0
        world.channels.get(str(world.channel.id))
        connection = world.session().connection
        # A platform collection: read platform-wide in the same transaction.
        user = world.users.get(str(owner.id))
        platform_settings = scope_settings(connection)
        foreign = world.channels.get(str(world.other_channel.id))
        tenant_settings = scope_settings(connection)
        visible = visible_channel_count(connection)

    assert user == owner
    assert platform_settings == ("", "on")
    # Back in the business's scope: the other business stays hidden.
    assert foreign is None
    assert tenant_settings == (str(world.business_id), "off")
    assert visible == 1
    assert world.pool.borrowed == 0


def test_a_session_is_plain_inside_a_unit_of_work_nested_or_unscoped(
    world: ReadSessionWorld,
) -> None:
    unit = PostgresUnitOfWorkAdapter(world.pools, world.scope)
    uncommitted = ChannelDocument(business_id=world.business_id, kind=ChannelKind.PHONE)
    with world.scope.scoped_to_business(world.business_id):
        with unit.unit_of_work(), world.sessions.read_session():
            world.channels.upsert(str(uncommitted.id), uncommitted)
            # Read on the unit's connection: its own write is visible.
            seen = world.channels.get(str(uncommitted.id))
            assert read_session_of(world.pool) is None
        world.pool.borrowed = 0
        with world.sessions.read_session(), world.sessions.read_session():
            world.channels.get(str(world.channel.id))
            world.channels.list_all()
        assert world.pool.borrowed == 1

    with world.sessions.read_session(), pytest.raises(UnscopedStorageAccessError):
        world.channels.list_all()

    assert seen == uncommitted


def test_another_thread_does_not_share_the_session(world: ReadSessionWorld) -> None:
    found: list[ChannelDocument | None] = []
    with (
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        world.pool.borrowed = 0
        context = contextvars.copy_context()
        thread = threading.Thread(
            target=context.run,
            args=(lambda: found.append(world.channels.get(str(world.channel.id))),),
        )
        thread.start()
        thread.join()

    assert found == [world.channel]
    assert world.pool.borrowed == 1


def test_a_failed_read_rolls_back_and_the_next_read_begins_anew(
    world: ReadSessionWorld,
) -> None:
    with world.scope.scoped_to_business(world.business_id):
        with world.sessions.read_session():
            world.channels.list_all()
            connection = world.session().connection
            with pytest.raises(psycopg.errors.DivisionByZero):
                connection.execute("select 1 / 0")
            # The transaction is aborted: this read fails and rolls it back.
            with pytest.raises(psycopg.Error):
                world.channels.list_all()
            assert world.session().scope is None
            again = world.channels.list_all()

        assert world.channels.list_all() == [world.channel]

    assert again == [world.channel]
