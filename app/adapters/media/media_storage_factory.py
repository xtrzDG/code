"""Choose where the platform keeps the files customers send."""

from pathlib import Path

from app.adapters.media.encrypted_object_media_storage_adapter import (
    EncryptedObjectMediaStorageAdapter,
)
from app.adapters.media.local_media_storage_adapter import LocalMediaStorageAdapter
from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.configurations.app_settings import AppSettings


def build_media_storage(
    settings: AppSettings,
    object_storage_client: ObjectStorageClientContract | None,
) -> MediaStorageAdapterContract:
    """
    Where call recordings go, customer files go too: the EU bucket, each
    file encrypted with its business's key, when RECORDINGS_STORAGE=s3;
    otherwise files under RECORDINGS_DIRECTORY (development).
    """

    if object_storage_client is None or settings.encryption_key is None:
        return LocalMediaStorageAdapter(Path(str(settings.recordings_directory)))

    return EncryptedObjectMediaStorageAdapter(
        client=object_storage_client,
        master_secret=settings.encryption_key,
        previous_master_secrets=settings.previous_encryption_keys,
    )
