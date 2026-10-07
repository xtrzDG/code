from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.media_collections_container import (
    MediaCollectionsContainer,
)
from app.repositories.message_media_repository import MessageMediaRepository


class MediaRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repository of the files customers send (migration 1081).
    `RepositoriesContainer` extends it, so it is read as
    `repositories.message_media_repo` like every other repository.
    """

    media_collections: MediaCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    message_media_repo: Singleton[MessageMediaRepository] = Singleton(
        MessageMediaRepository,
        collection=media_collections.message_media_collection,
    )
