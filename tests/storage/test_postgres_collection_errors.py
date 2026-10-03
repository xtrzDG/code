"""Errors of the Postgres document collection name their cause and the fix."""

import pytest

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_knowledge_item, build_owner
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_ticking_wall_clock

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")


def test_nul_character_is_rejected_with_a_clear_error(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    knowledge_items = postgres_collections(KnowledgeItemDocument, "knowledge_items")
    item = build_knowledge_item(COUNTRY_SAMPLES[0], BusinessId())
    item.title = KnowledgeTitle("bad\x00title")

    with pytest.raises(ValidationFailedError, match="NUL"):
        knowledge_items.upsert(str(item.id), item)

    assert knowledge_items.list_all() == []


def test_missing_table_names_the_migration_command(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    unknown_collection = PostgresCollectionFactory(
        connection_pool=connection_pool,
        storage_scope=StorageScopeContext(),
        wall_clock=build_ticking_wall_clock(),
    )(UserDocument, "not_migrated_yet")

    with pytest.raises(ExternalServiceError, match="migrate"):
        unknown_collection.list_all()

    with pytest.raises(ExternalServiceError, match="not_migrated_yet"):
        unknown_collection.upsert(str(UserId()), build_owner(COUNTRY_SAMPLES[1]))


def test_database_without_migrations_names_the_migration_command(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(empty_database_name), max_size=1
    )
    try:
        users = PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_ticking_wall_clock(),
        )(UserDocument, "users")

        with pytest.raises(ExternalServiceError, match="apply the migrations"):
            users.get("anything")
    finally:
        connection_pool.close()


def test_role_without_grants_gets_a_deployment_hint(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    with postgres_server.admin_connection(database_name) as connection:
        connection.execute("create role workshop_reader login")
    connection_pool = PostgresConnectionPoolClient(
        DatabaseUrl(postgres_server.conninfo(database_name, "workshop_reader")),
        max_size=1,
    )
    try:
        users = PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_ticking_wall_clock(),
        )(UserDocument, "users")

        with pytest.raises(ExternalServiceError, match="grant it usage"):
            users.list_all()
    finally:
        connection_pool.close()
        with postgres_server.admin_connection(database_name) as connection:
            connection.execute("drop role workshop_reader")


def test_corrupted_row_fails_validation_instead_of_returning_garbage(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    users: PostgresDocumentCollectionAdapter[UserDocument] = postgres_collections(
        UserDocument, "users"
    )
    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        connection.execute(
            "insert into workshop.users "
            "(document_key, business_id, document, created_at, updated_at) "
            "values ('broken', null, '{\"locale\": 42}', 0, 0)"
        )

    with pytest.raises(ValueError, match="validation error"):
        users.get("broken")
