"""The storage factory for the container wiring, and the migrate command setup."""

import io

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.document_collection_factory import (
    build_document_collection,
    build_postgres_connection_pool,
)
from app.adapters.storage.postgres.migrate import main
from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.storage import CollectionIsolation
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_business, build_contact
from tests.storage.storage_testing import build_fixed_wall_clock


def test_without_database_url_collections_live_in_memory() -> None:
    settings = assemble_app_settings({})

    users = build_document_collection(UserDocument, "users", settings)

    assert isinstance(users, InMemoryDocumentCollectionAdapter)
    assert build_postgres_connection_pool(settings) is None


@pytest.mark.parametrize(
    "collection_name", ["Users", "x", "1users", "users; drop table", "a" * 64]
)
def test_unsafe_collection_names_are_rejected(collection_name: str) -> None:
    with pytest.raises(ValidationFailedError, match="snake case"):
        build_document_collection(
            UserDocument, collection_name, assemble_app_settings({})
        )


def test_with_database_url_collections_are_postgres_tables(
    database_url: DatabaseUrl,
) -> None:
    settings = assemble_app_settings({"DATABASE_URL": database_url})
    connection_pool = build_postgres_connection_pool(settings, max_size=2)
    assert isinstance(connection_pool, PostgresConnectionPoolClient)
    assert connection_pool.max_size == 2
    storage_scope = StorageScopeContext()
    try:
        businesses = build_document_collection(
            BusinessDocument,
            "businesses",
            settings,
            connection_pool=connection_pool,
            storage_scope=storage_scope,
            wall_clock=build_fixed_wall_clock(),
        )
        contacts = build_document_collection(
            ContactDocument,
            "contacts",
            settings,
            connection_pool=connection_pool,
            storage_scope=storage_scope,
        )
        assert isinstance(businesses, PostgresDocumentCollectionAdapter)
        assert isinstance(contacts, PostgresDocumentCollectionAdapter)
        assert businesses.isolation is CollectionIsolation.PLATFORM
        assert contacts.isolation is CollectionIsolation.TENANT

        business_repo = BusinessRepository(businesses)
        business = build_business(COUNTRY_SAMPLES[5], owner_id=UserId())
        business_repo.save(business)
        contact = build_contact(COUNTRY_SAMPLES[5], business.id)
        contacts.upsert(str(contact.id), contact)

        assert business_repo.get(business.id) == business
        with storage_scope.scoped_to_business(BusinessId()):
            assert contacts.list_all() == []
        with storage_scope.scoped_to_business(business.id):
            assert contacts.list_all() == [contact]
    finally:
        connection_pool.close()


def test_defaults_build_a_working_adapter(database_url: DatabaseUrl) -> None:
    settings = assemble_app_settings({"DATABASE_URL": database_url})
    forced_tenant_users = build_document_collection(
        UserDocument,
        "users",
        settings,
        isolation=CollectionIsolation.TENANT,
    )
    assert isinstance(forced_tenant_users, PostgresDocumentCollectionAdapter)
    assert forced_tenant_users.isolation is CollectionIsolation.TENANT

    contacts = build_document_collection(ContactDocument, "contacts", settings)
    contact = build_contact(COUNTRY_SAMPLES[2], BusinessId())
    contacts.upsert(str(contact.id), contact)

    assert contacts.get(str(contact.id)) == contact


def test_migrate_without_database_url_explains_and_exits_with_two() -> None:
    error_output = io.StringIO()

    exit_code = main([], {}, output=io.StringIO(), error_output=error_output)

    assert exit_code == 2
    assert "DATABASE_URL is not set" in error_output.getvalue()


def test_migrate_with_invalid_settings_exits_with_two() -> None:
    error_output = io.StringIO()

    exit_code = main(
        [],
        {"DATABASE_URL": "host=/nowhere", "LLM_PROVIDER": "unknown-provider"},
        output=io.StringIO(),
        error_output=error_output,
    )

    assert exit_code == 2
    assert "Invalid settings" in error_output.getvalue()


def test_migrate_reports_an_unreachable_database(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    socket_directory = tmp_path_factory.mktemp("no-server")
    error_output = io.StringIO()

    exit_code = main(
        [],
        {"DATABASE_URL": f"host={socket_directory} port=1 dbname=missing"},
        output=io.StringIO(),
        error_output=error_output,
    )

    assert exit_code == 1
    assert "Migration failed" in error_output.getvalue()
