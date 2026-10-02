"""A played recording is kept in memory briefly: seeking downloads it once."""

from app.adapters.recordings.cached_recording_storage_adapter import (
    CachedRecordingStorageAdapter,
)
from app.schemas.typings.conversations.strings import RecordingStoragePath
from tests.brain.cabinet_fakes import InMemoryRecordingStorage
from tests.users.accounts_testbed import AdjustableClock

FIRST: RecordingStoragePath = RecordingStoragePath("elevenlabs/conversations/conv_1")
SECOND: RecordingStoragePath = RecordingStoragePath("elevenlabs/conversations/conv_2")


def build_cache(
    max_bytes: int = 1_000,
) -> tuple[CachedRecordingStorageAdapter, InMemoryRecordingStorage, AdjustableClock]:
    storage = InMemoryRecordingStorage()
    storage.recordings[str(FIRST)] = b"a" * 400
    storage.recordings[str(SECOND)] = b"b" * 400
    clock = AdjustableClock()
    cache = CachedRecordingStorageAdapter(
        storage,
        clock.build_wall_clock(),
        keep_seconds=300,
        max_bytes=max_bytes,
    )
    return cache, storage, clock


def test_a_recording_is_read_once_while_it_is_kept() -> None:
    cache, storage, clock = build_cache()

    first = cache.read(FIRST)
    clock.advance(299)
    again = cache.read(FIRST)
    clock.advance(2)
    after_expiry = cache.read(FIRST)

    assert first == again == after_expiry
    assert storage.reads == [str(FIRST), str(FIRST)]


def test_the_cache_is_bounded_and_forgets_deleted_recordings() -> None:
    cache, storage, _ = build_cache(max_bytes=700)

    cache.read(FIRST)
    cache.read(SECOND)  # the two do not fit: the first one is dropped
    cache.read(SECOND)
    cache.read(FIRST)
    cache.delete(FIRST)

    assert cache.read(FIRST) is None
    assert storage.reads == [str(FIRST), str(SECOND), str(FIRST), str(FIRST)]


def test_a_recording_larger_than_the_cache_is_not_kept() -> None:
    cache, storage, _ = build_cache(max_bytes=100)

    cache.read(FIRST)
    cache.read(FIRST)

    assert storage.reads == [str(FIRST), str(FIRST)]
