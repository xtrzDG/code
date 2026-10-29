"""The voice notes and photos of the demo customers, stored as uploads are."""

from collections.abc import Sequence

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.schemas.dto.demo_data import DemoMediaFile
from app.schemas.dto.media import MediaLocation, StoredMediaFile


def store_demo_media(
    media_storage: MediaStorageAdapterContract,
    message_media_repo: MessageMediaRepoContract,
    files: Sequence[DemoMediaFile],
) -> None:
    """Each file's bytes in the media storage, then its record."""

    for file in files:
        media_storage.store(
            MediaLocation(
                business_id=file.media.business_id, path=file.media.storage_path
            ),
            StoredMediaFile(content=file.content, media_type=file.media.media_type),
        )
        message_media_repo.save(file.media)
