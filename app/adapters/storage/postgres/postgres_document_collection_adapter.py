from collections.abc import Callable, Generator
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
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.storage import CollectionIsolation
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_tenancy import read_document_business_id


class PostgresDocumentCollectionAdapter[StoredDocument: PersistentDocument](
    DocumentCollectionAdapterContract[StoredDocument]
):
    """
    One document collection stored as one Postgres table (EU region).

    Table `workshop.<collection_name>` (created by migrations): `document_key`
    (primary key), `business_id` (copied from the document: its `business_id`,
    or its own id for a business), `document` (JSONB), `created_at` and
    `updated_at` (UNIX microseconds of the first and the last write) and an
    identity `row_sequence` that keeps the first-write order stable.

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
    documents in first-write order, like the in-memory adapter.
    """

    def __init__(
        self,
        document_type: type[StoredDocument],
        collection_name: DocumentCollectionName,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
        isolation: CollectionIsolation,
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

    @property
    def collection_name(self) -> DocumentCollectionName:
        return self._collection_name

    @property
    def isolation(self) -> CollectionIsolation:
        return self._isolation

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        serialized_document: str = document.model_dump_json()
        business_id: BusinessId | None = read_document_business_id(document)
        written_at: int = int(self._wall_clock.now_unix())
        with self._transaction() as (connection, _):
            connection.execute(
                self._queries.upsert,
                (
                    document_key,
                    None if business_id is None else str(business_id),
                    serialized_document,
                    written_at,
                    written_at,
                ),
            )

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

            changed: StoredDocument | None = change(
                self._document_type.model_validate_json(self._read_text(row))
            )
            if changed is None:
                return None

            serialized_document: str = changed.model_dump_json()
            business_id: BusinessId | None = read_document_business_id(changed)
            written_at: int = int(self._wall_clock.now_unix())
            connection.execute(
                self._queries.upsert,
                (
                    document_key,
                    None if business_id is None else str(business_id),
                    serialized_document,
                    written_at,
                    written_at,
                ),
            )

        return self._document_type.model_validate_json(serialized_document)

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

        if row is None:
            return None

        return self._document_type.model_validate_json(self._read_text(row))

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

        return [
            self._document_type.model_validate_json(self._read_text(row))
            for row in rows
        ]

    def list_by_field(self, field_name: str, value: str) -> list[StoredDocument]:
        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                rows: list[TupleRow] = connection.execute(
                    self._queries.list_by_field(field_name, is_in_business=False),
                    (value,),
                ).fetchall()
            else:
                rows = connection.execute(
                    self._queries.list_by_field(field_name, is_in_business=True),
                    (scoped_business_id, value),
                ).fetchall()

        return [
            self._document_type.model_validate_json(self._read_text(row))
            for row in rows
        ]

    def delete(self, document_key: str) -> None:
        with self._transaction() as (connection, scoped_business_id):
            if scoped_business_id is None:
                connection.execute(self._queries.delete, (document_key,))
            else:
                connection.execute(
                    self._queries.delete_in_business,
                    (document_key, scoped_business_id),
                )

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

    def _read_text(self, row: TupleRow) -> str:
        document_text: object = row[0]
        if not isinstance(document_text, str):
            raise ExternalServiceError(
                f"Collection {str(self._collection_name)!r} returned a document "
                f"that is not JSON text ({type(document_text).__name__})."
            )

        return document_text
