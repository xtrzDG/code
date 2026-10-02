"""Row-level security: a business scope sees and writes only its own rows."""

import pytest

from app.repositories.conversation_repositories import ContactRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.storage_queries import DocumentFieldMatch
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import build_contact, build_owner
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.rls_contacts import (
    EMIRATES,
    GEORGIA,
    ISRAEL,
    JAPAN,
    save_two_businesses_contacts,
)


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
        assert [c.id for c in contacts.list_by_fields([phone_is(first_phone)])] == [
            first_contact.id
        ]
        assert contacts.list_by_fields([phone_is(second_phone)]) == []
        assert contacts.find_one_by_field(PHONE_FIELD, phone_text(second_phone)) is None


PHONE_FIELD = DocumentFieldPath("phone_number")


def phone_text(phone: str) -> DocumentFieldText:
    return DocumentFieldText(phone)


def phone_is(phone: str) -> DocumentFieldMatch:
    return DocumentFieldMatch(field=PHONE_FIELD, value=phone_text(phone))
