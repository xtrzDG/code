from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.media_collections_container import (
    MediaCollectionsContainer,
)
from app.repositories.message_media_repository import MessageMediaRepository
from app.repositories.widget_upload_repository import WidgetUploadRepository


class MediaRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the files customers send (migration 1081) and of
    the files website chat visitors upload before their message (1191).
    `RepositoriesContainer` extends it, so it is read as
    `repositories.message_media_repo` and `repositories.widget_upload_repo`
    like every other repository.
    """

    media_collections: MediaCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    message_media_repo: Singleton[MessageMediaRepository] = Singleton(
        MessageMediaRepository,
        collection=media_collections.message_media_collection,
    )
    widget_upload_repo: Singleton[WidgetUploadRepository] = Singleton(
        WidgetUploadRepository,
        collection=media_collections.widget_upload_collection,
    )
