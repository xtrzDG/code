"""
The consent ledger on Postgres (1246) is append-only: the application's
tenant role may read and add entries but never change or delete one, no
role may change an entry (the trigger), and only the platform role, which
deletes a whole business, may delete them.
"""

from typing import LiteralString

import psycopg
import pytest
from psycopg import errors

from app.repositories.consent_record_repository import ConsentRecordRepository
from app.schemas.constants.consent_records import ConsentEvent, ConsentEventSource
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_roles import PLATFORM_LOGIN_ROLE, TENANT_LOGIN_ROLE
from tests.storage.postgres_server import ThrowawayPostgresServer

pytestmark = [pytest.mark.postgres, pytest.mark.usefixtures("platform_scope")]

BUSINESS: BusinessId = BusinessId()
CHANGE: LiteralString = "update workshop.consent_records set updated_at = 1"
REMOVE: LiteralString = "delete from workshop.consent_records"


def appended(collections: PostgresCollectionFactory) -> ConsentRecordRepository:
    repo = ConsentRecordRepository(
        collections(ConsentRecordDocument, "consent_records")
    )
    repo.append(
        ConsentRecordDocument(
            business_id=BUSINESS,
            contact_id=ContactId(),
            event=ConsentEvent.GIVEN,
            source=ConsentEventSource.BOOKING_PAGE,
        )
    )
    return repo


def stored_count(server: ThrowawayPostgresServer, database_name: str) -> int:
    with server.app_connection(database_name) as owner:
        row = owner.execute("select count(*) from workshop.consent_records").fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.parametrize("statement", [CHANGE, REMOVE])
def test_the_tenant_role_can_neither_change_nor_delete_an_entry(
    postgres_collections: PostgresCollectionFactory,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    statement: LiteralString,
) -> None:
    appended(postgres_collections)

    with (
        psycopg.connect(
            postgres_server.conninfo(database_name, TENANT_LOGIN_ROLE),
            autocommit=True,
        ) as tenant,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        tenant.execute(statement)

    assert stored_count(postgres_server, database_name) == 1


def test_no_role_changes_an_entry_not_even_the_tables_owner(
    postgres_collections: PostgresCollectionFactory,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    appended(postgres_collections)

    with (
        postgres_server.app_connection(database_name) as owner,
        pytest.raises(errors.InsufficientPrivilege, match="append-only"),
    ):
        owner.execute(CHANGE)


def test_only_the_deletion_of_the_business_removes_the_entries(
    postgres_collections: PostgresCollectionFactory,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    appended(postgres_collections)

    with psycopg.connect(
        postgres_server.conninfo(database_name, PLATFORM_LOGIN_ROLE),
        autocommit=True,
    ) as platform:
        with pytest.raises(errors.InsufficientPrivilege):
            platform.execute(CHANGE)
        platform.execute(
            "delete from workshop.consent_records where business_id = %s",
            [str(BUSINESS)],
        )

    assert stored_count(postgres_server, database_name) == 0
