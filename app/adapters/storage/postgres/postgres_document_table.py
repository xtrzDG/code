"""One document table: its statements, transactions with the RLS scope, decoding."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager

import psycopg
from base_pydantic_schemas import PersistentDocument
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.postgres.document_table_queries import (
    DocumentTableQueries,
    build_document_table_queries,
)
from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
    translate_storage_error,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.storage import CollectionIsolation, LookupFieldKind
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.utilities.storage.document_lookup_fields import declared_lookup_fields
from app.utilities.storage.document_tenancy import read_document_business_id


class PostgresDocumentTable[StoredDocument: PersistentDocument]:
    """
    Base of the Postgres document collection: the table's statements and
    lookup fields, one transaction per operation with the row-level
    security scope applied, and the decoding of rows into fresh documents.
    """

    def __init__(
        self,
        document_type: type[StoredDocument],
        collection_name: DocumentCollectionName,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
        isolation: CollectionIsolation,
        lookup_fields: Mapping[DocumentFieldPath, LookupFieldKind] | None = None,
    ) -> None:
        self._document_type: type[StoredDocument] = document_type
        self._collection_name: DocumentCollectionName = collection_name
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._isolation: CollectionIsolation = isolation
        self._platform_scope: StorageScope = StorageScope.platform_wide()
        self._queries: DocumentTableQueries = build_document_table_queries(
            collection_name
        )
        self._lookup_fields: dict[DocumentFieldPath, LookupFieldKind] = (
            declared_lookup_fields(collection_name, document_type)
            if lookup_fields is None
            else dict(lookup_fields)
        )

    @property
    def collection_name(self) -> DocumentCollectionName:
        return self._collection_name

    @property
    def isolation(self) -> CollectionIsolation:
        return self._isolation

    @contextmanager
    def _transaction(self) -> Generator[tuple[PostgresConnection, str | None]]:
        """
        One transaction with the RLS scope applied.

        Yields the connection and the business id of a business scope (None
        when platform-wide), for the explicit filter in queries.
        """

        scope: StorageScope = self._effective_scope()
        scoped_business_id: str | None = (
            None if scope.business_id is None else str(scope.business_id)
        )
        try:
            with self._connection_pool.transaction() as connection:
                apply_storage_scope(connection, scope)
                yield connection, scoped_business_id
        except psycopg.Error as error:
            application_error = translate_storage_error(
                error,
                str(self._collection_name),
            )
            if application_error is None:
                raise

            raise application_error from error

    def _effective_scope(self) -> StorageScope:
        if self._isolation is CollectionIsolation.PLATFORM:
            return self._platform_scope

        return self._storage_scope.current()

    def _write_parameters(
        self,
        document_key: str,
        document: StoredDocument,
    ) -> tuple[str, str | None, str, int, int]:
        """Parameters of the upsert and insert statements."""

        business_id: BusinessId | None = read_document_business_id(document)
        written_at: int = int(self._wall_clock.now_unix())
        return (
            document_key,
            None if business_id is None else str(business_id),
            document.model_dump_json(),
            written_at,
            written_at,
        )

    def _decode(self, row: TupleRow) -> StoredDocument:
        return self._document_type.model_validate_json(self._read_text(row))

    def _decode_all(self, rows: list[TupleRow]) -> list[StoredDocument]:
        return [self._decode(row) for row in rows]

    def _read_text(self, row: TupleRow) -> str:
        document_text: object = row[0]
        if not isinstance(document_text, str):
            raise ExternalServiceError(
                f"Collection {str(self._collection_name)!r} returned a document "
                f"that is not JSON text ({type(document_text).__name__})."
            )

        return document_text

    def _label(self) -> str:
        return f"collection {str(self._collection_name)!r}"
