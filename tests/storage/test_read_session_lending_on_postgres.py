"""
Read sessions lend their pinned connection to the other work of the block:
the session commits its reads first, so a write commits on its own at once
(as without a session) and a unit of work opens its own transaction, all
on the session's one connection: a session never waits for a second one.
"""

from collections.abc import Iterator

import pytest
from psycopg import pq

from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from tests.storage.postgres_roles import RoleDatabase
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.read_session_world import (
    ReadSessionWorld,
    role_world,
    transaction_status,
)


@pytest.fixture
def world(role_urls: RoleDatabase) -> Iterator[ReadSessionWorld]:
    # One connection per pool only, taken within a second: a session that
    # wanted a second connection would fail here instead of waiting.
    with role_world(
        role_urls, max_size=1, acquire_timeout_seconds=1.0
    ) as session_world:
        yield session_world


def stored_channel_ids(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> set[str]:
    """What another session of the server sees committed, past RLS."""

    with postgres_server.admin_connection(database_name) as connection:
        rows = connection.execute(
            "select document_key from workshop.channels"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_a_write_in_a_session_commits_at_once_on_the_same_connection(
    world: ReadSessionWorld,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    late = ChannelDocument(business_id=world.business_id, kind=ChannelKind.PHONE)
    committed: set[str] = set()
    after_write: pq.TransactionStatus | None = None
    seen: ChannelDocument | None = None
    open_connections: int = 0
    with (
        pytest.raises(RuntimeError),
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        world.channels.list_all()
        world.channels.upsert(str(late.id), late)
        committed = stored_channel_ids(postgres_server, database_name)
        connection = world.session().connection
        # The write's transaction ended; no read transaction is open.
        after_write = transaction_status(connection)
        seen = world.channels.get(str(late.id))
        open_connections = world.pool.open_connection_count()
        raise RuntimeError("the block fails after its write")

    assert str(late.id) in committed
    assert after_write is pq.TransactionStatus.IDLE
    assert seen == late
    assert open_connections == 1
    # The write stays, although the block failed after it.
    with world.scope.scoped_to_business(world.business_id):
        assert world.channels.get(str(late.id)) == late


def test_a_unit_of_work_in_a_session_runs_in_its_own_transaction(
    world: ReadSessionWorld,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    unit = PostgresUnitOfWorkAdapter(world.pools, world.scope)
    kept = ChannelDocument(business_id=world.business_id, kind=ChannelKind.PHONE)
    dropped = ChannelDocument(business_id=world.business_id, kind=ChannelKind.PHONE)
    with (
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        world.channels.list_all()
        with unit.unit_of_work():
            world.channels.upsert(str(kept.id), kept)
            # The unit's own write, read inside the unit before it commits.
            inside = world.channels.get(str(kept.id))
            uncommitted = stored_channel_ids(postgres_server, database_name)
        with pytest.raises(RuntimeError), unit.unit_of_work():
            world.channels.upsert(str(dropped.id), dropped)
            raise RuntimeError("the second unit fails")
        after = {str(channel.id) for channel in world.channels.list_all()}

    assert inside == kept
    assert str(kept.id) not in uncommitted
    assert after == {str(world.channel.id), str(kept.id)}


def test_other_users_of_the_pool_get_the_connection_outside_any_transaction(
    world: ReadSessionWorld,
) -> None:
    with (
        world.scope.scoped_to_business(world.business_id),
        world.sessions.read_session(),
    ):
        world.channels.list_all()
        session = world.session()
        with world.pool.connection() as lent:
            lent_status = transaction_status(lent)
            # Reads while the connection is lent run without the session.
            world.channels.get(str(world.channel.id))
            assert session.scope is None
            assert session.is_lent()
        reread = world.channels.list_all()

    assert lent is session.connection
    assert lent_status is pq.TransactionStatus.IDLE
    assert reread == [world.channel]
