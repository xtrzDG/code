from typing import LiteralString

from psycopg.rows import TupleRow

from app.adapters.storage.postgres.platform_transaction import platform_transaction
from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.monitoring import DatabaseSizeAdapterContract
from app.schemas.dto.admin_system import TableSizeView
from app.schemas.dto.platform_health import DatabaseSize
from app.schemas.typings.backups.constrained_strings import DatabaseTableName
from app.schemas.typings.monitoring.constrained_integers import (
    CollectionRowEstimate,
    StorageByteSize,
)

# Sizes from the catalog: pg_total_relation_size (table, indexes, TOAST)
# and the planner's row estimate (reltuples; -1 before the first ANALYZE),
# never a count of a table.
TABLE_SIZES_SQL: LiteralString = (
    "select n.nspname || '.' || c.relname, pg_total_relation_size(c.oid), "
    "greatest(c.reltuples, 0)::bigint "
    "from pg_class as c join pg_namespace as n on n.oid = c.relnamespace "
    "where n.nspname = %s and c.relkind in ('r', 'p') "
    "order by pg_total_relation_size(c.oid) desc, c.relname"
)
DATABASE_SIZE_SQL: LiteralString = "select pg_database_size(current_database())"
SIZE_PROBE_COLLECTION: str = "database_size"


class PostgresDatabaseSizeAdapter(DatabaseSizeAdapterContract):
    """
    The disk space of the database and of each table of the application
    schema, read from the system catalog: a few milliseconds whatever the
    tables hold.
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    def measure(self) -> DatabaseSize | None:
        with platform_transaction(
            self._connection_pool, SIZE_PROBE_COLLECTION
        ) as connection:
            table_rows: list[TupleRow] = connection.execute(
                TABLE_SIZES_SQL, (DOCUMENT_SCHEMA_NAME,)
            ).fetchall()
            total_row: TupleRow | None = connection.execute(
                DATABASE_SIZE_SQL
            ).fetchone()

        return DatabaseSize(
            total_bytes=StorageByteSize(int(total_row[0]) if total_row else 0),
            tables=[
                TableSizeView(
                    table=DatabaseTableName(str(row[0])),
                    total_bytes=StorageByteSize(int(row[1])),
                    row_estimate=CollectionRowEstimate(int(row[2])),
                )
                for row in table_rows
            ],
        )
