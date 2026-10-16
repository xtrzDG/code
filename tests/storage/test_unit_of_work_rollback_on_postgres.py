"""
A unit of work that fails on Postgres: its writes are rolled back, a
database failure the application understands is raised as its application
error (a programming error as it is), and the pinned connection goes back
to the pool with no transaction and no advisory lock left open.
"""

import threading
from collections.abc import Generator

import psycopg
import pytest

from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import build_contact
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.rls_contacts import GEORGIA, ISRAEL
from tests.storage.storage_testing import build_fixed_wall_clock

LOCK_KEY: int = 4_242_001


class Units:
    def __init__(self, database_url: DatabaseUrl) -> None:
        self.pool = PostgresConnectionPoolClient(database_url, max_size=2)
        self.scope = StorageScopeContext()
        self.adapter = PostgresUnitOfWorkAdapter(self.pool, self.scope)
        self.contacts = PostgresCollectionFactory(
            connection_pool=self.pool,
            storage_scope=self.scope,
            wall_clock=build_fixed_wall_clock(),
        )(ContactDocument, "contacts")


@pytest.fixture
def units(database_url: DatabaseUrl) -> Generator[Units]:
    world = Units(database_url)
    try:
        yield world
    finally:
        world.pool.close()


def test_a_database_failure_is_raised_as_its_application_error_and_rolls_back(
    units: Units,
) -> None:
    business_id = BusinessId()
    contact = build_contact(GEORGIA, business_id)
    lost = psycopg.errors.QueryCanceled("canceling statement due to statement timeout")

    with units.scope.scoped_to_business(business_id):
        with (
            pytest.raises(ExternalServiceError) as raised,
            units.adapter.unit_of_work(),
        ):
            units.contacts.upsert(str(contact.id), contact)
            raise lost

        assert raised.value.__cause__ is lost
        assert units.contacts.get(str(contact.id)) is None


def test_a_programming_error_from_the_database_propagates_unchanged(
    units: Units,
) -> None:
    business_id = BusinessId()
    contact = build_contact(ISRAEL, business_id)

    with units.scope.scoped_to_business(business_id):
        with (
            pytest.raises(psycopg.errors.UndefinedColumn),
            units.adapter.unit_of_work(),
        ):
            units.contacts.upsert(str(contact.id), contact)
            with units.pool.connection() as connection:
                connection.execute("select no_such_column from workshop.contacts")

        assert units.contacts.get(str(contact.id)) is None


def test_a_failed_unit_leaves_no_lock_and_no_transaction_behind(units: Units) -> None:
    business_id = BusinessId()

    with (
        units.scope.scoped_to_business(business_id),
        pytest.raises(RuntimeError),
        units.adapter.unit_of_work(),
    ):
        with units.pool.connection() as connection:
            connection.execute("select pg_advisory_xact_lock(%s)", (LOCK_KEY,))
        raise RuntimeError("the booking could not be placed")

    taken: list[bool] = []

    def take_the_lock_elsewhere() -> None:
        with units.pool.connection() as connection:
            row = connection.execute(
                "select pg_try_advisory_xact_lock(%s)", (LOCK_KEY,)
            ).fetchone()
            taken.append(bool(row and row[0]))

    other = threading.Thread(target=take_the_lock_elsewhere)
    other.start()
    other.join()
    assert taken == [True]

    # The next unit on the same pool commits normally.
    contact = build_contact(GEORGIA, business_id)
    with units.scope.scoped_to_business(business_id):
        with units.adapter.unit_of_work():
            units.contacts.upsert(str(contact.id), contact)
        assert units.contacts.get(str(contact.id)) == contact
