"""
Row-level security per session (migration 1200): a tenant session sees the
rows of the business it names and nothing else, whatever it sets; nothing
leaks between pool users or threads.
"""

import threading
from typing import LiteralString

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.storage import StorageScope
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_contact
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_roles import RoleDatabase
from tests.storage.rls_contacts import save_two_businesses_contacts
from tests.storage.storage_testing import build_fixed_wall_clock

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")


SCOPE: LiteralString = "select set_config('app.business_id', %s, true)"
BYPASS: LiteralString = "select set_config('app.bypass_rls', 'on', false)"


def count_rows(connection: psycopg.Connection[TupleRow]) -> int:
    row = connection.execute("select count(*) from workshop.contacts").fetchone()
    assert row is not None
    count: object = row[0]
    assert isinstance(count, int)
    return count


def test_a_tenant_session_sees_one_business_whatever_it_sets(
    role_urls: RoleDatabase,
    postgres_collections: PostgresCollectionFactory,
) -> None:
    first_business_id, _, _, _ = save_two_businesses_contacts(postgres_collections)

    with psycopg.connect(role_urls.tenant_url, autocommit=True) as connection:
        no_settings = count_rows(connection)
        with connection.transaction():
            connection.execute(SCOPE, (str(first_business_id),))
            scoped = count_rows(connection)
        # The switch every policy honoured before migration 1200, set by
        # the session itself as an injected statement would.
        connection.execute(BYPASS)
        bypassed = count_rows(connection)
        with connection.transaction():
            connection.execute(SCOPE, (str(first_business_id),))
            scoped_and_bypassed = count_rows(connection)
        after_transactions = count_rows(connection)

    assert no_settings == 0
    assert scoped == 1
    assert bypassed == 0
    assert scoped_and_bypassed == 1
    assert after_transactions == 0


def test_a_tenant_session_cannot_become_the_platform_role(
    role_urls: RoleDatabase,
) -> None:
    with psycopg.connect(role_urls.tenant_url, autocommit=True) as connection:
        for statement in (
            "set role workshop_platform",
            "set session authorization workshop_platform_login",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(statement)


def test_a_platform_session_sees_every_business_without_settings(
    role_urls: RoleDatabase,
    postgres_collections: PostgresCollectionFactory,
) -> None:
    save_two_businesses_contacts(postgres_collections)

    with psycopg.connect(role_urls.platform_url, autocommit=True) as connection:
        assert count_rows(connection) == 2


def test_scope_settings_do_not_leak_to_the_next_pool_user(
    role_urls: RoleDatabase,
    storage_scope: StorageScopeContext,
) -> None:
    single_connection_pool = PostgresConnectionPoolClient(
        database_url=role_urls.tenant_url, max_size=1
    )
    try:
        contacts = PostgresCollectionFactory(
            connection_pools=PostgresConnectionPools.single(single_connection_pool),
            storage_scope=storage_scope,
            wall_clock=build_fixed_wall_clock(),
        )(ContactDocument, "contacts")
        with storage_scope.scoped_to_business(BusinessId()):
            contacts.list_all()

        with single_connection_pool.connection() as connection:
            row = connection.execute(
                "select coalesce(current_setting('app.business_id', true), '')"
            ).fetchone()
    finally:
        single_connection_pool.close()

    assert row == ("",)


def test_concurrent_threads_keep_their_own_scope(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    contacts = postgres_collections(ContactDocument, "contacts")
    business_ids = [BusinessId() for _ in COUNTRY_SAMPLES]
    for sample, business_id in zip(COUNTRY_SAMPLES, business_ids, strict=True):
        for index in range(3):
            contact = build_contact(sample, business_id)
            contact.phone_number = E164PhoneNumber(f"{sample.phone_number[:-1]}{index}")
            contacts.upsert(str(contact.id), contact)

    seen_business_ids: dict[BusinessId, set[BusinessId]] = {}
    errors: list[BaseException] = []
    start = threading.Barrier(len(business_ids))

    def read_own_contacts(business_id: BusinessId) -> None:
        try:
            start.wait()
            with storage_scope.scoped_to_business(business_id):
                for _ in range(5):
                    found = {contact.business_id for contact in contacts.list_all()}
                    seen_business_ids.setdefault(business_id, set()).update(found)
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [
        threading.Thread(target=read_own_contacts, args=(business_id,))
        for business_id in business_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert seen_business_ids == {
        business_id: {business_id} for business_id in business_ids
    }


def test_an_unscoped_tenant_session_sees_and_writes_no_tenant_row(
    role_urls: RoleDatabase,
    postgres_collections: PostgresCollectionFactory,
) -> None:
    first_business_id, _, _, _ = save_two_businesses_contacts(postgres_collections)
    foreign_contact = build_contact(COUNTRY_SAMPLES[0], first_business_id)

    with psycopg.connect(role_urls.tenant_url, autocommit=True) as connection:
        with connection.transaction():
            apply_storage_scope(connection, StorageScope.unscoped())
            settings = connection.execute(
                "select current_setting('app.business_id', true)"
            ).fetchone()
            unscoped = count_rows(connection)
        with (
            pytest.raises(psycopg.errors.InsufficientPrivilege),
            connection.transaction(),
        ):
            apply_storage_scope(connection, StorageScope.unscoped())
            connection.execute(
                "insert into workshop.contacts "
                "(document_key, business_id, document, created_at, updated_at) "
                "values (%s, %s, '{}'::jsonb, 0, 0)",
                (str(foreign_contact.id), str(first_business_id)),
            )

    assert settings == ("",)
    assert unscoped == 0
