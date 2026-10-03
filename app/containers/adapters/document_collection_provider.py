"""
Typed provider of one document collection: every collection is built by the
storage factory from the same settings, connection pool, storage scope and
clock, so DATABASE_URL switches all of them to Postgres at once.
"""

from base_pydantic_schemas import PersistentDocument
from dependency_injector.providers import Singleton

from app.adapters.storage.postgres.document_collection_factory import (
    build_document_collection,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.document_store import DocumentCollectionAdapterContract


def document_collection[StoredDocument: PersistentDocument](
    document_type: type[StoredDocument],
    collection_name: str,
    config: ConfigContainer,
    clients: ClientsContainer,
    utilities: UtilitiesContainer,
    time_provider: TimeProviderContainer,
) -> Singleton[DocumentCollectionAdapterContract[StoredDocument]]:
    """Singleton collection of `document_type` stored under `collection_name`."""

    return Singleton(
        build_document_collection,
        document_type=document_type,
        collection_name=collection_name,
        settings=config.app_settings,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
