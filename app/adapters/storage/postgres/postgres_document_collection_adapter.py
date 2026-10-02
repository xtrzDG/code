from collections.abc import Callable, Sequence

from base_pydantic_schemas import PersistentDocument
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.document_lookup_sql import (
    compose_count,
    compose_delete_batch,
    compose_select,
)
from app.adapters.storage.postgres.postgres_document_table import (
    PostgresDocumentTable,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
    DocumentLookup,
)
from app.schemas.typings.storage.booleans import IsDescendingOrder, IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_lookup_fields import require_valid_lookup

# Rows one purge transaction deletes; small batches keep locks short.
DELETE_BATCH_SIZE: DocumentQueryLimit = DocumentQueryLimit(1000)


class PostgresDocumentCollectionAdapter[StoredDocument: PersistentDocument](
    PostgresDocumentTable[StoredDocument],
    DocumentCollectionAdapterContract[StoredDocument],
):
    """
    One document collection stored as one Postgres table (EU region).

    Table `workshop.<collection_name>` (created by migrations): `document_key`
    (primary key), `business_id` (copied from the document: its `business_id`,
    or its own id for a business), `document` (JSONB), `created_at` and
    `updated_at` (UNIX microseconds of the first and the last write), an
    identity `row_sequence` that keeps the first-write order stable, and
    generated `doc_<field>` columns of the lookup fields (migration 1010).

    Business isolation has two lines of defence. Repositories already read
    tenant documents only together with their business id. Below them, every
    table has row-level security (enabled and forced): each operation runs in
    its own transaction that first sets the scope with SET LOCAL semantics.
    For TENANT collections the scope is the ambient `StorageScopeContract`
    scope: inside `scoped_to_business(...)` a read sees only that business's
    rows (the query also filters by it, so the index is used) and writing or
    overwriting another business's row fails with AccessDeniedError. Outside
    of a business scope, and always for PLATFORM collections, the transaction
    runs platform-wide (`app.bypass_rls = on`).

    RLS here guards against application mistakes, not against someone who
    can run arbitrary SQL with the application's role (they can set the same
    settings). Connect with a role that is neither superuser nor BYPASSRLS,
    otherwise Postgres skips the policies.

    Documents are written with `model_dump_json()` and read back with
    `model_validate_json()` on the JSONB text, so typed primitives survive the
    round trip and callers always get fresh instances. `list_all()` returns
    documents in first-write order, like the in-memory adapter. Queries by
    lookup field are parameterized SQL on plain indexed columns
    (`document_lookup_sql`).
    """

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        with self._transaction() as (connection, _):
            connection.execute(
                self._queries.upsert,
                self._write_parameters(document_key, document),
            )

    def insert_if_absent(
        self,
        document_key: str,
        document: StoredDocument,
    ) -> IsDocumentInserted:
        """`insert ... on conflict do nothing`: atomic across processes."""

        with self._transaction() as (connection, _):
            inserted_rows: int = connection.execute(
                self._queries.insert_if_absent,
                self._write_parameters(document_key, document),
            ).rowcount

        return inserted_rows == 1

    def modify(
        self,
        document_key: str,
        change: Callable[[StoredDocument], StoredDocument | None],
    ) -> StoredDocument | None:
        """
        Read the row `for update` (other writers of it wait until this
        transaction ends), let `change` build the new document, and write it
        in the same transaction.
        """

        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                row: TupleRow | None = connection.execute(
                    self._queries.lock,
                    (document_key,),
                ).fetchone()
            else:
                row = connection.execute(
                    self._queries.lock_in_business,
                    (document_key, scoped_business_id),
                ).fetchone()

            if row is None:
                return None

            changed: StoredDocument | None = change(self._decode(row))
            if changed is None:
                return None

            parameters = self._write_parameters(document_key, changed)
            connection.execute(self._queries.upsert, parameters)

        return self._document_type.model_validate_json(parameters[2])

    def replace_if(
        self,
        document_key: str,
        document: StoredDocument,
        is_current: Callable[[StoredDocument], bool],
    ) -> bool:
        return (
            self.modify(
                document_key,
                lambda stored: document if is_current(stored) else None,
            )
            is not None
        )

    def get(self, document_key: str) -> StoredDocument | None:
        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                row: TupleRow | None = connection.execute(
                    self._queries.get,
                    (document_key,),
                ).fetchone()
            else:
                row = connection.execute(
                    self._queries.get_in_business,
                    (document_key, scoped_business_id),
                ).fetchone()

        return None if row is None else self._decode(row)

    def list_all(self) -> list[StoredDocument]:
        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                rows: list[TupleRow] = connection.execute(
                    self._queries.list_all
                ).fetchall()
            else:
                rows = connection.execute(
                    self._queries.list_in_business,
                    (scoped_business_id,),
                ).fetchall()

        return self._decode_all(rows)

    def find_one_by_field(
        self,
        field: DocumentFieldPath,
        value: DocumentFieldText,
    ) -> StoredDocument | None:
        found: list[StoredDocument] = self._select(
            DocumentLookup(
                matches=(DocumentFieldMatch(field=field, value=value),),
                limit=DocumentQueryLimit(1),
            )
        )
        return found[0] if found else None

    def list_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        return self._select(
            DocumentLookup(matches=tuple(matches), order=order, limit=limit)
        )

    def count_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        within: DocumentFieldRange | None = None,
    ) -> DocumentCount:
        lookup = DocumentLookup(matches=tuple(matches), within=within)
        require_valid_lookup(self._lookup_fields, lookup, self._label())
        with self._transaction() as (connection, scoped_business_id):
            query, parameters = compose_count(
                self._queries.table,
                self._collection_name,
                self._lookup_fields,
                lookup,
                scoped_business_id,
            )
            row: TupleRow | None = connection.execute(query, parameters).fetchone()

        count: object = None if row is None else row[0]
        return DocumentCount(count if isinstance(count, int) else 0)

    def list_by_range(
        self,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
        is_descending: IsDescendingOrder = False,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        return self._select(
            DocumentLookup(
                matches=tuple(matches),
                within=within,
                order=DocumentFieldOrder(
                    field=within.field, is_descending=is_descending
                ),
                limit=limit,
            )
        )

    def delete_by_range(
        self,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
    ) -> DocumentCount:
        """Deletes in transactions of DELETE_BATCH_SIZE rows each."""

        lookup = DocumentLookup(
            matches=tuple(matches),
            within=within,
            order=DocumentFieldOrder(field=within.field),
        )
        require_valid_lookup(self._lookup_fields, lookup, self._label())
        deleted_total: int = 0
        while True:
            with self._transaction() as (connection, scoped_business_id):
                query, parameters = compose_delete_batch(
                    self._queries.table,
                    self._collection_name,
                    self._lookup_fields,
                    lookup,
                    scoped_business_id,
                    DELETE_BATCH_SIZE,
                )
                deleted_rows: int = connection.execute(query, parameters).rowcount

            deleted_total += max(deleted_rows, 0)
            if deleted_rows < int(DELETE_BATCH_SIZE):
                return DocumentCount(deleted_total)

    def delete(self, document_key: str) -> None:
        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                connection.execute(self._queries.delete, (document_key,))
            else:
                connection.execute(
                    self._queries.delete_in_business,
                    (document_key, scoped_business_id),
                )

    def _select(self, lookup: DocumentLookup) -> list[StoredDocument]:
        require_valid_lookup(self._lookup_fields, lookup, self._label())
        with self._transaction() as (connection, scoped_business_id):
            query, parameters = compose_select(
                self._queries.table,
                self._collection_name,
                self._lookup_fields,
                lookup,
                scoped_business_id,
            )
            rows: list[TupleRow] = connection.execute(query, parameters).fetchall()

        return self._decode_all(rows)
