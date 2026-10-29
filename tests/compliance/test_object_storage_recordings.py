"""
Call recordings in S3-compatible EU object storage (moto's server): sealed
with the business's key before they leave the API, read back by presigned
byte-range GETs of just the chunks a player asks for.
"""

from collections.abc import Generator

import httpx
import pytest

from app.adapters.recordings.encrypted_object_recording_storage_adapter import (
    OPEN_RANGE_PART_BYTES,
    EncryptedObjectRecordingStorageAdapter,
)
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.security.recording_encryption import CHUNK_SIZE, HEADER_SIZE
from tests.compliance.moto_object_storage import (
    MotoStorage,
    RecordingTransport,
    moto_storage,
)

MASTER: PlatformSecret = PlatformSecret("recordings-master-secret-0123456789abcdef")
AUDIO: bytes = bytes(index % 241 for index in range(3 * CHUNK_SIZE + 77))
MP3: RecordingMediaType = RecordingMediaType("audio/mpeg")


@pytest.fixture(scope="module")
def storage() -> Generator[MotoStorage]:
    with moto_storage() as running:
        yield running


def recordings(
    storage: MotoStorage,
    transport: RecordingTransport | None = None,
) -> EncryptedObjectRecordingStorageAdapter:
    return EncryptedObjectRecordingStorageAdapter(storage.client(transport), MASTER)


def location(path: str, business_id: BusinessId | None = None) -> RecordingLocation:
    return RecordingLocation(
        business_id=business_id or BusinessId(), path=RecordingStoragePath(path)
    )


def span(first: int, last: int | None = None) -> RecordingByteRange:
    return RecordingByteRange(
        first_byte=RecordingByteOffset(first),
        last_byte=None if last is None else RecordingByteOffset(last),
    )


def test_the_bucket_keeps_only_ciphertext(storage: MotoStorage) -> None:
    call = location("businesses/b1/calls/c1.mp3")

    recordings(storage).store(call, RecordingAudio(content=AUDIO, media_type=MP3))

    stored = storage.raw_object(str(call.path))
    assert str(call.path) in storage.object_keys()
    assert stored.startswith(b"AWR1")
    assert AUDIO[5000:5064] not in stored
    whole = recordings(storage).read(call)
    assert whole is not None
    assert (whole.content, str(whole.media_type), int(whole.total_bytes)) == (
        AUDIO,
        "audio/mpeg",
        len(AUDIO),
    )


def test_a_seek_fetches_the_header_and_only_the_chunks_it_needs(
    storage: MotoStorage,
) -> None:
    call = location("businesses/b1/calls/c2.mp3")
    recordings(storage).store(call, RecordingAudio(content=AUDIO, media_type=MP3))
    transport = RecordingTransport()
    first = 2 * CHUNK_SIZE - 5

    part = recordings(storage, transport).read(call, span(first, first + 9))

    assert part is not None
    assert (part.content, int(part.first_byte)) == (AUDIO[first : first + 10], first)
    ranges = [request.headers["range"] for request in transport.requests]
    sealed = CHUNK_SIZE + 16
    assert ranges == [
        f"bytes=0-{HEADER_SIZE - 1}",
        f"bytes={HEADER_SIZE + sealed}-{HEADER_SIZE + 3 * sealed - 1}",
    ]
    for request in transport.requests:
        assert request.method == "GET"
        assert request.url.params["X-Amz-Expires"] == "60"
        assert "X-Amz-Signature" in request.url.params
        assert "authorization" not in request.headers


def test_open_and_suffix_ranges_and_ranges_outside(storage: MotoStorage) -> None:
    call = location("businesses/b1/calls/c3.mp3")
    long_audio = bytes(index % 239 for index in range(OPEN_RANGE_PART_BYTES + 1000))
    adapter = recordings(storage)
    adapter.store(call, RecordingAudio(content=long_audio, media_type=MP3))

    from_start = adapter.read(call, span(0))
    ending = adapter.read(call, RecordingByteRange(suffix_length=RecordingByteCount(5)))
    outside = adapter.read(call, span(len(long_audio)))

    assert from_start is not None and ending is not None and outside is not None
    # "The rest" is answered a few megabytes at a time.
    assert from_start.content == long_audio[:OPEN_RANGE_PART_BYTES]
    assert ending.content == long_audio[-5:]
    assert (outside.content, int(outside.total_bytes)) == (b"", len(long_audio))


def test_another_business_cannot_open_the_recording(storage: MotoStorage) -> None:
    owner = BusinessId()
    call = location("businesses/b2/calls/c4.mp3", owner)
    recordings(storage).store(call, RecordingAudio(content=AUDIO, media_type=MP3))

    with pytest.raises(ExternalServiceError, match="business's key"):
        recordings(storage).read(location(str(call.path)), span(0, 10))
    assert recordings(storage).read(call, span(0, 1)) is not None


def test_deleted_and_missing_recordings_read_as_none(storage: MotoStorage) -> None:
    call = location("businesses/b1/calls/c5.mp3")
    adapter = recordings(storage)
    adapter.store(call, RecordingAudio(content=b"short", media_type=MP3))

    adapter.delete(call)
    adapter.delete(call)

    assert adapter.read(call) is None
    assert str(call.path) not in storage.object_keys()


def test_an_empty_recording_round_trips(storage: MotoStorage) -> None:
    call = location("businesses/b1/calls/c6.mp3")
    adapter = recordings(storage)
    adapter.store(call, RecordingAudio(content=b"", media_type=MP3))

    whole = adapter.read(call)

    assert whole is not None and (whole.content, int(whole.total_bytes)) == (b"", 0)


@pytest.mark.parametrize("path", ["/absolute.mp3", "a/../../b.mp3", "", "a\x00b"])
def test_paths_that_are_no_object_keys_are_refused(
    storage: MotoStorage, path: str
) -> None:
    with pytest.raises(ValidationFailedError):
        recordings(storage).store(
            location(path), RecordingAudio(content=b"x", media_type=MP3)
        )


def test_an_unreachable_or_refusing_storage_is_an_external_error(
    storage: MotoStorage,
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(403, text="<Error>AccessDenied</Error>")

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    call = location("businesses/b1/calls/c7.mp3")
    for transport in (httpx.MockTransport(refuse), httpx.MockTransport(unreachable)):
        adapter = EncryptedObjectRecordingStorageAdapter(
            storage.client(transport), MASTER
        )
        with pytest.raises(ExternalServiceError) as failure:
            adapter.read(call)
        assert "X-Amz-Signature" not in str(failure.value)
        with pytest.raises(ExternalServiceError):
            adapter.store(call, RecordingAudio(content=b"x", media_type=MP3))
        with pytest.raises(ExternalServiceError):
            adapter.delete(call)
