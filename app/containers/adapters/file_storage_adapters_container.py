"""Files the platform keeps: call recordings and full business exports."""

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.exports.export_archive_storage_factory import (
    build_export_archive_storage,
)
from app.adapters.recordings.cached_recording_storage_adapter import (
    CachedRecordingStorageAdapter,
)
from app.adapters.recordings.recording_storage_factory import (
    build_own_recording_storage,
)
from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.recording_storage import RecordingStorageAdapterContract


class FileStorageAdaptersContainer(containers.DeclarativeContainer):
    """
    Recordings of calls (the voice platform's storage until they are
    archived, then the platform's own) and the archives of full business
    exports beside them.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    # Recordings the platform keeps itself: EU object storage encrypted per
    # business (RECORDINGS_STORAGE=s3), files of this server in development.
    own_recording_storage: Singleton[RecordingStorageAdapterContract] = Singleton(
        build_own_recording_storage,
        settings=config.app_settings,
        object_storage_client=clients.object_storage_client,
    )
    # ElevenLabs keeps call audio in its own (EU) storage until it is
    # archived; other paths are the platform's own.
    platform_recording_storage: Singleton[ElevenLabsRecordingStorageAdapter] = (
        Singleton(
            ElevenLabsRecordingStorageAdapter,
            elevenlabs_client=clients.elevenlabs_client,
            fallback=own_recording_storage,
        )
    )
    # The voice platform hands out a recording only whole, and a player asks
    # for parts while it plays and seeks: keep a played one in memory for a
    # few minutes instead of downloading it again.
    recording_storage: Singleton[CachedRecordingStorageAdapter] = Singleton(
        CachedRecordingStorageAdapter,
        storage=platform_recording_storage,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Archives of full business exports, beside the recordings.
    export_archive_storage: Singleton[ExportArchiveStorageContract] = Singleton(
        build_export_archive_storage,
        settings=config.app_settings,
        object_storage_client=clients.object_storage_client,
    )
