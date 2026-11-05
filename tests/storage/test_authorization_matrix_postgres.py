"""
The authorization matrix (tests/platform/test_authorization_matrix.py) on
Postgres with the application's two pools (migration 1200), where
row-level security is the second line of defence: every business
operation refuses strangers (404), staff on owner-only operations (403)
and callers without a token (401) without changing a row, and lets members
through inside their business's scope. A session of the tenant pool reads
no other business even after it switches the old bypass on, as a statement
smuggled into a request would.
"""

from psycopg import errors, sql
from psycopg.rows import TupleRow

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.platform.authorization_checks import (
    check_members_are_let_through,
    check_owner_reads_every_record,
    check_refusals,
    expect_error,
)
from tests.platform.authorization_tables import OWNER_ONLY_OPERATIONS
from tests.platform.authorization_world import open_authorization_world
from tests.storage.postgres_roles import RoleDatabase

SECURED_TABLES: sql.SQL = sql.SQL(
    "select c.relname from pg_class c"
    " join pg_namespace n on n.oid = c.relnamespace"
    " where n.nspname = 'workshop' and c.relkind = 'r' and c.relrowsecurity"
    " and has_table_privilege(current_user, c.oid, 'select')"
    " order by c.relname"
)


def environment_of(role_urls: RoleDatabase) -> dict[str, str]:
    return {**E2E_ENVIRONMENT, **role_urls.environment()}


def test_every_business_operation_refuses_outsiders_on_postgres(
    role_urls: RoleDatabase,
) -> None:
    with open_authorization_world(environment_of(role_urls)) as world:
        failures = (
            check_owner_reads_every_record(world)
            + check_refusals(world, world.owner_a, expect_error(404, "not_found"))
            + check_refusals(world, world.staff_a, expect_error(404, "not_found"))
            + check_refusals(world, {}, expect_error(401, "authentication_required"))
            + check_refusals(
                world,
                world.staff_b,
                expect_error(403, "access_denied"),
                only=OWNER_ONLY_OPERATIONS,
            )
        )

    assert failures == []


def test_members_are_let_through_in_their_business_scope_on_postgres(
    role_urls: RoleDatabase,
) -> None:
    with open_authorization_world(environment_of(role_urls)) as world:
        failures = check_members_are_let_through(world)

    assert failures == []


def test_a_tenant_session_reads_no_other_business_even_with_the_bypass_on(
    role_urls: RoleDatabase,
) -> None:
    with open_authorization_world(environment_of(role_urls)) as world:
        pools: PostgresConnectionPools | None = (
            world.workshop.container.clients.postgres_pools()
        )
        assert pools is not None and not pools.is_single
        with pools.tenant.connection() as tenant, tenant.transaction():
            enter_business_with_bypass(tenant, world.business_a)
            leaked = rows_of_other_businesses(tenant, world.business_a)
            users_refused = reads_are_refused(tenant, "users")
        with pools.platform.connection() as platform, platform.transaction():
            seen_by_platform = rows_of_other_businesses(platform, world.business_a)

    assert leaked == {}
    assert users_refused
    # Business B's demo records are there: the tenant role just never sees them.
    assert sum(seen_by_platform.values()) > 0


def enter_business_with_bypass(
    connection: PostgresConnection, business_id: str
) -> None:
    connection.execute("select set_config('app.business_id', %s, true)", (business_id,))
    connection.execute("select set_config('app.bypass_rls', 'on', true)")


def rows_of_other_businesses(
    connection: PostgresConnection, business_id: str
) -> dict[str, int]:
    """Rows of each readable secured table that name another business."""

    counts: dict[str, int] = {}
    tables: list[TupleRow] = connection.execute(SECURED_TABLES).fetchall()
    for (table,) in tables:
        row = connection.execute(
            sql.SQL(
                "select count(*) from workshop.{} where business_id is distinct from %s"
            ).format(sql.Identifier(str(table))),
            (business_id,),
        ).fetchone()
        if row is not None and int(row[0]) > 0:
            counts[str(table)] = int(row[0])
    return counts


def reads_are_refused(connection: PostgresConnection, table: str) -> bool:
    try:
        with connection.transaction():
            connection.execute(
                sql.SQL("select count(*) from workshop.{}").format(
                    sql.Identifier(table)
                )
            )
    except errors.InsufficientPrivilege:
        return True
    return False
