"""
Choose the document storage for the container wiring.

With `DATABASE_URL` set every collection is a Postgres table; without it
collections live in memory (tests, demos). Use one shared connection pool and
one shared storage scope for all collections of a process:

    pool = build_postgres_connection_pool(settings)
    scope = StorageScopeContext()
    users = build_document_collection(
        UserDocument, "users", settings, connection_pool=pool, storage_scope=scope
    )
"""

from base_pydantic_schemas import PersistentDocument
from base_typed_string import BaseTypedStringConstraintViolationError
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.storage import StorageScopeContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.storage import CollectionIsolation
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_lookup_fields import declared_lookup_fields
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext

# A request or job statement that runs longer is cancelled by the server;
# a transaction left open longer (a stuck thread) is ended by it.
STATEMENT_TIMEOUT_SECONDS: int = 10
IDLE_IN_TRANSACTION_TIMEOUT_SECONDS: int = 30


def build_postgres_connection_pool(
    settings: AppSettings,
) -> PostgresConnectionPoolClient | None:
    """
    The process-wide pool when `DATABASE_URL` is set, otherwise None: up to
    DB_POOL_SIZE connections, each with the statement and idle-transaction
    timeouts above (the migration commands use their own, longer ones);
    connections idle for DB_POOL_MAX_IDLE_SECONDS close down to
    DB_POOL_MIN_SIZE.
    """

    if settings.database_url is None:
        return None

    return PostgresConnectionPoolClient(
        database_url=settings.database_url,
        max_size=int(settings.db_pool_size),
        statement_timeout_seconds=STATEMENT_TIMEOUT_SECONDS,
        idle_in_transaction_timeout_seconds=IDLE_IN_TRANSACTION_TIMEOUT_SECONDS,
        min_size=int(settings.db_pool_min_size),
        max_idle_seconds=float(int(settings.db_pool_max_idle_seconds)),
    )


def build_document_collection[StoredDocument: PersistentDocument](
    document_type: type[StoredDocument],
    collection_name: str,
    settings: AppSettings,
    connection_pool: PostgresConnectionPoolClient | None = None,
    storage_scope: StorageScopeContract | None = None,
    wall_clock: WallClock[Microseconds] | None = None,
    isolation: CollectionIsolation | None = None,
) -> DocumentCollectionAdapterContract[StoredDocument]:
    """
    A Postgres collection when `settings.database_url` is set, else in-memory.

    The name is validated in both cases, so a wiring mistake shows up in
    tests too. A tenant collection refuses code outside a storage scope in
    both (fail-closed); pass the process's shared `StorageScopeContext`.
    Without one, the in-memory collection is not guarded and the Postgres
    one gets a scope of its own that nothing enters (it refuses every call).
    Postgres-only arguments fall back to: a pool of its own (pass the shared
    one instead), the system clock, and the isolation inferred from the
    document type (`infer_collection_isolation`).
    """

    validated_collection_name: DocumentCollectionName = validate_collection_name(
        collection_name
    )
    effective_isolation: CollectionIsolation = (
        isolation
        if isolation is not None
        else infer_collection_isolation(document_type)
    )
    if settings.database_url is None:
        return InMemoryDocumentCollectionAdapter[StoredDocument](
            document_type,
            declared_lookup_fields(validated_collection_name, document_type),
            tenant_scope=(
                storage_scope
                if effective_isolation is CollectionIsolation.TENANT
                else None
            ),
        )

    return PostgresDocumentCollectionAdapter[StoredDocument](
        document_type=document_type,
        collection_name=validated_collection_name,
        connection_pool=(
            connection_pool
            if connection_pool is not None
            else PostgresConnectionPoolClient(database_url=settings.database_url)
        ),
        storage_scope=(
            storage_scope if storage_scope is not None else StorageScopeContext()
        ),
        wall_clock=(
            wall_clock
            if wall_clock is not None
            else WallClock(preferred_time_unit_type=Microseconds)
        ),
        isolation=effective_isolation,
    )


def validate_collection_name(collection_name: str) -> DocumentCollectionName:
    """The typed name; ValidationFailedError for anything not a safe table name."""

    try:
        return DocumentCollectionName(collection_name)
    except BaseTypedStringConstraintViolationError as error:
        raise ValidationFailedError(
            f"Collection name {collection_name!r} must be lowercase snake case "
            "starting with a letter, 2 to 63 characters."
        ) from error
