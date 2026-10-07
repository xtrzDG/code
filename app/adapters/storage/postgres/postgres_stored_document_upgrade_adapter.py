from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from base_pydantic_schemas import PersistentDocument
from psycopg.rows import TupleRow

from app.adapters.storage.document_upgrades import (
    DOCUMENT_UPCASTERS,
    FIRST_SCHEMA_VERSION,
    NO_UPCASTERS,
    DocumentUpcaster,
)
from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.adapters.storage.postgres.platform_transaction import (
    platform_transaction,
    read_document_text,
)
from app.adapters.storage.postgres.stored_document_upgrade_queries import (
    FIRST_POSITION,
    StoredDocumentUpgradeQueries,
    build_stored_document_upgrade_queries,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.storage import StoredDocumentUpgradeAdapterContract
from app.schemas.constants.storage import StoredDocumentVersionState
from app.schemas.dto.document_upgrades import (
    CollectionUpgradeReport,
    CollectionUpgradeRequest,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

# A report lists at most this many keys of documents that failed.
LISTED_FAILURES: int = 20


@dataclass
class UpgradeTally:
    """Running counts of one collection (technical record)."""

    outdated: int = 0
    upgraded: int = 0
    newer: int = 0
    changed_meanwhile: int = 0
    failed_keys: list[str] = field(default_factory=list[str])

    def report(
        self,
        collection_name: DocumentCollectionName,
        current_version: DocumentSchemaVersionNumber,
    ) -> CollectionUpgradeReport:
        return CollectionUpgradeReport(
            collection_name=collection_name,
            current_version=current_version,
            outdated=DocumentCount(self.outdated),
            upgraded=DocumentCount(self.upgraded),
            newer=DocumentCount(self.newer),
            changed_meanwhile=DocumentCount(self.changed_meanwhile),
            failed=DocumentCount(len(self.failed_keys)),
            failed_document_keys=[
                StoredDocumentKey(key) for key in self.failed_keys[:LISTED_FAILURES]
            ],
        )


class PostgresStoredDocumentUpgradeAdapter(StoredDocumentUpgradeAdapterContract):
    """
    Rewrites outdated stored documents of `workshop.<collection>` tables.

    Each batch is one platform-wide transaction (`app.bypass_rls = on`):
    select up to `batch_size` rows whose `schema_version` is not the current
    one (keyset on the `(created_at, row_sequence)` index), upgrade each
    through the collection's `PersistedDocumentCodec` (upcasters, then the
    current shape) and write it back only if the row still holds the text
    that was read, so a concurrent write by the application always wins.
    `updated_at` is kept: the content did not change, only its shape.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        collections: Sequence[DocumentCollectionDefinition] = DOCUMENT_COLLECTIONS,
        upcasters: Mapping[
            DocumentCollectionName,
            Mapping[DocumentSchemaVersionNumber, DocumentUpcaster],
        ] = DOCUMENT_UPCASTERS,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._upcasters: Mapping[
            DocumentCollectionName,
            Mapping[DocumentSchemaVersionNumber, DocumentUpcaster],
        ] = upcasters
        self._collections: dict[
            DocumentCollectionName, DocumentCollectionDefinition
        ] = {definition.name: definition for definition in collections}

    def upgrade_collection(
        self,
        request: CollectionUpgradeRequest,
    ) -> CollectionUpgradeReport:
        definition: DocumentCollectionDefinition | None = self._collections.get(
            request.collection_name
        )
        if definition is None:
            raise NotFoundError(
                f"{request.collection_name!s} is not a document collection."
            )

        codec: PersistedDocumentCodec[PersistentDocument] = PersistedDocumentCodec(
            definition.document_type,
            definition.name,
            self._upcasters.get(definition.name, NO_UPCASTERS),
        )
        current_version: DocumentSchemaVersionNumber = (
            FIRST_SCHEMA_VERSION
            if codec.current_version is None
            else codec.current_version
        )
        queries = build_stored_document_upgrade_queries(definition.name)
        tally = UpgradeTally()
        position: tuple[int, int] = FIRST_POSITION
        while True:
            with platform_transaction(
                self._connection_pool, str(definition.name)
            ) as connection:
                rows: list[TupleRow] = connection.execute(
                    queries.select_batch,
                    {
                        "after_created_at": position[0],
                        "after_row_sequence": position[1],
                        "current_version": str(int(current_version)),
                        "batch_size": int(request.batch_size),
                    },
                ).fetchall()
                for row in rows:
                    self._upgrade_row(
                        connection, queries, codec, row, request.is_dry_run, tally
                    )

            if len(rows) < int(request.batch_size):
                return tally.report(definition.name, current_version)

            position = read_position(rows[-1])

    def _upgrade_row(
        self,
        connection: PostgresConnection,
        queries: StoredDocumentUpgradeQueries,
        codec: PersistedDocumentCodec[PersistentDocument],
        row: TupleRow,
        is_dry_run: bool,
        tally: UpgradeTally,
    ) -> None:
        document_key: str = str(row[0])
        stored_text: str = read_document_text((row[1],), "migrate-documents")
        tally.outdated += 1
        try:
            state: StoredDocumentVersionState = codec.version_state(stored_text)
            if state is not StoredDocumentVersionState.OLDER:
                # The select returns no current rows: this one is newer.
                tally.newer += int(state is StoredDocumentVersionState.NEWER)
                return

            upgraded_text: str = codec.upgrade(stored_text)
        except ValueError, KeyError, TypeError:
            # Unreadable JSON or version, a document the upcasters cannot
            # make valid (pydantic's ValidationError is a ValueError), or
            # an upcaster that does not fit the data.
            tally.failed_keys.append(document_key)
            return

        if is_dry_run:
            tally.upgraded += 1
            return

        rewritten: int = connection.execute(
            queries.rewrite,
            {
                "upgraded": upgraded_text,
                "document_key": document_key,
                "stored": stored_text,
            },
        ).rowcount
        if rewritten == 1:
            tally.upgraded += 1
        else:
            tally.changed_meanwhile += 1


def read_position(row: TupleRow) -> tuple[int, int]:
    """`(created_at, row_sequence)` of a selected row."""

    created_at: object = row[2]
    row_sequence: object = row[3]
    if not isinstance(created_at, int) or not isinstance(row_sequence, int):
        raise TypeError("created_at and row_sequence must be integers.")

    return created_at, row_sequence
