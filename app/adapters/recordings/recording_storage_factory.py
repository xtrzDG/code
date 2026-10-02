"""Choose where the platform keeps call recordings itself."""

from pathlib import Path

from app.adapters.recordings.encrypted_object_recording_storage_adapter import (
    EncryptedObjectRecordingStorageAdapter,
)
from app.adapters.recordings.local_recording_storage_adapter import (
    LocalRecordingStorageAdapter,
)
from app.contracts.object_storage import ObjectStorageClientContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.configurations.app_settings import AppSettings


def build_own_recording_storage(
    settings: AppSettings,
    object_storage_client: ObjectStorageClientContract | None,
) -> RecordingStorageAdapterContract:
    """
    EU object storage, each recording encrypted with its business's key,
    when RECORDINGS_STORAGE=s3 (the settings refuse it without a bucket or
    ENCRYPTION_KEY); otherwise files under RECORDINGS_DIRECTORY
    (development: one server, one disk).
    """

    if object_storage_client is None or settings.encryption_key is None:
        return LocalRecordingStorageAdapter(Path(str(settings.recordings_directory)))

    return EncryptedObjectRecordingStorageAdapter(
        client=object_storage_client,
        master_secret=settings.encryption_key,
    )
