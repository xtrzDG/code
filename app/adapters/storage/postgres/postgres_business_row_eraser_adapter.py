from collections.abc import Sequence

from app.adapters.storage.postgres.business_row_queries import (
    count_business_rows,
    delete_business_batch,
    list_business_tables,
)
from app.adapters.storage.postgres.platform_transaction import platform_transaction
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.business_erasure import BusinessRowEraserAdapterContract
from app.schemas.dto.business_closures.business_rows import BusinessTableRows
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.business_closures.retained_tables import erase_order

TRANSACTION_LABEL: str = "business rows"
DEFAULT_BATCH_ROWS: int = 1000


class PostgresBusinessRowEraserAdapter(BusinessRowEraserAdapterContract):
    """
    A business's rows on Postgres, through the platform pool (its role,
    a member of workshop_platform, sees and may delete every business's
    rows; the tenant pool's role never could reach across). Every table of
    the schema with a business column is covered, whether or not the
    catalog names it (`knowledge_embeddings`, `document_lookup_keys`).
    Each batch of `batch_rows` rows is a short transaction of its own, so
    deleting a large business never holds a long lock on a busy table.
    """

    def __init__(
        self,
        connection_pools: PostgresConnectionPools,
        batch_rows: int = DEFAULT_BATCH_ROWS,
    ) -> None:
        self._pools: PostgresConnectionPools = connection_pools
        self._batch_rows: int = batch_rows

    def count_rows(self, business_id: BusinessId) -> list[BusinessTableRows]:
        ids: list[str] = [str(business_id)]
        with platform_transaction(self._pools.platform, TRANSACTION_LABEL) as conn:
            counts: list[tuple[str, int]] = [
                (table, count_business_rows(conn, table, ids))
                for table in list_business_tables(conn)
            ]

        return [
            BusinessTableRows(
                table=DocumentCollectionName(table), row_count=DocumentCount(count)
            )
            for table, count in counts
            if count > 0
        ]

    def erase_rows(
        self,
        business_id: BusinessId,
        tables: Sequence[DocumentCollectionName] | None = None,
    ) -> list[BusinessTableRows]:
        with platform_transaction(self._pools.platform, TRANSACTION_LABEL) as conn:
            present: list[DocumentCollectionName] = [
                DocumentCollectionName(table) for table in list_business_tables(conn)
            ]

        chosen: list[DocumentCollectionName] = erase_order(
            present if tables is None else [t for t in tables if t in present]
        )
        erased: list[BusinessTableRows] = []
        for table in chosen:
            removed: int = self._erase_table(str(table), [str(business_id)])
            if removed:
                erased.append(
                    BusinessTableRows(table=table, row_count=DocumentCount(removed))
                )

        return erased

    def _erase_table(self, table: str, business_ids: list[str]) -> int:
        removed: int = 0
        while True:
            with platform_transaction(self._pools.platform, TRANSACTION_LABEL) as conn:
                batch: int = delete_business_batch(
                    conn, table, business_ids, self._batch_rows
                )
            removed += batch
            if batch < self._batch_rows:
                return removed
