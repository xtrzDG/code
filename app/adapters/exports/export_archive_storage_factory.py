"""Choose where the platform keeps the archives of full business exports."""

from pathlib import Path

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    EncryptedObjectExportArchiveStorageAdapter,
)
from app.adapters.exports.local_export_archive_storage_adapter import (
    LocalExportArchiveStorageAdapter,
)
from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.configurations.app_settings import AppSettings


def build_export_archive_storage(
    settings: AppSettings,
    object_storage_client: ObjectStorageClientContract | None,
) -> ExportArchiveStorageContract:
    """
    Where call recordings go, export archives go too: the EU bucket, each
    archive encrypted with its business's key, when RECORDINGS_STORAGE=s3;
    otherwise files under RECORDINGS_DIRECTORY (development).
    """

    if object_storage_client is None or settings.encryption_key is None:
        return LocalExportArchiveStorageAdapter(
            Path(str(settings.recordings_directory))
        )

    return EncryptedObjectExportArchiveStorageAdapter(
        client=object_storage_client,
        master_secret=settings.encryption_key,
        previous_master_secrets=settings.previous_encryption_keys,
    )
