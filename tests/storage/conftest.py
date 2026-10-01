"""
Fixtures of the storage tests.

Postgres tests use a throwaway Postgres 16 server (see postgres_server.py)
and are skipped when its binaries are missing. Each test gets its own
database, cloned from a template that already ran the migrations.
"""

from collections.abc import Generator
from typing import Protocol

import pytest
from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.postgres_schema_migration_store_adapter import (
    PostgresSchemaMigrationStoreAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.dto.storage import ApplyDatabaseMigrationsCommand
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    is_postgres_available,
    postgres_bin_directory,
)
from tests.storage.storage_testing import (
    MIGRATIONS_DIRECTORY,
    build_fixed_wall_clock,
)


class CollectionFactory(Protocol):
    """Builds a document collection of one storage kind for a test."""

    def __call__[StoredDocument: PersistentDocument](
        self,
        document_type: type[StoredDocument],
        collection_name: str,
    ) -> DocumentCollectionAdapterContract[StoredDocument]: ...


class InMemoryCollectionFactory:
    def __call__[StoredDocument: PersistentDocument](
        self,
        document_type: type[StoredDocument],
        collection_name: str,
    ) -> DocumentCollectionAdapterContract[StoredDocument]:
        del collection_name
        return InMemoryDocumentCollectionAdapter[StoredDocument](document_type)


class PostgresCollectionFactory:
    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContext,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContext = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def __call__[StoredDocument: PersistentDocument](
        self,
        document_type: type[StoredDocument],
        collection_name: str,
    ) -> PostgresDocumentCollectionAdapter[StoredDocument]:
        return PostgresDocumentCollectionAdapter[StoredDocument](
            document_type=document_type,
            collection_name=DocumentCollectionName(collection_name),
            connection_pool=self._connection_pool,
            storage_scope=self._storage_scope,
            wall_clock=self._wall_clock,
            isolation=infer_collection_isolation(document_type),
        )


@pytest.fixture(scope="session")
def postgres_server() -> Generator[ThrowawayPostgresServer]:
    bin_directory = postgres_bin_directory()
    if not is_postgres_available(bin_directory):
        pytest.skip(f"Postgres binaries not found in {bin_directory}.")

    server = ThrowawayPostgresServer(bin_directory)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(scope="session")
def migrated_template_database(postgres_server: ThrowawayPostgresServer) -> str:
    database_name: str = postgres_server.create_database()
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(database_name),
        max_size=1,
    )
    try:
        ApplyDatabaseMigrationsUseCase(
            migration_source=SqlFileMigrationSourceAdapter(MIGRATIONS_DIRECTORY),
            migration_store=PostgresSchemaMigrationStoreAdapter(connection_pool),
            wall_clock=build_fixed_wall_clock(),
        ).run(ApplyDatabaseMigrationsCommand())
    finally:
        connection_pool.close()

    return database_name


@pytest.fixture
def empty_database_name(
    postgres_server: ThrowawayPostgresServer,
) -> Generator[str]:
    database_name: str = postgres_server.create_database()
    try:
        yield database_name
    finally:
        postgres_server.drop_database(database_name)


@pytest.fixture
def database_name(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
) -> Generator[str]:
    database_name: str = postgres_server.create_database(
        template_name=migrated_template_database
    )
    try:
        yield database_name
    finally:
        postgres_server.drop_database(database_name)


@pytest.fixture
def database_url(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> DatabaseUrl:
    return postgres_server.app_database_url(database_name)


@pytest.fixture
def connection_pool(
    database_url: DatabaseUrl,
) -> Generator[PostgresConnectionPoolClient]:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=8)
    try:
        yield connection_pool
    finally:
        connection_pool.close()


@pytest.fixture
def storage_scope() -> StorageScopeContext:
    return StorageScopeContext()


@pytest.fixture
def postgres_collections(
    connection_pool: PostgresConnectionPoolClient,
    storage_scope: StorageScopeContext,
) -> PostgresCollectionFactory:
    return PostgresCollectionFactory(
        connection_pool=connection_pool,
        storage_scope=storage_scope,
        wall_clock=build_fixed_wall_clock(),
    )


@pytest.fixture(params=["in_memory", "postgres"])
def collections(request: pytest.FixtureRequest) -> CollectionFactory:
    """The same test runs on the in-memory and on the Postgres storage."""

    if request.param == "in_memory":
        return InMemoryCollectionFactory()

    postgres_factory: PostgresCollectionFactory = request.getfixturevalue(
        "postgres_collections"
    )
    return postgres_factory
