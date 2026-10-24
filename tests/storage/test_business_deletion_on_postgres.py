"""
The hard delete on Postgres with the two database roles (migration 1200):
the deletion runs on the platform pool, and afterwards the business's own
scope (the tenant role under row-level security) sees no row of it in any
table but what the law keeps, the platform role finds none either, and the
other business's rows are exactly as they were.
"""

import psycopg
from psycopg import sql

from app.adapters.storage.postgres.business_row_queries import (
    APPLICATION_SCHEMA,
    list_business_tables,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.business_closures.retained_tables import (
    QUEUED_JOBS_TABLE,
    RETAINED_TABLES,
)
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB
from tests.business_closures.closure_world import DAY_SECONDS, open_closure_world
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.storage.postgres_roles import RoleDatabase

type TableCounts = dict[str, int]


def scoped_counts(tenant_url: DatabaseUrl, business_id: str) -> TableCounts:
    """
    Every row the business's own scope sees, by table: the tenant role with
    `app.business_id` set, no filter but row-level security.
    """

    counts: TableCounts = {}
    with psycopg.connect(str(tenant_url)) as connection, connection.transaction():
        connection.execute(
            "select set_config('app.business_id', %s, true)", [business_id]
        )
        for table in list_business_tables(connection):
            row = connection.execute(
                sql.SQL("select count(*) from {}.{}").format(
                    sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(table)
                )
            ).fetchone()
            if row is not None and int(row[0]):
                counts[table] = int(row[0])

    return counts


def platform_counts(platform_url: DatabaseUrl, business_id: str) -> TableCounts:
    """The business's rows by table as the platform role finds them."""

    counts: TableCounts = {}
    with psycopg.connect(str(platform_url)) as connection:
        for table in list_business_tables(connection):
            row = connection.execute(
                sql.SQL("select count(*) from {}.{} where business_id = %s").format(
                    sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(table)
                ),
                [business_id],
            ).fetchone()
            if row is not None and int(row[0]):
                counts[table] = int(row[0])

    return counts


def unfinished_jobs(platform_url: DatabaseUrl, business_id: str) -> list[str]:
    """The business's queued jobs other than its sub-processors' erasure."""

    with psycopg.connect(str(platform_url)) as connection:
        rows = connection.execute(
            sql.SQL(
                "select document ->> 'name' from {}.{} where business_id = %s"
            ).format(
                sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(QUEUED_JOBS_TABLE)
            ),
            [business_id],
        ).fetchall()
    return [str(row[0]) for row in rows if row[0] != ERASE_PROCESSOR_COPIES_JOB]


def test_nothing_of_a_deleted_business_remains_on_the_two_roles(
    role_urls: RoleDatabase,
) -> None:
    environment = {**E2E_ENVIRONMENT, **role_urls.environment()}
    with open_closure_world(environment) as world:
        business_b, business_a = world.business_b, world.business_a
        before_b = scoped_counts(role_urls.tenant_url, business_b)
        before_a = platform_counts(role_urls.platform_url, business_a)
        assert before_b["messages"] > 0 and before_b["contacts"] > 0
        assert before_b["document_lookup_keys"] > 0

        world.close_b()
        world.workshop.clock.advance(31 * DAY_SECONDS)
        world.tick("queue_business_deletions")
        world.workshop.run_queued_jobs()

        kept = set(RETAINED_TABLES) | {QUEUED_JOBS_TABLE}
        scoped = scoped_counts(role_urls.tenant_url, business_b)
        assert set(scoped) <= kept, scoped
        assert "businesses" not in scoped
        found = platform_counts(role_urls.platform_url, business_b)
        assert set(found) <= kept, found
        assert unfinished_jobs(role_urls.platform_url, business_b) == []
        assert platform_counts(role_urls.platform_url, business_a) == before_a


def test_a_closure_cancelled_within_its_days_keeps_every_row(
    role_urls: RoleDatabase,
) -> None:
    environment = {**E2E_ENVIRONMENT, **role_urls.environment()}
    with open_closure_world(environment) as world:
        business_b = world.business_b
        before = scoped_counts(role_urls.tenant_url, business_b)
        world.close_b()
        world.workshop.clock.advance(5 * 60)

        cancelled = world.workshop.client.delete(
            world.closure_path, headers=world.owner_b
        )
        assert cancelled.status_code == 204, cancelled.text
        world.workshop.clock.advance(31 * DAY_SECONDS)
        world.tick("queue_business_deletions")
        world.workshop.run_queued_jobs()

        after = scoped_counts(role_urls.tenant_url, business_b)
        # The closure itself is gone and no row was lost; the notices of
        # closing and cancelling (and their audit trail) only added some.
        assert "business_closures" not in after
        assert {
            table: after.get(table, 0)
            for table, count in before.items()
            if after.get(table, 0) < count
        } == {}
        for table in ("contacts", "conversations", "messages", "bookings"):
            assert after[table] == before[table], table
        assert platform_counts(role_urls.platform_url, business_b)["businesses"] == 1
