from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.meta_connections import MetaConnectionStateDocument


class MetaConnectionCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collection of Meta's self-serve connection (migration
    1212): the Facebook sign-ins owners start on the Channels page. A
    sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    meta_connection_state_collection = document_collection(
        MetaConnectionStateDocument,
        "meta_connection_states",
        config,
        clients,
        utilities,
        time_provider,
    )
