"""The backup bucket client against moto's S3 server and scripted replies."""

import os
from collections.abc import Callable, Generator
from pathlib import Path

import httpx
import pytest
from typed_time_provider import Microseconds, WallClock

from app.clients.object_storage.s3_backup_bucket_client import S3BackupBucketClient
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import LocalFilePath
from tests.compliance.moto_object_storage import (
    MotoStorage,
    RecordingTransport,
    moto_storage,
)

PART_SIZE: int = 5 * 1024 * 1024
PREFIX: BackupObjectPrefix = BackupObjectPrefix("workshop/")


def client_for(
    storage: MotoStorage, transport: httpx.BaseTransport | None = None
) -> S3BackupBucketClient:
    return S3BackupBucketClient(
        storage.connection(),
        WallClock(preferred_time_unit_type=Microseconds),
        transport=transport,
        part_size=PART_SIZE,
    )


def scripted(
    storage: MotoStorage, answer: Callable[[httpx.Request], httpx.Response]
) -> S3BackupBucketClient:
    return client_for(storage, httpx.MockTransport(answer))


def file_with(path: Path, content: bytes) -> LocalFilePath:
    path.write_bytes(content)
    return LocalFilePath(str(path))


@pytest.fixture(scope="module")
def storage() -> Generator[MotoStorage]:
    with moto_storage() as running:
        yield running


def test_small_and_multipart_uploads_round_trip(
    storage: MotoStorage, tmp_path: Path
) -> None:
    transport = RecordingTransport()
    client = client_for(storage, transport)
    small, big = os.urandom(1000), os.urandom(2 * PART_SIZE + 7)
    client.upload_file(
        BackupObjectKey("workshop/a.age"), file_with(tmp_path / "a", small)
    )
    client.upload_file(
        BackupObjectKey("workshop/b.age"), file_with(tmp_path / "b", big)
    )

    assert client.download_file(
        BackupObjectKey("workshop/b.age"), LocalFilePath(str(tmp_path / "b2"))
    )
    assert (tmp_path / "b2").read_bytes() == big
    assert client.download_file(
        BackupObjectKey("workshop/a.age"), LocalFilePath(str(tmp_path / "a2"))
    )
    assert (tmp_path / "a2").read_bytes() == small
    part_puts = [r for r in transport.requests if "partNumber" in str(r.url)]
    assert len(part_puts) == 3
    assert all("X-Amz-Signature=" in str(r.url) for r in transport.requests)
    assert all(r.headers.get("Authorization") is None for r in transport.requests)


def test_listing_sees_only_the_prefix_and_deleting_is_idempotent(
    storage: MotoStorage, tmp_path: Path
) -> None:
    client = client_for(storage)
    source = file_with(tmp_path / "x", b"x" * 10)
    for key in ("workshop/2026/10/one", "workshop/2026/10/two", "other/three"):
        client.upload_file(BackupObjectKey(key), source)

    listed = client.list_objects(BackupObjectPrefix("workshop/2026/"))
    client.delete_object(BackupObjectKey("workshop/2026/10/one"))
    client.delete_object(BackupObjectKey("workshop/2026/10/one"))

    assert [(str(item.key), int(item.size)) for item in listed] == [
        ("workshop/2026/10/one", 10),
        ("workshop/2026/10/two", 10),
    ]
    assert [
        str(item.key)
        for item in client.list_objects(BackupObjectPrefix("workshop/2026/"))
    ] == ["workshop/2026/10/two"]
    assert not client.download_file(
        BackupObjectKey("workshop/none"), LocalFilePath(str(tmp_path / "n"))
    )


def test_listing_follows_continuation_tokens(storage: MotoStorage) -> None:
    pages = {
        None: (
            "<ListBucketResult><Contents><Key>workshop/b</Key><Size>2</Size>"
            "</Contents><IsTruncated>true</IsTruncated>"
            "<NextContinuationToken>t&amp;1</NextContinuationToken>"
            "</ListBucketResult>"
        ),
        "t&1": (
            "<ListBucketResult><Contents><Key>workshop/a&amp;x</Key><Size>1</Size>"
            "</Contents><IsTruncated>false</IsTruncated></ListBucketResult>"
        ),
    }

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=pages[request.url.params.get("continuation-token")]
        )

    listed = scripted(storage, answer).list_objects(PREFIX)

    assert [str(item.key) for item in listed] == ["workshop/a&x", "workshop/b"]


def test_refusals_name_the_status_and_the_s3_code(
    storage: MotoStorage, tmp_path: Path
) -> None:
    denied = "<Error><Code>AccessDenied</Code><Message>no</Message></Error>"
    client = scripted(storage, lambda request: httpx.Response(403, text=denied))

    with pytest.raises(
        ExternalServiceError, match=r"refused a PUT \(HTTP 403, AccessDenied\)"
    ):
        client.upload_file(
            BackupObjectKey("workshop/x"), file_with(tmp_path / "x", b"1")
        )
    with pytest.raises(ExternalServiceError, match=r"refused a GET \(HTTP 403"):
        client.download_file(
            BackupObjectKey("workshop/x"), LocalFilePath(str(tmp_path / "y"))
        )
    with pytest.raises(ExternalServiceError, match="refused a LIST"):
        client.list_objects(PREFIX)
    with pytest.raises(ExternalServiceError, match="refused a DELETE"):
        client.delete_object(BackupObjectKey("workshop/x"))


def test_an_unreachable_bucket_is_an_external_error(storage: MotoStorage) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ExternalServiceError, match="could not be reached"):
        scripted(storage, fail).list_objects(PREFIX)
    with pytest.raises(ExternalServiceError, match="could not be reached"):
        scripted(storage, fail).download_file(
            BackupObjectKey("workshop/x"), LocalFilePath("/nonexistent/x")
        )


def test_a_failed_multipart_upload_is_aborted(
    storage: MotoStorage, tmp_path: Path
) -> None:
    seen: list[str] = []
    complete_error = "<Error><Code>InternalError</Code></Error>"

    def answer(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        seen.append(
            f"{request.method} {'uploads' if 'uploads' in params else ''}"
            f"{'part' if 'partNumber' in params else ''}"
        )
        if "uploads" in params:
            return httpx.Response(
                200,
                text="<InitiateMultipartUploadResult><UploadId>u-1</UploadId></InitiateMultipartUploadResult>",
            )
        if request.method == "POST":
            return httpx.Response(200, text=complete_error)
        return httpx.Response(
            200 if request.method == "PUT" else 204, headers={"ETag": '"e"'}
        )

    with pytest.raises(ExternalServiceError, match="refused a POST complete"):
        scripted(storage, answer).upload_file(
            BackupObjectKey("workshop/big"),
            file_with(tmp_path / "big", b"z" * (PART_SIZE + 1)),
        )

    assert seen == ["POST uploads", "PUT part", "PUT part", "POST ", "DELETE "]


def test_a_multipart_upload_without_an_id_fails(
    storage: MotoStorage, tmp_path: Path
) -> None:
    client = scripted(storage, lambda request: httpx.Response(200, text="<Nothing/>"))

    with pytest.raises(ExternalServiceError, match="no multipart upload id"):
        client.upload_file(
            BackupObjectKey("workshop/big"),
            file_with(tmp_path / "big", b"z" * (PART_SIZE + 1)),
        )
