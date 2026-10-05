"""
Read sessions on Postgres: the reads of a block share one connection and
one transaction whose scope is set once; everything else (writes, reads in
another scope, other threads, units of work) runs as it does without one.
"""

import contextvars
import threading
from collections.abc import Generator, Iterator
from contextlib import contextmanager

import psycopg
import pytest

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.adapters.storage.postgres.read_sessions import read_session_of
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.storage_errors import UnscopedStorageAccessError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_owner
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import build_fixed_wall_clock


class CountingPool(PostgresConnectionPoolClient):
    """Counts how often a connection is borrowed (transactions included)."""

    borrowed: int = 0

    @contextmanager
    def connection(
        self, acquire_timeout_seconds: float | None = None
    ) -> Generator[PostgresConnection]:
        self.borrowed += 1
        with super().connection(acquire_timeout_seconds) as connection:
            yield connection


class World:
    def __init__(self, pool: CountingPool, scope: StorageScopeContext) -> None:
        self.pool = pool
        self.scope = scope
        factory = PostgresCollectionFactory(pool, scope, build_fixed_wall_clock())
        self.channels: PostgresDocumentCollectionAdapter[ChannelDocument] = factory(
            ChannelDocument, "channels"
        )
        self.users: PostgresDocumentCollectionAdapter[UserDocument] = factory(
            UserDocument, "users"
        )
        self.sessions = PostgresReadSessionAdapter(pool, scope)
        self.business_id = BusinessId()
        self.channel = self.add_channel(self.business_id)
        self.other_channel = self.add_channel(BusinessId())

    def add_channel(self, business_id: BusinessId) -> ChannelDocument:
        channel = ChannelDocument(
            business_id=business_id,
            kind=ChannelKind.WEB_CHAT,
            status=ChannelStatus.CONNECTED,
        )
        with self.scope.scoped_to_business(business_id):
            self.channels.upsert(str(channel.id), channel)
        return channel


@pytest.fixture
def world(database_url: DatabaseUrl) -> Iterator[World]:
    pool = CountingPool(database_url, max_size=4)
    try:
        yield World(pool, StorageScopeContext())
    finally:
        pool.close()


def test_the_reads_of_a_session_share_one_connection(world: World) -> None:
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


def test_the_session_applies_the_scope_once(world: World) -> None:
    with (
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        session = read_session_of(world.pool)
        assert session is not None
        settings = session.connection.execute(
            "select current_setting('app.business_id', true), "
            "current_setting('app.bypass_rls', true)"
        ).fetchone()
        # Row-level security alone hides the other business's rows here.
        rows = session.connection.execute(
            "select count(*) from workshop.channels"
        ).fetchone()

    assert settings == (str(world.business_id), "off")
    assert rows == (1,)


def test_writes_and_platform_reads_use_connections_of_their_own(world: World) -> None:
    owner = build_owner(COUNTRY_SAMPLES[0])
    with world.scope.platform_wide():
        world.users.upsert(str(owner.id), owner)
    written = world.add_channel(world.business_id)
    late = ChannelDocument(business_id=world.business_id, kind=ChannelKind.PHONE)
    user: UserDocument | None = None
    with (
        pytest.raises(RuntimeError),
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        world.pool.borrowed = 0
        world.channels.upsert(str(late.id), late)
        user = world.users.get(str(owner.id))
        # The write and the platform read each borrowed a connection.
        assert world.pool.borrowed == 2
        raise RuntimeError("the block fails after its write")

    with world.scope.scoped_to_business(world.business_id):
        stored = {str(channel.id) for channel in world.channels.list_all()}

    assert user == owner
    # The write committed on its own, although the block failed.
    assert stored == {str(world.channel.id), str(written.id), str(late.id)}


def test_a_session_is_plain_inside_a_unit_of_work_nested_or_unscoped(
    world: World,
) -> None:
    unit = PostgresUnitOfWorkAdapter(world.pool, world.scope)
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


def test_another_thread_does_not_share_the_session(world: World) -> None:
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


def test_a_failed_statement_ends_the_session_and_the_pool_recovers(
    world: World,
) -> None:
    with world.scope.scoped_to_business(world.business_id):
        with pytest.raises(psycopg.Error), world.sessions.read_session():
            session = read_session_of(world.pool)
            assert session is not None
            with pytest.raises(psycopg.errors.DivisionByZero):
                session.connection.execute("select 1 / 0")
            world.channels.list_all()

        assert world.channels.list_all() == [world.channel]
