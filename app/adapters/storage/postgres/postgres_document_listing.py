"""Keyset pages and aggregations of one Postgres document table."""

from collections.abc import Sequence

from base_pydantic_schemas import PersistentDocument
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.document_listing_sql import (
    compose_aggregation,
    compose_latest,
    compose_page,
)
from app.adapters.storage.postgres.postgres_document_table import (
    PostgresDocumentTable,
)
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentLatestQuery, DocumentPageQuery
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import (
    DocumentBucketIndex,
    DocumentCount,
)
from app.schemas.typings.storage.integers import DocumentFieldInteger, DocumentFieldSum
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_query_rules import (
    require_valid_aggregation,
    require_valid_latest,
    require_valid_page,
)


class PostgresDocumentListing[StoredDocument: PersistentDocument](
    PostgresDocumentTable[StoredDocument]
):
    """
    `get_many`, `page_by`, `latest_by` and `count_by` of the Postgres
    collection: one statement each, in the transaction and row-level
    security scope of every operation (`document_listing_sql` has the SQL).
    """

    def get_many(self, document_keys: Sequence[str]) -> list[StoredDocument]:
        keys: list[str] = list(dict.fromkeys(document_keys))
        if not keys:
            return []

        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                rows: list[TupleRow] = connection.execute(
                    self._queries.get_many, (keys,)
                ).fetchall()
            else:
                rows = connection.execute(
                    self._queries.get_many_in_business, (keys, scoped_business_id)
                ).fetchall()

        return self._decode_all(rows)

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

    def latest_by(self, query: DocumentLatestQuery) -> list[StoredDocument]:
        require_valid_latest(self._lookup_fields, query, self._label())
        if not query.groups:
            return []

        with self._transaction() as (connection, scoped_business_id):
            statement, parameters = compose_latest(
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
        """A result row: group values, bucket, count, totals, largest value."""

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
        totals: tuple[DocumentFieldSum, ...] = tuple(
            DocumentFieldSum(self._read_integer(cell))
            for cell in cells[position : position + len(aggregation.totals_of)]
        )
        position += len(aggregation.totals_of)

        latest: DocumentFieldInteger | None = None
        if aggregation.latest_of is not None and cells[position] is not None:
            latest = DocumentFieldInteger(self._read_integer(cells[position]))

        return DocumentGroupCount(
            values=values, bucket=bucket, count=count, totals=totals, latest=latest
        )

    def _read_integer(self, cell: object) -> int:
        if not isinstance(cell, int) or isinstance(cell, bool):
            raise ExternalServiceError(
                f"Collection {str(self._collection_name)!r} returned a count that "
                f"is not an integer ({type(cell).__name__})."
            )

        return cell
