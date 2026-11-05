"""A recording storage that keeps audio in memory and remembers deletions."""

import threading
from collections.abc import Callable

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.utilities.recordings.recording_byte_ranges import cut_recording_part


class InMemoryRecordingStorage(RecordingStorageAdapterContract):
    """
    Every path in one dictionary; `failure` makes the next deletes raise it,
    and `on_delete` runs after each deletion (another writer acting then).
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self.audio: dict[RecordingStoragePath, RecordingAudio] = {}
        self.deleted: list[RecordingStoragePath] = []
        self.failure: ApplicationError | None = None
        self.on_delete: Callable[[], None] | None = None

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        audio: RecordingAudio | None = self.audio.get(location.path)
        return None if audio is None else cut_recording_part(audio, wanted)

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        with self._lock:
            self.audio[location.path] = audio

    def delete(self, location: RecordingLocation) -> None:
        if self.failure is not None:
            raise self.failure

        with self._lock:
            self.audio.pop(location.path, None)
            self.deleted.append(location.path)
        if self.on_delete is not None:
            self.on_delete()
