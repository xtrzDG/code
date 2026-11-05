import threading
from collections import OrderedDict

from typed_time_provider import Microseconds, WallClock

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.utilities.channels.voice_recordings import read_voice_platform_call_id
from app.utilities.recordings.recording_byte_ranges import cut_recording_part

RECORDING_CACHE_SECONDS: int = 300
RECORDING_CACHE_BYTES: int = 64 * 1024 * 1024
MICROSECONDS_PER_SECOND: int = 1_000_000


class CachedRecordingStorageAdapter(RecordingStorageAdapterContract):
    """
    Keeps recently played recordings of the voice platform in this
    process's memory for a few minutes: the platform hands out a recording
    only whole, so the parts a player asks for while it plays and seeks
    (byte ranges) would download all of it each time. Recordings in object
    storage are read by range and are not cached.

    The cache is private to the process (no HTTP cache holds personal
    data), bounded in total size (the least recently used recordings go
    first; one larger than the bound is not kept) and forgets a recording
    as soon as it is deleted through this adapter (retention purge, a
    contact's data deleted). A deletion in another process (the worker's
    purge) also clears the call's recording path, so playback refuses the
    recording before it would come from this cache.
    """

    def __init__(
        self,
        storage: RecordingStorageAdapterContract,
        wall_clock: WallClock[Microseconds],
        keep_seconds: int = RECORDING_CACHE_SECONDS,
        max_bytes: int = RECORDING_CACHE_BYTES,
    ) -> None:
        self._storage: RecordingStorageAdapterContract = storage
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._keep_microseconds: int = keep_seconds * MICROSECONDS_PER_SECOND
        self._max_bytes: int = max_bytes
        self._entries: OrderedDict[RecordingStoragePath, tuple[int, RecordingAudio]] = (
            OrderedDict()
        )
        self._lock: threading.Lock = threading.Lock()

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        if read_voice_platform_call_id(location.path) is None:
            return self._storage.read(location, wanted)

        path: RecordingStoragePath = location.path
        now: int = int(self._wall_clock.now_unix())
        with self._lock:
            entry: tuple[int, RecordingAudio] | None = self._entries.get(path)
            if entry is not None and entry[0] > now:
                self._entries.move_to_end(path)
                return cut_recording_part(entry[1], wanted)

            self._entries.pop(path, None)

        whole: RecordingPart | None = self._storage.read(location)
        if whole is None:
            return None

        audio = RecordingAudio(content=whole.content, media_type=whole.media_type)
        if len(audio.content) <= self._max_bytes:
            with self._lock:
                self._entries[path] = (now + self._keep_microseconds, audio)
                self._evict(now)

        return cut_recording_part(audio, wanted)

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        self._storage.store(location, audio)

    def delete(self, location: RecordingLocation) -> None:
        with self._lock:
            self._entries.pop(location.path, None)

        self._storage.delete(location)

    def _evict(self, now: int) -> None:
        for path, (expires_at, _) in list(self._entries.items()):
            if expires_at <= now:
                del self._entries[path]

        total_bytes: int = sum(
            len(audio.content) for _, audio in self._entries.values()
        )
        while total_bytes > self._max_bytes:
            _, (_, oldest) = self._entries.popitem(last=False)
            total_bytes -= len(oldest.content)
