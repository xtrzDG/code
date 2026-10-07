"""
Archives are sealed in segments (AWX2) as they are read from their file:
every length comes back, segments cannot be cut off, reordered or changed,
and archives sealed whole before (AWX1) still open while they are kept.
"""

import io
import os
import struct

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.utilities.security.export_encryption import (
    HEADER_FORMAT,
    MAGIC,
    derive_archive_key,
    open_archive,
)
from app.utilities.security.export_stream_encryption import (
    STREAM_HEADER_SIZE,
    STREAM_MAGIC,
    TAG_SIZE,
    open_pieces,
    read_stream_header,
    seal_stream,
)
from app.utilities.security.recording_encryption import master_key_id

SECRET: PlatformSecret = PlatformSecret("export-stream-key-0000")
RING: dict[bytes, PlatformSecret] = {master_key_id(SECRET): SECRET}
BUSINESS: BusinessId = BusinessId()
PATH: ExportArchivePath = ExportArchivePath(f"business-exports/{BUSINESS}/x.zip")
SEGMENT: int = 7
STEP: int = SEGMENT + TAG_SIZE


def sealed(archive: bytes, segment_size: int = SEGMENT) -> bytes:
    return b"".join(
        seal_stream(
            SECRET,
            BUSINESS,
            PATH,
            io.BytesIO(archive),
            os.urandom(16),
            os.urandom(7),
            segment_size,
        )
    )


def open_sealed_archive(
    ring: dict[bytes, PlatformSecret],
    business: BusinessId,
    path: ExportArchivePath,
    sealed: bytes,
) -> bytes:
    """An archive opened as a download opens it: in segments, or whole (AWX1)."""

    if not sealed.startswith(STREAM_MAGIC):
        return open_archive(ring, business, path, sealed)

    opener = read_stream_header(ring, business, path, sealed)
    return b"".join(open_pieces(opener, [sealed], skip=STREAM_HEADER_SIZE))


def open_(data: bytes) -> bytes:
    return open_sealed_archive(RING, BUSINESS, PATH, data)


@pytest.mark.parametrize("length", [0, 1, SEGMENT - 1, SEGMENT, SEGMENT + 1, 50])
def test_every_length_comes_back(length: int) -> None:
    archive = bytes(range(length))

    data = sealed(archive)

    assert data.startswith(b"AWX2")
    assert archive == open_(data)
    segments = max(1, -(-length // SEGMENT))
    assert len(data) == STREAM_HEADER_SIZE + length + segments * TAG_SIZE


def test_cut_reordered_or_changed_segments_do_not_open() -> None:
    data = sealed(bytes(range(3 * SEGMENT + 3)))
    header, body = data[:STREAM_HEADER_SIZE], data[STREAM_HEADER_SIZE:]
    segments = [body[start : start + STEP] for start in range(0, len(body), STEP)]
    changed = bytearray(data)
    changed[-1] ^= 1

    variants = [
        header + b"".join(segments[:-1]),  # the last segment cut off
        header + b"".join(segments[:2]),  # cut at a segment boundary
        header + segments[1] + segments[0] + b"".join(segments[2:]),
        bytes(changed),
    ]

    for variant in variants:
        with pytest.raises(ExternalServiceError):
            open_(variant)


def test_another_business_or_path_or_a_dropped_key_does_not_open_it() -> None:
    data = sealed(b"PK archive of Nino")

    with pytest.raises(ExternalServiceError):
        open_sealed_archive(RING, BusinessId(), PATH, data)
    with pytest.raises(ExternalServiceError):
        open_sealed_archive(RING, BUSINESS, ExportArchivePath("other.zip"), data)
    with pytest.raises(ExternalServiceError, match="ENCRYPTION_KEYS"):
        open_sealed_archive({}, BUSINESS, PATH, data)
    with pytest.raises(ExternalServiceError):
        open_(data[: STREAM_HEADER_SIZE + 3])


def test_archives_sealed_whole_before_still_open() -> None:
    salt, nonce = os.urandom(16), os.urandom(12)
    header = struct.pack(HEADER_FORMAT, MAGIC, master_key_id(SECRET), salt, nonce)
    cipher = AESGCM(derive_archive_key(SECRET, BUSINESS, PATH, salt))
    old = header + cipher.encrypt(nonce, b"PK whole archive", header)

    assert open_(old) == b"PK whole archive"
    with pytest.raises(ExternalServiceError, match="not an encrypted archive"):
        open_(b"PK plain zip")
