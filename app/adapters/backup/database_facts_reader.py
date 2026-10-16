"""
Count what a database holds, for the backup manifest and the restore drill.

Every query runs on a connection the caller prepared: inside the dump's
exported snapshot, or on the restored scratch database. Row-level security
is bypassed for the counts with the application's own switch
(`app.bypass_rls`), so a role bound by the policies counts every row; the
isolation probes then switch it off again and look as a bound role would.
"""

from typing import LiteralString

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

from app.schemas.dto.backups import DatabaseFacts, IsolationProbe, RecordedMigration
from app.schemas.typings.backups.constrained_integers import (
    DatabasePolicyCount,
    TableRowCount,
)
from app.schemas.typings.backups.constrained_strings import DatabaseTableName
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)

APPLICATION_SCHEMA: str = "workshop"
MIGRATIONS_TABLE: str = "schema_migrations"
BUSINESSES_TABLE: str = "businesses"
# A business id no real row has: the probe of an empty database.
ABSENT_BUSINESS_ID: str = "biz_restore_drill_probe"
TABLES_SQL: LiteralString = (
    "select c.relname, c.relrowsecurity and c.relforcerowsecurity"
    " from pg_class c join pg_namespace n on n.oid = c.relnamespace"
    " where n.nspname = %s and c.relkind in ('r', 'p') order by c.relname"
)
POLICIES_SQL: LiteralString = "select count(*) from pg_policies where schemaname = %s"

type Connection = psycopg.Connection[TupleRow]


def bypass_row_security(connection: Connection, is_on: bool) -> None:
    """Turn the application's RLS bypass on or off for this session."""

    connection.execute(
        "select set_config('app.bypass_rls', %s, false)", ["on" if is_on else "off"]
    )


def read_database_facts(connection: Connection) -> DatabaseFacts:
    """Row counts, migrations, secured tables and policies (bypass on)."""

    tables: list[tuple[str, bool]] = [
        (str(row[0]), bool(row[1]))
        for row in connection.execute(TABLES_SQL, [APPLICATION_SCHEMA]).fetchall()
    ]
    policy_row = connection.execute(POLICIES_SQL, [APPLICATION_SCHEMA]).fetchone()
    return DatabaseFacts(
        row_counts={
            qualified_name(table): TableRowCount(count_rows(connection, table))
            for table, _ in tables
        },
        applied_migrations=read_migrations(connection, [t for t, _ in tables]),
        secured_tables=[qualified_name(table) for table, secured in tables if secured],
        policy_count=DatabasePolicyCount(0 if policy_row is None else policy_row[0]),
    )


def read_migrations(
    connection: Connection, tables: list[str]
) -> list[RecordedMigration]:
    if MIGRATIONS_TABLE not in tables:
        return []

    rows = connection.execute(
        sql.SQL("select name, checksum from {}.{} order by name").format(
            sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(MIGRATIONS_TABLE)
        )
    ).fetchall()
    return [
        RecordedMigration(
            name=SchemaMigrationName(str(row[0])),
            checksum=SchemaMigrationChecksum(str(row[1])),
        )
        for row in rows
    ]


def probe_isolation(
    connection: Connection,
    secured_tables: list[DatabaseTableName],
) -> list[IsolationProbe]:
    """
    Look at every secured table as a role bound by row-level security
    would (the caller made the session such a role): nothing without a
    scope; in the scope of one business, its rows and only its rows.
    """

    bypass_row_security(connection, True)
    business_id: str = pick_business_id(connection)
    expected: dict[DatabaseTableName, int] = {
        table: count_rows(connection, table_part(table), business_id)
        for table in secured_tables
    }
    bypass_row_security(connection, False)
    set_business_scope(connection, "")
    unscoped: dict[DatabaseTableName, int] = {
        table: count_rows(connection, table_part(table)) for table in secured_tables
    }
    set_business_scope(connection, business_id)
    probes: list[IsolationProbe] = [
        IsolationProbe(
            table=table,
            unscoped_rows=TableRowCount(unscoped[table]),
            own_rows=TableRowCount(
                count_rows(connection, table_part(table), business_id)
            ),
            expected_own_rows=TableRowCount(expected[table]),
            foreign_rows=TableRowCount(
                count_rows(connection, table_part(table), business_id, foreign=True)
            ),
        )
        for table in secured_tables
    ]
    set_business_scope(connection, "")
    return probes


def pick_business_id(connection: Connection) -> str:
    row = connection.execute(
        sql.SQL(
            "select business_id from {}.{} where business_id is not null"
            " order by business_id limit 1"
        ).format(sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(BUSINESSES_TABLE))
    ).fetchone()
    return ABSENT_BUSINESS_ID if row is None else str(row[0])


def set_business_scope(connection: Connection, business_id: str) -> None:
    connection.execute("select set_config('app.business_id', %s, false)", [business_id])


def count_rows(
    connection: Connection,
    table: str,
    business_id: str | None = None,
    foreign: bool = False,
) -> int:
    query = sql.SQL("select count(*) from {}.{}").format(
        sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(table)
    )
    parameters: list[str] = []
    if business_id is not None:
        query += (
            sql.SQL(" where business_id is distinct from %s")
            if foreign
            else sql.SQL(" where business_id = %s")
        )
        parameters.append(business_id)

    row = connection.execute(query, parameters).fetchone()
    return 0 if row is None else int(row[0])


def qualified_name(table: str) -> DatabaseTableName:
    return DatabaseTableName(f"{APPLICATION_SCHEMA}.{table}")


def table_part(table: DatabaseTableName) -> str:
    return str(table).split(".", 1)[1]
