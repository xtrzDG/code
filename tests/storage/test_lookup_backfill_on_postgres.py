"""
Trigger-kept lookup columns on Postgres (migration 1122): the trigger fills
them on every write, and `workshop backfill-lookup` fills the rows written
before the column existed, in keyset batches, waiting out locked rows.
"""

import json
import threading
from typing import LiteralString

from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_lookup_backfill_adapter import (
    PostgresLookupBackfillAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.lookup_backfill import (
    BackfillLookupColumnsCommand,
    LookupBackfillReport,
    TriggerLookupColumn,
)
from app.schemas.typings.storage.constrained_integers import (
    LockWaitSeconds,
    LookupBackfillBatchSize,
    MigrationAttemptNumber,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.use_cases.maintenance.backfill_lookup_columns_use_case import (
    BackfillLookupColumnsUseCase,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import RecordedRetryPause

UPDATED_AT = TriggerLookupColumn(
    collection_name=DocumentCollectionName("knowledge_items"),
    field=DocumentFieldPath("updated_at"),
)
INSERT_SQL: LiteralString = (
    "insert into workshop.knowledge_items "
    "(document_key, business_id, document, created_at, updated_at) "
    "values (%s, 'business_1', %s::jsonb, 1, 1)"
)


def seed_items(connection_pool: PostgresConnectionPoolClient) -> None:
    """Eight rows: six as if written before 1122 (empty column), one
    without the field, one already filled."""

    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        for index in range(8):
            key = f"item_{index:02d}"
            document: dict[str, object] = {
                "is_active": True,
                "updated_at": 1_000 + index,
            }
            if index == 6:
                del document["updated_at"]
            connection.execute(INSERT_SQL, (key, json.dumps(document)))
        connection.execute(
            "update workshop.knowledge_items "
            "set doc_updated_at = null, doc_is_active = null "
            "where document_key < 'item_06'"
        )


def column_values(connection_pool: PostgresConnectionPoolClient) -> list[TupleRow]:
    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        return connection.execute(
            "select document_key, doc_updated_at, doc_is_active "
            "from workshop.knowledge_items order by document_key"
        ).fetchall()


def backfill(
    connection_pool: PostgresConnectionPoolClient,
    command: BackfillLookupColumnsCommand,
    pause: RecordedRetryPause | None = None,
) -> LookupBackfillReport:
    return BackfillLookupColumnsUseCase(
        backfill=PostgresLookupBackfillAdapter(
            connection_pool, lock_timeout=LockWaitSeconds(1)
        ),
        retry_pause=pause or RecordedRetryPause(),
    ).run(command)


def test_the_trigger_fills_lookup_columns_on_every_write(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    seed_items(connection_pool)

    rows = column_values(connection_pool)

    assert rows[6] == ("item_06", None, "true")
    assert rows[7] == ("item_07", 1_007, "true")


def test_trigger_columns_are_listed_from_the_catalog(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    columns = PostgresLookupBackfillAdapter(connection_pool).list_trigger_columns()

    assert UPDATED_AT in columns
    assert (
        TriggerLookupColumn(
            collection_name=DocumentCollectionName("contacts"),
            field=DocumentFieldPath("last_seen_at"),
        )
        in columns
    )
    # Stored generated columns of older migrations are not backfilled.
    assert all(str(column.field) != "phone_number" for column in columns)


def test_the_backfill_fills_old_rows_in_keyset_batches_once(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    seed_items(connection_pool)
    command = BackfillLookupColumnsCommand(
        collection_name=DocumentCollectionName("knowledge_items"),
        field=DocumentFieldPath("updated_at"),
        batch_size=LookupBackfillBatchSize(3),
    )

    dry_run = backfill(connection_pool, command.model_copy(update={"is_dry_run": True}))
    report = backfill(connection_pool, command)
    again = backfill(connection_pool, command)

    assert [int(entry.missing) for entry in dry_run.columns] == [6]
    [entry] = report.columns
    assert (int(entry.scanned), int(entry.filled), int(entry.batch_count)) == (8, 6, 3)
    assert [int(entry.filled) for entry in again.columns] == [0]
    rows = column_values(connection_pool)
    # One rewrite of a row runs the trigger: every lookup column is filled.
    assert [(row[1], row[2]) for row in rows] == [
        *((1_000 + index, "true") for index in range(6)),
        (None, "true"),
        (1_007, "true"),
    ]


def test_a_batch_waits_out_a_locked_row_and_tries_again(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    seed_items(connection_pool)
    release, released, holding = threading.Event(), threading.Event(), threading.Event()

    def hold_a_row() -> None:
        with (
            postgres_server.app_connection(database_name) as connection,
            connection.transaction(),
        ):
            connection.execute("select set_config('app.bypass_rls', 'on', true)")
            connection.execute(
                "select 1 from workshop.knowledge_items "
                "where document_key = 'item_02' for update"
            )
            holding.set()
            release.wait(timeout=30)
        released.set()

    class ReleasingPause(RecordedRetryPause):
        def pause(self, attempt: MigrationAttemptNumber) -> None:
            super().pause(attempt)
            release.set()
            assert released.wait(timeout=10)

    blocker = threading.Thread(target=hold_a_row)
    blocker.start()
    assert holding.wait(timeout=10)
    pause = ReleasingPause()
    try:
        report = backfill(
            connection_pool,
            BackfillLookupColumnsCommand(
                collection_name=DocumentCollectionName("knowledge_items")
            ),
            pause,
        )
    finally:
        release.set()
        blocker.join(timeout=30)

    assert pause.attempts == [1]
    filled = {str(entry.field): int(entry.filled) for entry in report.columns}
    # The first column's batches rewrite the rows, which fills every column.
    assert filled == {"is_active": 6, "updated_at": 0}
    assert column_values(connection_pool)[2][1] == 1_002
