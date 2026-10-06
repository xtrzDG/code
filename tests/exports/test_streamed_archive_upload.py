"""
An export archive goes from its file to S3-compatible object storage
(moto's server) sealed in segments and uploaded in parts held one at a
time: a big archive is a multipart upload, a small one a single PUT, and a
failed part aborts the upload so no half object is left.
"""

import io
import os
from collections.abc import Generator

import httpx
import pytest

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    EncryptedObjectExportArchiveStorageAdapter,
    upload_parts,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.strings import ExportArchivePath
from tests.compliance.moto_object_storage import (
    MotoStorage,
    RecordingTransport,
    moto_storage,
)

KEY: PlatformSecret = PlatformSecret("export-upload-key-0000")
BUSINESS: BusinessId = BusinessId()
MEBIBYTE: int = 1024 * 1024


@pytest.fixture(scope="module")
def storage() -> Generator[MotoStorage]:
    with moto_storage() as running:
        yield running


def path_of(name: str) -> ExportArchivePath:
    return ExportArchivePath(f"business-exports/{BUSINESS}/{name}.zip")


def test_a_big_archive_goes_up_in_parts(storage: MotoStorage) -> None:
    transport = RecordingTransport()
    adapter = EncryptedObjectExportArchiveStorageAdapter(storage.client(transport), KEY)
    archive = os.urandom(20 * MEBIBYTE + 123)
    path = path_of("big")

    adapter.store(BUSINESS, path, io.BytesIO(archive))

    requests = [(request.method, request.url.params) for request in transport.requests]
    assert [method for method, _ in requests] == ["POST", "PUT", "PUT", "PUT", "POST"]
    assert "uploads" in requests[0][1]
    assert [params["partNumber"] for _, params in requests[1:4]] == ["1", "2", "3"]
    assert "uploadId" in requests[-1][1]
    assert adapter.read(BUSINESS, path) == archive
    raw = storage.raw_object(str(path))
    assert raw.startswith(b"AWX2") and archive[:64] not in raw


def test_a_small_archive_is_one_put(storage: MotoStorage) -> None:
    transport = RecordingTransport()
    adapter = EncryptedObjectExportArchiveStorageAdapter(storage.client(transport), KEY)

    adapter.store(BUSINESS, path_of("small"), io.BytesIO(b"PK tiny"))

    assert [request.method for request in transport.requests] == ["PUT"]
    assert adapter.read(BUSINESS, path_of("small")) == b"PK tiny"


class FailingSecondPart(RecordingTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.method == "PUT" and request.url.params.get("partNumber") == "2":
            self.requests.append(request)
            return httpx.Response(500, text="<Error><Code>InternalError</Code></Error>")
        return super().handle_request(request)


def test_a_failed_part_aborts_the_upload(storage: MotoStorage) -> None:
    transport = FailingSecondPart()
    adapter = EncryptedObjectExportArchiveStorageAdapter(storage.client(transport), KEY)
    path = path_of("broken")

    with pytest.raises(ExternalServiceError, match="PUT part"):
        adapter.store(BUSINESS, path, io.BytesIO(os.urandom(17 * MEBIBYTE)))

    assert transport.requests[-1].method == "DELETE"
    assert "uploadId" in transport.requests[-1].url.params
    assert str(path) not in storage.object_keys()


def test_segments_are_regrouped_into_parts_of_one_size() -> None:
    parts = list(upload_parts([b"abc", b"defg", b"h", b""], 3))

    assert parts == [b"abc", b"def", b"gh"]
    assert list(upload_parts([], 3)) == [b""]
    assert list(upload_parts([b"abcdef"], 3)) == [b"abc", b"def"]
