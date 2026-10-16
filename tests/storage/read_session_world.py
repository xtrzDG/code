"""
The world of the read session tests: a pool that counts its borrows, two
businesses' channels and a platform collection, and the session adapter.
"""

from collections.abc import Generator
from contextlib import contextmanager

from psycopg import pq

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.read_sessions import ReadSession, read_session_of
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.storage.storage_scope_context import StorageScopeContext
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


class ReadSessionWorld:
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
        self.sessions = PostgresReadSessionAdapter(pool)
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

    def session(self) -> ReadSession:
        session: ReadSession | None = read_session_of(self.pool)
        assert session is not None
        return session


def transaction_status(connection: PostgresConnection) -> pq.TransactionStatus:
    return connection.info.transaction_status


def scope_settings(connection: PostgresConnection) -> tuple[object, ...] | None:
    return connection.execute(
        "select current_setting('app.business_id', true), "
        "current_setting('app.bypass_rls', true)"
    ).fetchone()


def visible_channel_count(connection: PostgresConnection) -> int:
    """Channels row-level security lets the connection's scope see."""

    row = connection.execute("select count(*) from workshop.channels").fetchone()
    assert row is not None
    count: object = row[0]
    assert isinstance(count, int)
    return count
