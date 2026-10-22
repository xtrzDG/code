"""
Migration 1200 and the release before it. The previous release connects
as the tables' owner and scopes with app.business_id and app.bypass_rls:
it keeps working on the migrated database (the owner joined
workshop_platform). `workshop.revert_tenant_and_platform_roles()` gives it
back exactly its old policies, after which the next migrate applies 1200
again. A migration role without CREATEROLE migrates once an administrator
made the groups and its membership.
"""

from collections.abc import Generator
from typing import LiteralString

import psycopg
import pytest
from psycopg import errors, sql

from app.schemas.constants.storage import CollectionIsolation
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.document_tenancy import infer_collection_isolation
from tests.storage.migration_steps import run_migrations
from tests.storage.postgres_roles import TENANT_GROUP, TENANT_LOGIN_ROLE
from tests.storage.postgres_server import ThrowawayPostgresServer

MIGRATION: str = "1200_tenant_and_platform_roles"
PLAIN_MIGRATION_ROLE: str = "workshop_plain_owner"
POLICIES: LiteralString = (
    "select tablename, policyname, roles::text[], qual from pg_policies"
    " where schemaname = 'workshop' order by tablename, policyname"
)
INSERT_CONTACT: LiteralString = (
    "insert into workshop.contacts (document_key, business_id, document,"
    " created_at, updated_at) values (%s, %s, '{}', 1, 1)"
)
COUNT_CONTACTS: LiteralString = "select count(*) from workshop.contacts"


def test_the_previous_release_works_on_the_migrated_database(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> None:
    with postgres_server.app_connection(database_name) as owner:
        with owner.transaction():
            owner.execute("select set_config('app.business_id', 'biz_a', true)")
            owner.execute(INSERT_CONTACT, ("contact_a", "biz_a"))
        with owner.transaction():
            owner.execute("select set_config('app.bypass_rls', 'on', true)")
            owner.execute(INSERT_CONTACT, ("contact_b", "biz_b"))
            owner.execute(
                "insert into workshop.users (document_key, business_id, document,"
                " created_at, updated_at) values ('user_1', null, '{}', 1, 1)"
            )
            counted = owner.execute(COUNT_CONTACTS).fetchone()

    assert counted == (2,)


def test_the_revert_restores_the_old_policies_and_1200_applies_again(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> None:
    with postgres_server.app_connection(database_name) as owner:
        owner.execute(INSERT_CONTACT, ("contact_a", "biz_a"))
        owner.execute(INSERT_CONTACT, ("contact_b", "biz_b"))
        owner.execute("select workshop.revert_tenant_and_platform_roles()")

    reverted = read_policies(postgres_server, database_name)
    assert {policy for _, policy, _, _ in reverted} == {"business_isolation"}
    assert all("app.bypass_rls" in str(qual) for _, _, _, qual in reverted)
    assert MIGRATION not in recorded_migrations(postgres_server, database_name)
    with (
        tenant_connection(postgres_server, database_name) as tenant,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        tenant.execute(COUNT_CONTACTS)
    with postgres_server.app_connection(database_name) as owner, owner.transaction():
        owner.execute("select set_config('app.business_id', 'biz_a', true)")
        assert owner.execute(COUNT_CONTACTS).fetchone() == (1,)

    report = run_migrations(postgres_server.app_database_url(database_name))

    assert report.newly_applied == [MIGRATION]
    reapplied = read_policies(postgres_server, database_name)
    assert {policy for _, policy, _, _ in reapplied} == {
        "platform_access",
        "tenant_isolation",
    }
    with tenant_connection(postgres_server, database_name) as tenant:
        tenant.execute("select set_config('app.bypass_rls', 'on', false)")
        tenant.execute("select set_config('app.business_id', 'biz_a', false)")
        assert tenant.execute(COUNT_CONTACTS).fetchone() == (1,)


def test_the_tenant_role_holds_nothing_on_tables_whose_rows_name_no_business(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> None:
    expected = {
        str(definition.name)
        for definition in DOCUMENT_COLLECTIONS
        if infer_collection_isolation(definition.document_type)
        is CollectionIsolation.PLATFORM
        and "business_id" not in definition.document_type.model_fields
        and definition.name != "businesses"
    }
    with postgres_server.admin_connection(database_name) as admin:
        rows = admin.execute(
            "select c.relname from pg_class c"
            " join pg_namespace n on n.oid = c.relnamespace"
            " where n.nspname = 'workshop' and c.relkind = 'r'"
            " and not has_table_privilege(%s, c.oid,"
            " 'select, insert, update, delete')",
            (TENANT_GROUP,),
        ).fetchall()

    assert {str(row[0]) for row in rows} == expected


def test_a_migration_role_without_createrole_needs_the_groups_made_for_it(
    postgres_server: ThrowawayPostgresServer, plain_owner_database: str
) -> None:
    url = DatabaseUrl(
        postgres_server.conninfo(plain_owner_database, PLAIN_MIGRATION_ROLE)
    )
    with pytest.raises(ExternalServiceError, match="member of workshop_platform"):
        run_migrations(url)

    with postgres_server.admin_connection() as admin:
        admin.execute(
            sql.SQL("grant workshop_platform to {}").format(
                sql.Identifier(PLAIN_MIGRATION_ROLE)
            )
        )
    report = run_migrations(url)

    assert MIGRATION in report.newly_applied
    assert report.pending == []


@pytest.fixture
def plain_owner_database(
    postgres_server: ThrowawayPostgresServer,
) -> Generator[str]:
    """
    A database owned by a login role without CREATEROLE, on a server whose
    groups another database's migration already made.
    """

    database_name = f"plain_{PLAIN_MIGRATION_ROLE}"
    role = sql.Identifier(PLAIN_MIGRATION_ROLE)
    with postgres_server.admin_connection() as admin:
        admin.execute(
            sql.SQL("create role {} login nocreaterole nosuperuser").format(role)
        )
        admin.execute(
            sql.SQL("create database {} owner {}").format(
                sql.Identifier(database_name), role
            )
        )
    try:
        yield database_name
    finally:
        with postgres_server.admin_connection() as admin:
            admin.execute(
                sql.SQL("drop database if exists {} with (force)").format(
                    sql.Identifier(database_name)
                )
            )
            admin.execute(sql.SQL("drop role if exists {}").format(role))


def read_policies(
    server: ThrowawayPostgresServer, database_name: str
) -> list[tuple[str, str, list[str], str | None]]:
    with server.admin_connection(database_name) as admin:
        return [
            (str(row[0]), str(row[1]), list(row[2]), row[3])
            for row in admin.execute(POLICIES).fetchall()
        ]


def recorded_migrations(
    server: ThrowawayPostgresServer, database_name: str
) -> set[str]:
    with server.admin_connection(database_name) as admin:
        rows = admin.execute("select name from workshop.schema_migrations").fetchall()
    return {str(row[0]) for row in rows}


def tenant_connection(
    server: ThrowawayPostgresServer, database_name: str
) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        server.conninfo(database_name, TENANT_LOGIN_ROLE), autocommit=True
    )
