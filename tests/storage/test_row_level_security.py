"""Row-level security: a business scope sees and writes only its own rows."""

import threading

import pytest
from psycopg.rows import TupleRow

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.conversation_repositories import ContactRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_contact, build_owner
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

GEORGIA, ISRAEL, EMIRATES, JAPAN = COUNTRY_SAMPLES[0:4]


def count_contacts(rows: list[TupleRow]) -> int:
    count: object = rows[0][0]
    assert isinstance(count, int)
    return count


def save_two_businesses_contacts(
    postgres_collections: PostgresCollectionFactory,
) -> tuple[BusinessId, BusinessId, ContactDocument, ContactDocument]:
    contacts = postgres_collections(ContactDocument, "contacts")
    first_business_id, second_business_id = BusinessId(), BusinessId()
    first_contact = build_contact(GEORGIA, first_business_id)
    second_contact = build_contact(ISRAEL, second_business_id)
    contacts.upsert(str(first_contact.id), first_contact)
    contacts.upsert(str(second_contact.id), second_contact)
    return first_business_id, second_business_id, first_contact, second_contact


def test_every_collection_table_has_forced_rls_and_the_policy(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    with postgres_server.admin_connection(database_name) as connection:
        tables = connection.execute(
            "select c.relname, c.relrowsecurity, c.relforcerowsecurity "
            "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'workshop' and c.relkind = 'r' "
            "and c.relname <> 'schema_migrations'"
        ).fetchall()
        policies = connection.execute(
            "select tablename, cmd, qual, with_check from pg_policies "
            "where schemaname = 'workshop'"
        ).fetchall()

    table_names = {str(row[0]) for row in tables}
    assert {str(definition.name) for definition in DOCUMENT_COLLECTIONS} <= table_names
    assert all(row[1] is True and row[2] is True for row in tables)
    assert {str(row[0]) for row in policies} == table_names
    for _, command, using_expression, check_expression in policies:
        assert command == "ALL"
        assert "app.business_id" in str(using_expression)
        assert "app.bypass_rls" in str(using_expression)
        assert using_expression == check_expression


def test_application_role_cannot_skip_policies(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    with postgres_server.app_connection(database_name) as connection:
        row = connection.execute(
            "select rolsuper, rolbypassrls from pg_roles where rolname = current_user"
        ).fetchone()

    assert row == (False, False)


def test_business_scope_sees_only_its_own_rows(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    first_business_id, _, first_contact, second_contact = save_two_businesses_contacts(
        postgres_collections
    )
    contacts = postgres_collections(ContactDocument, "contacts")

    with storage_scope.scoped_to_business(first_business_id):
        assert [contact.id for contact in contacts.list_all()] == [first_contact.id]
        assert contacts.get(str(first_contact.id)) == first_contact
        assert contacts.get(str(second_contact.id)) is None
        contacts.delete(str(second_contact.id))

    assert [contact.id for contact in contacts.list_all()] == [
        first_contact.id,
        second_contact.id,
    ]


def test_business_scope_cannot_write_or_overwrite_another_business(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    first_business_id, second_business_id, _, second_contact = (
        save_two_businesses_contacts(postgres_collections)
    )
    contacts = postgres_collections(ContactDocument, "contacts")
    foreign_contact = build_contact(EMIRATES, second_business_id)
    hijacked_contact = second_contact.model_copy(
        update={"name": ContactName("Hijacked")}
    )

    with storage_scope.scoped_to_business(first_business_id):
        with pytest.raises(AccessDeniedError, match="another business"):
            contacts.upsert(str(foreign_contact.id), foreign_contact)

        with pytest.raises(AccessDeniedError):
            contacts.upsert(str(second_contact.id), hijacked_contact)

        # Moving a row of this business to another business is refused too.
        own_contact = build_contact(JAPAN, first_business_id)
        contacts.upsert(str(own_contact.id), own_contact)
        moved_contact = own_contact.model_copy(
            update={"business_id": second_business_id}
        )
        with pytest.raises(AccessDeniedError):
            contacts.upsert(str(own_contact.id), moved_contact)

    assert contacts.get(str(foreign_contact.id)) is None
    assert contacts.get(str(second_contact.id)) == second_contact


def test_platform_scope_inside_a_business_scope_sees_everything(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    first_business_id, _, _, _ = save_two_businesses_contacts(postgres_collections)
    contacts = postgres_collections(ContactDocument, "contacts")

    with storage_scope.scoped_to_business(first_business_id):
        with storage_scope.platform_wide():
            assert len(contacts.list_all()) == 2

        assert len(contacts.list_all()) == 1


def test_platform_collections_ignore_the_business_scope(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    users = postgres_collections(UserDocument, "users")
    audit_log = postgres_collections(AuditLogEntryDocument, "audit_log_entries")
    owners = [build_owner(sample) for sample in (GEORGIA, ISRAEL)]
    for owner in owners:
        users.upsert(str(owner.id), owner)

    with storage_scope.scoped_to_business(BusinessId()):
        assert [user.id for user in users.list_all()] == [owner.id for owner in owners]
        user_repo = UserRepository(users)
        assert (
            user_repo.find_by_phone_number(E164PhoneNumber(ISRAEL.phone_number))
            == (owners[1])
        )
        assert audit_log.list_all() == []


def test_repository_check_and_rls_both_hide_foreign_rows(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    first_business_id, second_business_id, _, second_contact = (
        save_two_businesses_contacts(postgres_collections)
    )
    contact_repo = ContactRepository(postgres_collections(ContactDocument, "contacts"))

    # A buggy caller that passes the right pair of ids for the other business
    # is still stopped by RLS inside the first business's scope.
    with storage_scope.scoped_to_business(first_business_id):
        assert contact_repo.get(second_business_id, second_contact.id) is None
        assert contact_repo.list_by_business(second_business_id) == []

    assert contact_repo.get(second_business_id, second_contact.id) == second_contact


def test_raw_sessions_default_to_deny(
    postgres_server: ThrowawayPostgresServer,
    postgres_collections: PostgresCollectionFactory,
    database_name: str,
) -> None:
    first_business_id, _, _, _ = save_two_businesses_contacts(postgres_collections)

    with postgres_server.app_connection(database_name) as connection:
        no_settings = connection.execute(
            "select count(*) from workshop.contacts"
        ).fetchall()
        with connection.transaction():
            connection.execute(
                "select set_config('app.business_id', %s, true)",
                (str(first_business_id),),
            )
            scoped = connection.execute(
                "select count(*) from workshop.contacts"
            ).fetchall()
        with connection.transaction():
            connection.execute("select set_config('app.bypass_rls', 'on', true)")
            bypassed = connection.execute(
                "select count(*) from workshop.contacts"
            ).fetchall()
        after_transactions = connection.execute(
            "select count(*) from workshop.contacts"
        ).fetchall()

    assert count_contacts(no_settings) == 0
    assert count_contacts(scoped) == 1
    assert count_contacts(bypassed) == 2
    assert count_contacts(after_transactions) == 0


def test_scope_settings_do_not_leak_to_the_next_pool_user(
    database_url: DatabaseUrl,
    storage_scope: StorageScopeContext,
) -> None:
    single_connection_pool = PostgresConnectionPoolClient(
        database_url=database_url, max_size=1
    )
    try:
        contacts = PostgresCollectionFactory(
            connection_pool=single_connection_pool,
            storage_scope=storage_scope,
            wall_clock=build_fixed_wall_clock(),
        )(ContactDocument, "contacts")
        with storage_scope.scoped_to_business(BusinessId()):
            contacts.list_all()

        with single_connection_pool.connection() as connection:
            row = connection.execute(
                "select coalesce(current_setting('app.business_id', true), ''), "
                "coalesce(current_setting('app.bypass_rls', true), '')"
            ).fetchone()
    finally:
        single_connection_pool.close()

    assert row == ("", "")


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


def test_field_lookups_keep_to_the_business_scope(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    first_business_id, _, first_contact, second_contact = save_two_businesses_contacts(
        postgres_collections
    )
    contacts = postgres_collections(ContactDocument, "contacts")
    first_phone = str(first_contact.phone_number)
    second_phone = str(second_contact.phone_number)

    with storage_scope.scoped_to_business(first_business_id):
        assert [c.id for c in contacts.list_by_field("phone_number", first_phone)] == [
            first_contact.id
        ]
        assert contacts.list_by_field("phone_number", second_phone) == []
