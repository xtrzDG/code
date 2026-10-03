from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.security_collections_container import (
    SecurityCollectionsContainer,
)
from app.repositories.key_rotation_repository import KeyRotationRepository


class SecurityRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repository of key management (migration 1063). `RepositoriesContainer`
    extends it, so it is read as `repositories.key_rotation_repo`.
    """

    security_collections: SecurityCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    key_rotation_repo: Singleton[KeyRotationRepository] = Singleton(
        KeyRotationRepository,
        collection=security_collections.key_rotation_collection,
    )
