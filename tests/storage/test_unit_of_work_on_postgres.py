"""
A unit of work on Postgres: one pinned connection and one transaction for a
block, the scope's row-level security kept for every statement in it.
"""

import threading
from collections.abc import Generator

import pytest

from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import build_contact, build_owner
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.rls_contacts import GEORGIA, ISRAEL, save_two_businesses_contacts
from tests.storage.storage_testing import build_fixed_wall_clock


class UnitWorld:
    """A pool, a scope, a unit of work and the contacts and users on them."""

    def __init__(self, database_url: DatabaseUrl) -> None:
        self.pool = PostgresConnectionPoolClient(database_url, max_size=4)
        self.scope = StorageScopeContext()
        self.units = PostgresUnitOfWorkAdapter(self.pool, self.scope)
        collections = PostgresCollectionFactory(
            connection_pool=self.pool,
            storage_scope=self.scope,
            wall_clock=build_fixed_wall_clock(),
        )
        self.collections = collections
        self.contacts = collections(ContactDocument, "contacts")
        self.users = collections(UserDocument, "users")


@pytest.fixture
def world(database_url: DatabaseUrl) -> Generator[UnitWorld]:
    unit_world = UnitWorld(database_url)
    try:
        yield unit_world
    finally:
        unit_world.pool.close()


def count_visible_contacts(world: UnitWorld) -> int:
    """Contacts the current transaction's row-level security lets through."""

    with world.pool.connection() as connection:
        row = connection.execute("select count(*) from workshop.contacts").fetchone()

    assert row is not None
    return int(row[0])


def test_the_writes_of_a_unit_commit_together_on_one_connection(
    world: UnitWorld,
) -> None:
    business_id = BusinessId()
    first, second = (
        build_contact(GEORGIA, business_id),
        build_contact(ISRAEL, business_id),
    )
    seen_from_outside: list[ContactDocument | None] = []

    def read_from_another_thread() -> None:
        with world.scope.scoped_to_business(business_id):
            seen_from_outside.append(world.contacts.get(str(first.id)))

    with world.scope.scoped_to_business(business_id):
        with world.units.unit_of_work():
            world.contacts.upsert(str(first.id), first)
            world.contacts.upsert(str(second.id), second)
            # The unit sees its own writes; other connections do not yet.
            assert world.contacts.get(str(first.id)) == first
            reader = threading.Thread(target=read_from_another_thread)
            reader.start()
            reader.join()
            assert world.pool.open_connection_count() == 2

        assert world.contacts.get(str(second.id)) == second

    assert seen_from_outside == [None]


def test_a_unit_that_raises_keeps_none_of_its_writes(world: UnitWorld) -> None:
    business_id = BusinessId()
    contact = build_contact(GEORGIA, business_id)

    with world.scope.scoped_to_business(business_id):
        with pytest.raises(RuntimeError), world.units.unit_of_work():
            world.contacts.upsert(str(contact.id), contact)
            raise RuntimeError("the booking could not be placed")

        assert world.contacts.get(str(contact.id)) is None


def test_a_nested_unit_rolls_back_only_its_own_writes(world: UnitWorld) -> None:
    business_id = BusinessId()
    kept, dropped = (
        build_contact(GEORGIA, business_id),
        build_contact(ISRAEL, business_id),
    )

    with world.scope.scoped_to_business(business_id):
        with world.units.unit_of_work():
            world.contacts.upsert(str(kept.id), kept)
            with pytest.raises(RuntimeError), world.units.unit_of_work():
                world.contacts.upsert(str(dropped.id), dropped)
                raise RuntimeError("inner step failed")

        assert world.contacts.get(str(kept.id)) == kept
        assert world.contacts.get(str(dropped.id)) is None


def test_a_refused_write_of_another_business_does_not_end_the_unit(
    world: UnitWorld,
) -> None:
    business_id = BusinessId()
    own, foreign = (
        build_contact(GEORGIA, business_id),
        build_contact(ISRAEL, BusinessId()),
    )

    with world.scope.scoped_to_business(business_id):
        with world.units.unit_of_work():
            with pytest.raises(AccessDeniedError):
                world.contacts.upsert(str(foreign.id), foreign)
            world.contacts.upsert(str(own.id), own)

        assert world.contacts.get(str(own.id)) == own


def test_a_platform_write_in_a_unit_leaves_no_bypass_for_tenant_writes(
    world: UnitWorld,
) -> None:
    with world.scope.platform_wide():
        first_business_id, _, _, _ = save_two_businesses_contacts(world.collections)
    foreign = build_contact(ISRAEL, BusinessId())

    with (
        world.scope.scoped_to_business(first_business_id),
        world.units.unit_of_work(),
    ):
        # The unit starts in the business's scope.
        assert count_visible_contacts(world) == 1
        # Users are a platform collection: written platform-wide ...
        world.users.upsert("owner", build_owner(GEORGIA))
        # ... and the next tenant write is checked in the business's scope.
        with pytest.raises(AccessDeniedError):
            world.contacts.upsert(str(foreign.id), foreign)

    with world.scope.platform_wide():
        assert world.users.get("owner") is not None
        assert world.contacts.get(str(foreign.id)) is None
