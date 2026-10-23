"""
The deletion ledger applied to a restored database: every business the
ledger names (its copy in the bucket, and the restored database's own
entries) loses its rows again, in every table but what the law keeps and the
job queue (the deletion's own sub-processor erasure jobs), so a restored
backup never brings a deleted business back.
"""

from collections.abc import Sequence
from typing import LiteralString

import psycopg
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.business_row_queries import (
    count_business_rows,
    delete_business_batch,
    list_business_tables,
)
from app.schemas.dto.backups import DeletionLedgerApplication
from app.schemas.typings.business_closures.constrained_integers import (
    DeletedRowCount,
    LedgerBusinessCount,
    ResurrectedRowCount,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.business_closures.retained_tables import ledger_erase_order

LEDGER_TABLE_SQL: LiteralString = "select to_regclass('workshop.business_deletions')"
LEDGER_ENTRIES_SQL: LiteralString = (
    "select document ->> 'deleted_business_id' from workshop.business_deletions"
)
BATCH_ROWS: int = 5000

type Connection = psycopg.Connection[TupleRow]


def ledger_business_ids(
    connection: Connection, mirrored: Sequence[BusinessId]
) -> list[str]:
    """The mirrored businesses and those of the restored database's own ledger."""

    ids: list[str] = [str(business_id) for business_id in mirrored]
    row = connection.execute(LEDGER_TABLE_SQL).fetchone()
    if row is not None and row[0] is not None:
        ids += [
            str(entry[0])
            for entry in connection.execute(LEDGER_ENTRIES_SQL).fetchall()
            if entry[0] is not None
        ]

    return sorted(set(ids))


def apply_deletion_ledger(
    connection: Connection, mirrored: Sequence[BusinessId]
) -> DeletionLedgerApplication:
    """Delete the ledger's businesses' rows again; count what is left of them."""

    business_ids: list[str] = ledger_business_ids(connection, mirrored)
    tables: list[DocumentCollectionName] = ledger_erase_order(
        [DocumentCollectionName(table) for table in list_business_tables(connection)]
    )
    erased: int = 0
    remaining: int = 0
    if business_ids:
        for table in tables:
            while True:
                batch: int = delete_business_batch(
                    connection, str(table), business_ids, BATCH_ROWS
                )
                erased += batch
                if batch < BATCH_ROWS:
                    break

        remaining = sum(
            count_business_rows(connection, str(table), business_ids)
            for table in tables
        )

    return DeletionLedgerApplication(
        deleted_businesses=LedgerBusinessCount(len(business_ids)),
        erased_rows=DeletedRowCount(erased),
        remaining_rows=ResurrectedRowCount(remaining),
    )
