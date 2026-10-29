"""Choose the recordings object storage client for the container wiring."""

from typed_time_provider import Microseconds, WallClock

from app.clients.object_storage.s3_object_storage_client import S3ObjectStorageClient
from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.storage import RecordingStorageKind


def build_object_storage_client(
    settings: AppSettings,
) -> ObjectStorageClientContract | None:
    """
    The S3-compatible client with RECORDINGS_STORAGE=s3, else None. It
    signs with the system clock: a presigned URL must be valid at the
    object storage's real time, whatever clock the rest of the process uses.
    """

    if (
        settings.recording_storage_kind is not RecordingStorageKind.OBJECT_STORAGE
        or settings.recordings_object_storage is None
    ):
        return None

    return S3ObjectStorageClient(
        connection=settings.recordings_object_storage,
        wall_clock=WallClock(preferred_time_unit_type=Microseconds),
    )
