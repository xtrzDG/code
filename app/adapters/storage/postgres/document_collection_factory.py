"""
Choose the document storage for the container wiring.

With `DATABASE_URL` set every collection is a Postgres table; without it
collections live in memory (tests, demos). Use the process's shared pools
(`build_postgres_connection_pools`) and one shared storage scope for all
collections of a process:

    pools = build_postgres_connection_pools(settings)
    scope = StorageScopeContext()
    users = build_document_collection(
        UserDocument, "users", settings, connection_pools=pools, storage_scope=scope
    )
"""

from base_pydantic_schemas import PersistentDocument
from base_typed_string import BaseTypedStringConstraintViolationError
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_collection_registry import (
    InMemoryCollectionRegistry,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.storage import StorageScopeContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.storage import CollectionIsolation
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_lookup_fields import declared_lookup_fields
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext


def build_document_collection[StoredDocument: PersistentDocument](
    document_type: type[StoredDocument],
    collection_name: str,
    settings: AppSettings,
    connection_pools: PostgresConnectionPools | None = None,
    storage_scope: StorageScopeContract | None = None,
    wall_clock: WallClock[Microseconds] | None = None,
    isolation: CollectionIsolation | None = None,
    in_memory_registry: InMemoryCollectionRegistry | None = None,
) -> DocumentCollectionAdapterContract[StoredDocument]:
    """
    A Postgres collection when `settings.database_url` is set, else in-memory.

    The name is validated in both cases, so a wiring mistake shows up in
    tests too. A tenant collection refuses code outside a storage scope in
    both (fail-closed); pass the process's shared `StorageScopeContext`.
    Without one, the in-memory collection is not guarded and the Postgres
    one gets a scope of its own that nothing enters (it refuses every call).
    Postgres-only arguments fall back to: one pool of its own on
    DATABASE_URL (pass the process's shared pools instead), the system
    clock, and the isolation inferred from the document type
    (`infer_collection_isolation`). An in-memory collection joins
    `in_memory_registry`, the process's list a business's deletion walks.
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
        collection = InMemoryDocumentCollectionAdapter[StoredDocument](
            document_type,
            declared_lookup_fields(validated_collection_name, document_type),
            tenant_scope=(
                storage_scope
                if effective_isolation is CollectionIsolation.TENANT
                else None
            ),
        )
        if in_memory_registry is not None:
            in_memory_registry.register(validated_collection_name, collection)
        return collection

    return PostgresDocumentCollectionAdapter[StoredDocument](
        document_type=document_type,
        collection_name=validated_collection_name,
        connection_pools=(
            connection_pools
            if connection_pools is not None
            else PostgresConnectionPools.single(
                PostgresConnectionPoolClient(database_url=settings.database_url)
            )
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
