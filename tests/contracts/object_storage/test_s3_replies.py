"""
S3 as the backup bucket and the recordings/exports store use it: the
documented replies (a listing in two pages, a multipart upload started and
completed) match S3's service model and are read; every request the clients
sign uses only the parameters and headers the operation defines, and the
completion body has no element S3 does not know; S3's documented errors
become refusals naming S3's code, an error inside a 200 included.
"""

from typing import Any

import httpx
import pytest
from typed_time_provider import Microseconds, WallClock

from app.clients.object_storage.s3_backup_bucket_client import S3BackupBucketClient
from app.clients.object_storage.s3_object_storage_client import S3ObjectStorageClient
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_strings import BackupObjectPrefix
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.constrained_strings import (
    ObjectStorageBucketName,
    ObjectStorageRegion,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.contracts.contract_files import load_json_fixture, read_fixture_bytes
from tests.contracts.object_storage.s3_model import (
    assert_xml_matches,
    request_problems,
)

CONNECTION = ObjectStorageConnection(
    endpoint_url=PublicBaseUrl("https://s3.eu-central-1.amazonaws.com"),
    region=ObjectStorageRegion("eu-central-1"),
    bucket=ObjectStorageBucketName("workshop-backups"),
    access_key_id=PlatformIdentifier("test-access-key-0000"),
    secret_access_key=PlatformSecret("test-secret-access-key-0000"),
)
EXPORT_KEY = RecordingStoragePath("exports/business-0000/export.zip")
ERROR_CASES: list[dict[str, Any]] = load_json_fixture(
    "object_storage", "s3_errors.json"
)["cases"]


def reply(name: str) -> bytes:
    return read_fixture_bytes("object_storage", name)


class ScriptedBucket:
    """Answers requests in order and keeps them."""

    def __init__(self, answers: list[httpx.Response]) -> None:
        self.answers: list[httpx.Response] = answers
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.answers.pop(0)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)


def backup_bucket(bucket: ScriptedBucket) -> S3BackupBucketClient:
    return S3BackupBucketClient(
        CONNECTION,
        WallClock(preferred_time_unit_type=Microseconds),
        transport=bucket.transport(),
    )


def object_storage(bucket: ScriptedBucket) -> S3ObjectStorageClient:
    return S3ObjectStorageClient(
        CONNECTION,
        WallClock(preferred_time_unit_type=Microseconds),
        transport=bucket.transport(),
    )


def assert_requests_match(bucket: ScriptedBucket, operations: list[str]) -> None:
    assert len(bucket.requests) == len(operations)
    for request, operation_name in zip(bucket.requests, operations, strict=True):
        problems: list[str] = request_problems(request, operation_name)
        assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    ("name", "root", "shape_name"),
    [
        ("list_objects_v2_page_1.xml", "ListBucketResult", "ListObjectsV2Output"),
        ("list_objects_v2_page_2.xml", "ListBucketResult", "ListObjectsV2Output"),
        (
            "create_multipart_upload.xml",
            "InitiateMultipartUploadResult",
            "CreateMultipartUploadOutput",
        ),
        (
            "complete_multipart_upload.xml",
            "CompleteMultipartUploadResult",
            "CompleteMultipartUploadOutput",
        ),
    ],
)
def test_documented_replies_match_the_service_model(
    name: str, root: str, shape_name: str
) -> None:
    assert_xml_matches(reply(name), root, shape_name)


def test_listing_pages_are_read_and_continued() -> None:
    bucket = ScriptedBucket(
        [
            httpx.Response(200, content=reply("list_objects_v2_page_1.xml")),
            httpx.Response(200, content=reply("list_objects_v2_page_2.xml")),
        ]
    )

    listed = backup_bucket(bucket).list_objects(BackupObjectPrefix("workshop/"))

    assert [(str(item.key), int(item.size)) for item in listed] == [
        ("workshop/daily/2026-10-04T02-00-00Z.dump.age", 18_342_011),
        ("workshop/daily/2026-10-05T02-00-00Z.dump.age", 18_420_736),
        ("workshop/monthly/2026-10-01T02-00-00Z.dump.age", 17_998_112),
    ]
    assert_requests_match(bucket, ["ListObjectsV2", "ListObjectsV2"])
    first, second = bucket.requests
    assert "continuation-token" not in first.url.params
    assert second.url.params["continuation-token"] == "test/continuation+token=0000"


def test_multipart_upload_sends_what_the_model_defines() -> None:
    bucket = ScriptedBucket(
        [
            httpx.Response(200, content=reply("create_multipart_upload.xml")),
            httpx.Response(200, headers={"ETag": '"part-1-etag-0000"'}),
            httpx.Response(200, headers={"ETag": '"part-2-etag-0000"'}),
            httpx.Response(200, content=reply("complete_multipart_upload.xml")),
        ]
    )

    object_storage(bucket).put_object_parts(EXPORT_KEY, [b"PK\x03\x04", b"rest"])

    assert_requests_match(
        bucket,
        [
            "CreateMultipartUpload",
            "UploadPart",
            "UploadPart",
            "CompleteMultipartUpload",
        ],
    )
    completion: httpx.Request = bucket.requests[-1]
    assert completion.url.params["uploadId"] == "test-upload-id-0000"
    assert_xml_matches(
        completion.content, "CompleteMultipartUpload", "CompletedMultipartUpload"
    )
    assert b"<ETag>&quot;part-2-etag-0000&quot;</ETag>" in completion.content


def test_single_put_and_ranged_get_send_what_the_model_defines() -> None:
    bucket = ScriptedBucket(
        [httpx.Response(200), httpx.Response(206, content=b"ID3\x04")]
    )
    storage = object_storage(bucket)

    storage.put_object(EXPORT_KEY, b"ID3\x04\x00")
    assert storage.get_object_range(EXPORT_KEY, 0, 3) == b"ID3\x04"

    assert_requests_match(bucket, ["PutObject", "GetObject"])


def test_an_error_inside_a_200_completion_aborts_the_upload() -> None:
    internal_error: dict[str, Any] = ERROR_CASES[-1]
    bucket = ScriptedBucket(
        [
            httpx.Response(200, content=reply("create_multipart_upload.xml")),
            httpx.Response(200, headers={"ETag": '"part-1-etag-0000"'}),
            httpx.Response(200, headers={"ETag": '"part-2-etag-0000"'}),
            httpx.Response(internal_error["status"], text=internal_error["xml"]),
            httpx.Response(204),
        ]
    )

    with pytest.raises(ExternalServiceError):
        object_storage(bucket).put_object_parts(EXPORT_KEY, [b"one", b"two"])

    assert_requests_match(
        bucket,
        [
            "CreateMultipartUpload",
            "UploadPart",
            "UploadPart",
            "CompleteMultipartUpload",
            "AbortMultipartUpload",
        ],
    )


@pytest.mark.parametrize(
    "case",
    [case for case in ERROR_CASES if case["status"] != 200],
    ids=lambda case: case["code"],
)
def test_documented_errors_name_s3s_code(case: dict[str, Any]) -> None:
    bucket = ScriptedBucket([httpx.Response(case["status"], text=case["xml"])])

    with pytest.raises(ExternalServiceError) as raised:
        backup_bucket(bucket).list_objects(BackupObjectPrefix("workshop/"))

    assert str(raised.value) == (
        f"The backup bucket refused a LIST (HTTP {case['status']}, {case['code']})."
    )
