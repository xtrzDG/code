"""Keyset pages and aggregations of one Postgres document table."""

from base_pydantic_schemas import PersistentDocument
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.document_listing_sql import (
    compose_aggregation,
    compose_page,
)
from app.adapters.storage.postgres.postgres_document_table import (
    PostgresDocumentTable,
)
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import (
    DocumentBucketIndex,
    DocumentCount,
)
from app.schemas.typings.storage.integers import DocumentFieldInteger, DocumentFieldSum
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_query_rules import (
    require_valid_aggregation,
    require_valid_page,
)


class PostgresDocumentListing[StoredDocument: PersistentDocument](
    PostgresDocumentTable[StoredDocument]
):
    """
    `page_by` and `count_by` of the Postgres collection: one statement each,
    in the transaction and row-level security scope of every operation
    (`document_listing_sql` has the SQL).
    """

    def page_by(self, query: DocumentPageQuery) -> list[StoredDocument]:
        require_valid_page(self._lookup_fields, query, self._label())
        with self._transaction() as (connection, scoped_business_id):
            statement, parameters = compose_page(
                self._queries.table,
                self._collection_name,
                self._lookup_fields,
                query,
                scoped_business_id,
            )
            rows: list[TupleRow] = connection.execute(statement, parameters).fetchall()

        return self._decode_all(rows)

    def count_by(self, aggregation: DocumentAggregation) -> list[DocumentGroupCount]:
        require_valid_aggregation(self._lookup_fields, aggregation, self._label())
        with self._transaction() as (connection, scoped_business_id):
            statement, parameters = compose_aggregation(
                self._queries.table,
                self._collection_name,
                self._lookup_fields,
                aggregation,
                scoped_business_id,
            )
            rows: list[TupleRow] = connection.execute(statement, parameters).fetchall()

        return [self._read_group(row, aggregation) for row in rows]

    def _read_group(
        self,
        row: TupleRow,
        aggregation: DocumentAggregation,
    ) -> DocumentGroupCount:
        """A result row: group values, bucket, count, total, largest value."""

        cells: list[object] = list(row)
        values: tuple[DocumentFieldText | None, ...] = tuple(
            None if cell is None else DocumentFieldText(str(cell))
            for cell in cells[: len(aggregation.group_by)]
        )
        position: int = len(aggregation.group_by)
        bucket: DocumentBucketIndex | None = None
        if aggregation.buckets is not None:
            bucket = DocumentBucketIndex(self._read_integer(cells[position]))
            position += 1

        count = DocumentCount(self._read_integer(cells[position]))
        position += 1
        total: DocumentFieldSum | None = None
        if aggregation.total_of is not None:
            total = DocumentFieldSum(self._read_integer(cells[position]))
            position += 1

        latest: DocumentFieldInteger | None = None
        if aggregation.latest_of is not None and cells[position] is not None:
            latest = DocumentFieldInteger(self._read_integer(cells[position]))

        return DocumentGroupCount(
            values=values, bucket=bucket, count=count, total=total, latest=latest
        )

    def _read_integer(self, cell: object) -> int:
        if not isinstance(cell, int) or isinstance(cell, bool):
            raise ExternalServiceError(
                f"Collection {str(self._collection_name)!r} returned a count that "
                f"is not an integer ({type(cell).__name__})."
            )

        return cell
