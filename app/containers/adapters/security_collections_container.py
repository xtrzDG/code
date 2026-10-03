from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.key_rotations import KeyRotationDocument


class SecurityCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collection of key management (migration 1063): the latest
    re-encryption of the stored secrets. A sibling of
    DocumentCollectionsContainer with the same storage factory.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    key_rotation_collection = document_collection(
        KeyRotationDocument,
        "key_rotations",
        config,
        clients,
        utilities,
        time_provider,
    )
