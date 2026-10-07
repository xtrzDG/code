"""
A download reads its sealed archive from S3-compatible storage (moto's
server) in ranges as the response asks for pieces, never whole: the first
range is read before the response starts (a missing or unopenable archive
is known then), the others one at a time. Every length comes back, also at
the edges of a range, and a segment changed in the bucket stops the
download at that segment.
"""

import io
import os
from collections.abc import Generator, Iterable

import pytest

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    READ_WINDOW_BYTES,
    EncryptedObjectExportArchiveStorageAdapter,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.utilities.security.export_stream_encryption import (
    SEGMENT_SIZE,
    STREAM_HEADER_SIZE,
    TAG_SIZE,
)
from tests.compliance.moto_object_storage import (
    MotoStorage,
    RecordingTransport,
    moto_storage,
)
from tests.exports.archive_reading import read_whole
from tests.security.previous_key_fakes import DictObjectStorage

KEY: PlatformSecret = PlatformSecret("export-download-key-0000")
BUSINESS: BusinessId = BusinessId()
PATH: ExportArchivePath = ExportArchivePath(f"business-exports/{BUSINESS}/a.zip")
MEBIBYTE: int = 1024 * 1024
# An archive whose sealed form fills exactly one range.
ONE_RANGE: int = READ_WINDOW_BYTES - STREAM_HEADER_SIZE - 4 * TAG_SIZE


@pytest.fixture(scope="module")
def storage() -> Generator[MotoStorage]:
    with moto_storage() as running:
        yield running


def range_reads(transport: RecordingTransport) -> list[str]:
    return [
        request.headers["range"]
        for request in transport.requests
        if request.method == "GET"
    ]


def test_the_archive_is_read_in_ranges_as_the_pieces_are_asked_for(
    storage: MotoStorage,
) -> None:
    transport = RecordingTransport()
    adapter = EncryptedObjectExportArchiveStorageAdapter(storage.client(transport), KEY)
    archive = os.urandom(10 * MEBIBYTE + 7)
    adapter.store(BUSINESS, PATH, io.BytesIO(archive))
    transport.requests.clear()

    pieces = adapter.stream(BUSINESS, PATH)
    assert pieces is not None
    before_the_first_piece = range_reads(transport)
    received = iter(pieces)
    first = next(received)
    rest = b"".join(received)

    assert before_the_first_piece == [f"bytes=0-{READ_WINDOW_BYTES - 1}"]
    assert first + rest == archive
    assert len(first) == SEGMENT_SIZE
    assert range_reads(transport) == [
        f"bytes={start}-{start + READ_WINDOW_BYTES - 1}"
        for start in range(0, 3 * READ_WINDOW_BYTES, READ_WINDOW_BYTES)
    ]


def test_a_missing_archive_is_none(storage: MotoStorage) -> None:
    adapter = EncryptedObjectExportArchiveStorageAdapter(storage.client(), KEY)

    assert (
        adapter.stream(BUSINESS, ExportArchivePath("business-exports/gone.zip")) is None
    )


@pytest.mark.parametrize(
    "length",
    [0, 1, SEGMENT_SIZE, ONE_RANGE - 1, ONE_RANGE, ONE_RANGE + 1, 9 * MEBIBYTE],
)
def test_every_length_comes_back(length: int) -> None:
    adapter = EncryptedObjectExportArchiveStorageAdapter(DictObjectStorage(), KEY)
    archive = os.urandom(length)

    adapter.store(BUSINESS, PATH, io.BytesIO(archive))

    assert read_whole(adapter, BUSINESS, PATH) == archive


def test_a_changed_segment_stops_the_download_at_that_segment() -> None:
    objects = DictObjectStorage()
    adapter = EncryptedObjectExportArchiveStorageAdapter(objects, KEY)
    adapter.store(BUSINESS, PATH, io.BytesIO(os.urandom(6 * MEBIBYTE)))
    sealed = bytearray(objects.objects[str(PATH)])
    sealed[STREAM_HEADER_SIZE + 4 * (SEGMENT_SIZE + TAG_SIZE) + 5] ^= 1
    objects.objects[str(PATH)] = bytes(sealed)
    received: list[bytes] = []

    pieces: Iterable[bytes] | None = adapter.stream(BUSINESS, PATH)
    assert pieces is not None
    with pytest.raises(ExternalServiceError, match="does not open"):
        for piece in pieces:
            received.append(piece)

    assert len(received) == 4


def test_an_archive_of_a_key_no_longer_kept_fails_before_the_first_piece() -> None:
    objects = DictObjectStorage()
    EncryptedObjectExportArchiveStorageAdapter(objects, KEY).store(
        BUSINESS, PATH, io.BytesIO(b"PK zip")
    )
    rotated = EncryptedObjectExportArchiveStorageAdapter(
        objects, PlatformSecret("another-export-key-0000")
    )

    with pytest.raises(ExternalServiceError, match="ENCRYPTION_KEYS"):
        rotated.stream(BUSINESS, PATH)
