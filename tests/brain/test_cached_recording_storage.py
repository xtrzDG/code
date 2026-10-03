"""A played recording is kept in memory briefly: seeking downloads it once."""

from app.adapters.recordings.cached_recording_storage_adapter import (
    CachedRecordingStorageAdapter,
)
from app.schemas.dto.call_recordings import RecordingByteRange, RecordingLocation
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import RecordingByteOffset
from app.schemas.typings.conversations.strings import RecordingStoragePath
from tests.brain.cabinet_fakes import InMemoryRecordingStorage
from tests.users.accounts_testbed import AdjustableClock

BUSINESS_ID: BusinessId = BusinessId()
FIRST: RecordingLocation = RecordingLocation(
    business_id=BUSINESS_ID,
    path=RecordingStoragePath("elevenlabs/conversations/conv_1"),
)
SECOND: RecordingLocation = RecordingLocation(
    business_id=BUSINESS_ID,
    path=RecordingStoragePath("elevenlabs/conversations/conv_2"),
)
ARCHIVED: RecordingLocation = RecordingLocation(
    business_id=BUSINESS_ID,
    path=RecordingStoragePath("businesses/b/calls/c.mp3"),
)


def build_cache(
    max_bytes: int = 1_000,
) -> tuple[CachedRecordingStorageAdapter, InMemoryRecordingStorage, AdjustableClock]:
    storage = InMemoryRecordingStorage()
    storage.recordings[str(FIRST.path)] = b"a" * 400
    storage.recordings[str(SECOND.path)] = b"b" * 400
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
    assert storage.reads == [str(FIRST.path), str(FIRST.path)]


def test_the_cache_is_bounded_and_forgets_deleted_recordings() -> None:
    cache, storage, _ = build_cache(max_bytes=700)

    cache.read(FIRST)
    cache.read(SECOND)  # the two do not fit: the first one is dropped
    cache.read(SECOND)
    cache.read(FIRST)
    cache.delete(FIRST)

    assert cache.read(FIRST) is None
    assert storage.reads == [
        str(FIRST.path),
        str(SECOND.path),
        str(FIRST.path),
        str(FIRST.path),
    ]


def test_a_recording_larger_than_the_cache_is_not_kept() -> None:
    cache, storage, _ = build_cache(max_bytes=100)

    cache.read(FIRST)
    cache.read(FIRST)

    assert storage.reads == [str(FIRST.path), str(FIRST.path)]


def test_parts_come_from_the_kept_recording() -> None:
    cache, storage, _ = build_cache()

    whole = cache.read(FIRST)
    part = cache.read(
        FIRST,
        RecordingByteRange(
            first_byte=RecordingByteOffset(10), last_byte=RecordingByteOffset(19)
        ),
    )

    assert whole is not None and part is not None
    assert (part.content, int(part.first_byte), int(part.total_bytes)) == (
        b"a" * 10,
        10,
        400,
    )
    assert storage.reads == [str(FIRST.path)]


def test_archived_recordings_are_read_by_range_and_not_kept() -> None:
    cache, storage, _ = build_cache()
    storage.recordings[str(ARCHIVED.path)] = b"c" * 100
    tail = RecordingByteRange(first_byte=RecordingByteOffset(90))

    first = cache.read(ARCHIVED, tail)
    second = cache.read(ARCHIVED, tail)

    assert first == second
    assert first is not None and first.content == b"c" * 10
    assert storage.reads == [str(ARCHIVED.path), str(ARCHIVED.path)]
