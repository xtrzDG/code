from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.message_media import MessageMediaDocument


class MediaCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collection of the files customers send (migration 1081):
    one row per stored voice note or photo. A sibling of
    DocumentCollectionsContainer with the same storage factory (Postgres
    with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    message_media_collection = document_collection(
        MessageMediaDocument,
        "message_media",
        config,
        clients,
        utilities,
        time_provider,
    )
