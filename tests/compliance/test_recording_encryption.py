"""
Recordings at rest: sealed per business in 64 KiB chunks, any range opens
from its own chunks, and nothing opens under another key, business or path.
"""

import pytest

from app.schemas.dto.call_recordings import RecordingAudio, RecordingLocation
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.security.recording_encryption import (
    CHUNK_SIZE,
    HEADER_SIZE,
    TAG_SIZE,
    derive_business_key,
    open_chunks,
    read_header,
    seal_recording,
    sealed_chunk_span,
)

MASTER: PlatformSecret = PlatformSecret("recordings-master-secret-0123456789abcdef")
SALT: bytes = bytes(range(16))
AUDIO: bytes = bytes(index % 251 for index in range(2 * CHUNK_SIZE + 1234))
LOCATION: RecordingLocation = RecordingLocation(
    business_id=BusinessId(), path=RecordingStoragePath("businesses/b/calls/c.mp3")
)


def sealed(audio: bytes = AUDIO, location: RecordingLocation = LOCATION) -> bytes:
    return seal_recording(
        MASTER,
        location,
        RecordingAudio(content=audio, media_type=RecordingMediaType("audio/mpeg")),
        SALT,
    )


def open_range(
    stored: bytes,
    first_byte: int,
    last_byte: int,
    location: RecordingLocation = LOCATION,
    master: PlatformSecret = MASTER,
) -> bytes:
    header = read_header(stored[:HEADER_SIZE])
    first_chunk, stored_first, stored_last = sealed_chunk_span(
        header, first_byte, last_byte
    )
    plaintext = open_chunks(
        master, location, header, first_chunk, stored[stored_first : stored_last + 1]
    )
    start = first_byte - first_chunk * header.chunk_size
    return plaintext[start : start + last_byte - first_byte + 1]


def test_a_sealed_recording_hides_the_audio_and_keeps_its_shape() -> None:
    stored = sealed()
    header = read_header(stored[:HEADER_SIZE])

    assert stored.startswith(b"AWR1")
    assert AUDIO[1000:1064] not in stored
    assert len(stored) == HEADER_SIZE + len(AUDIO) + 3 * TAG_SIZE
    assert (header.plaintext_length, header.chunk_count) == (len(AUDIO), 3)
    assert str(header.media_type) == "audio/mpeg"


@pytest.mark.parametrize(
    ("first_byte", "last_byte"),
    [
        (0, 1),
        (0, len(AUDIO) - 1),
        (CHUNK_SIZE - 10, CHUNK_SIZE + 10),
        (2 * CHUNK_SIZE, len(AUDIO) - 1),
        (len(AUDIO) - 1, len(AUDIO) - 1),
    ],
)
def test_any_range_opens_from_its_own_chunks(first_byte: int, last_byte: int) -> None:
    assert (
        open_range(sealed(), first_byte, last_byte) == AUDIO[first_byte : last_byte + 1]
    )


def test_an_empty_recording_is_one_empty_chunk() -> None:
    stored = sealed(b"")
    header = read_header(stored[:HEADER_SIZE])

    assert (header.plaintext_length, header.chunk_count) == (0, 1)
    assert len(stored) == HEADER_SIZE + TAG_SIZE


def test_each_business_has_a_key_of_its_own() -> None:
    other = RecordingLocation(business_id=BusinessId(), path=LOCATION.path)

    assert derive_business_key(MASTER, LOCATION) != derive_business_key(MASTER, other)
    with pytest.raises(ExternalServiceError, match="business's key"):
        open_range(sealed(), 0, 10, location=other)


def test_a_recording_copied_to_another_path_does_not_open() -> None:
    moved = RecordingLocation(
        business_id=LOCATION.business_id,
        path=RecordingStoragePath("businesses/b/calls/other.mp3"),
    )

    with pytest.raises(ExternalServiceError):
        open_range(sealed(), 0, 10, location=moved)


def test_another_master_key_is_named_as_such() -> None:
    with pytest.raises(ExternalServiceError, match="another ENCRYPTION_KEY"):
        open_range(sealed(), 0, 10, master=PlatformSecret("x" * 40))


@pytest.mark.parametrize("position", [HEADER_SIZE + 5, HEADER_SIZE - 70])
def test_a_changed_byte_or_header_is_refused(position: int) -> None:
    stored = bytearray(sealed())
    stored[position] ^= 0x01

    with pytest.raises(ExternalServiceError):
        open_range(bytes(stored), 0, 10)


def test_a_cut_recording_is_refused() -> None:
    # The second chunk passed off as the last one fails its "last" mark.
    stored = sealed()
    header = read_header(stored[:HEADER_SIZE])
    sealed_size = CHUNK_SIZE + TAG_SIZE
    second = stored[HEADER_SIZE + sealed_size : HEADER_SIZE + 2 * sealed_size]

    with pytest.raises(ExternalServiceError):
        open_chunks(MASTER, LOCATION, header, header.chunk_count - 1, second)


def test_something_else_is_not_read_as_a_recording() -> None:
    with pytest.raises(ExternalServiceError, match="not an encrypted recording"):
        read_header(b"ID3" + b"\x00" * HEADER_SIZE)
