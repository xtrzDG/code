"""
The lookup fields on Postgres: every declared field is indexed by the
migrations, list fields follow row-level security, and purges delete in
batches (inbox and outbox uniqueness: test_inbox_outbox_on_postgres.py).
"""

from typing import LiteralString

import pytest
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.document_lookup_sql import lookup_column_name
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.conversation_repositories import ContactRepository
from app.repositories.user_repositories import UserSessionRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.storage import LookupFieldKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserSessionDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.storage.document_lookup_catalog import DOCUMENT_LOOKUP_FIELDS
from app.utilities.storage.document_lookup_fields import (
    split_element_path,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_contact
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.hot_path_seeding import insert_session_rows
from tests.storage.postgres_server import ThrowawayPostgresServer

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")

COLUMN_TYPES: dict[LookupFieldKind, str] = {
    LookupFieldKind.TEXT: "text",
    LookupFieldKind.FILTER_TEXT: "text",
    LookupFieldKind.INTEGER: "bigint",
}
LOOKUP_COLUMNS_SQL: LiteralString = (
    "select table_name, column_name, data_type, is_generated = 'ALWAYS' "
    "from information_schema.columns "
    "where table_schema = 'workshop' and column_name like 'doc\\_%'"
)
INDEXED_COLUMNS_SQL: LiteralString = (
    "select t.relname, a.attname from pg_index i "
    "join pg_class t on t.oid = i.indrelid "
    "join pg_namespace n on n.oid = t.relnamespace and n.nspname = 'workshop' "
    "join pg_attribute a on a.attrelid = t.oid and a.attnum = any(i.indkey)"
)
TRIGGERS_SQL: LiteralString = (
    "select c.relname, encode(t.tgargs, 'escape') from pg_trigger t "
    "join pg_class c on c.oid = t.tgrelid where not t.tgisinternal"
)
FILL_TRIGGERS_SQL: LiteralString = (
    "select c.relname, encode(t.tgargs, 'escape') from pg_trigger t "
    "join pg_class c on c.oid = t.tgrelid "
    "where t.tgname = c.relname || '_lookup_columns'"
)


def text_rows(rows: list[TupleRow]) -> set[tuple[str, ...]]:
    return {tuple(str(value) for value in row) for row in rows}


def test_every_declared_lookup_field_is_indexed_by_the_migrations(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    """
    A TEXT, FILTER_TEXT or INTEGER field has its `doc_<field>` column of the
    right type: a stored generated one (up to migration 1113) or a plain
    one that the table's `<table>_lookup_columns` trigger fills from the
    field (1122 on); TEXT and INTEGER columns are indexed.
    """

    with postgres_server.admin_connection(database_name) as connection:
        columns = {
            (str(row[0]), str(row[1])): (str(row[2]), row[3] is True)
            for row in connection.execute(LOOKUP_COLUMNS_SQL).fetchall()
        }
        indexed = text_rows(connection.execute(INDEXED_COLUMNS_SQL).fetchall())
        triggers = text_rows(connection.execute(TRIGGERS_SQL).fetchall())
        fill_arguments = {
            str(row[0]): str(row[1]).split("\\000")
            for row in connection.execute(FILL_TRIGGERS_SQL).fetchall()
        }

    for collection_name, fields in DOCUMENT_LOOKUP_FIELDS.items():
        table: str = str(collection_name)
        for field in fields:
            if field.kind is LookupFieldKind.ELEMENT_TEXT:
                list_field, element_field = split_element_path(field.path)
                arguments: str = f"{list_field}\\000{element_field}\\000"
                assert (table, arguments) in triggers, field
                continue

            column: str = lookup_column_name(field.path)
            data_type, is_generated = columns[(table, column)]
            assert data_type == COLUMN_TYPES[field.kind], field
            if not is_generated:
                pairs = fill_arguments.get(table, [])
                assert any(
                    pairs[index : index + 2] == [column, str(field.path)]
                    for index in range(0, len(pairs) - 1, 2)
                ), f"{table}.{column} is neither generated nor filled by a trigger"
            if field.kind is not LookupFieldKind.FILTER_TEXT:
                assert (table, column) in indexed, f"{table}.{column} has no index"


def test_every_plain_lookup_column_is_declared(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    """No trigger fills a column the catalog does not query (dead weight)."""

    with postgres_server.admin_connection(database_name) as connection:
        plain = {
            (str(row[0]), str(row[1]))
            for row in connection.execute(LOOKUP_COLUMNS_SQL).fetchall()
            if row[3] is not True
        }

    declared = {
        (str(collection_name), lookup_column_name(field.path))
        for collection_name, fields in DOCUMENT_LOOKUP_FIELDS.items()
        for field in fields
        if field.kind is not LookupFieldKind.ELEMENT_TEXT
    }
    assert plain <= declared


def test_list_field_lookups_keep_to_the_business_scope(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    contacts = ContactRepository(postgres_collections(ContactDocument, "contacts"))
    first = build_contact(COUNTRY_SAMPLES[0], BusinessId())
    second = build_contact(COUNTRY_SAMPLES[1], BusinessId())
    second.channel_identities = list(first.channel_identities)
    contacts.save(first)
    contacts.save(second)
    identity = first.channel_identities[0]
    assert identity.channel is not ChannelKind.TELEGRAM

    with storage_scope.scoped_to_business(first.business_id):
        found = contacts.find_by_channel_identity(
            first.business_id, identity.channel, identity.channel_user_id
        )
        foreign = contacts.find_by_channel_identity(
            second.business_id, identity.channel, identity.channel_user_id
        )
        other_channel = contacts.find_by_channel_identity(
            first.business_id, ChannelKind.TELEGRAM, identity.channel_user_id
        )

    assert found is not None and found.id == first.id
    assert foreign is None
    assert other_channel is None
    found_platform_wide = contacts.find_by_channel_identity(
        second.business_id, identity.channel, identity.channel_user_id
    )
    assert found_platform_wide is not None and found_platform_wide.id == second.id


def test_the_session_purge_deletes_in_batches(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    insert_session_rows(connection_pool, count=2_500, expires_at=0)
    sessions = UserSessionRepository(
        postgres_collections(UserSessionDocument, "user_sessions")
    )
    assert sessions.delete_expired(Microseconds(2_000)) == 2_000
    assert sessions.delete_expired(Microseconds(2_000)) == 0
    assert sessions.delete_expired(Microseconds(10_000)) == 500
