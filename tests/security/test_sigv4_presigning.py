"""Presigned URLs of S3-compatible object storage (AWS Signature Version 4)."""

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_strings import (
    ObjectStorageBucketName,
    ObjectStorageRegion,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.security.sigv4_presigning import presign_url, presigned_query


def connection(endpoint: str, region: str = "us-east-1") -> ObjectStorageConnection:
    return ObjectStorageConnection(
        endpoint_url=PublicBaseUrl(endpoint),
        region=ObjectStorageRegion(region),
        bucket=ObjectStorageBucketName("examplebucket"),
        access_key_id=PlatformIdentifier("AKIAIOSFODNN7EXAMPLE"),
        secret_access_key=PlatformSecret("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
    )


def test_the_signature_matches_the_aws_documentation_example() -> None:
    # "Authenticating Requests: Using Query Parameters" in the Amazon S3 API
    # reference: GET /test.txt of examplebucket, 24 May 2013, valid a day.
    query = presigned_query(
        method="GET",
        host="examplebucket.s3.amazonaws.com",
        canonical_path="/test.txt",
        connection=connection("https://examplebucket.s3.amazonaws.com"),
        signed_at=datetime(2013, 5, 24, tzinfo=UTC),
        expires_seconds=86400,
    )

    assert query == (
        "X-Amz-Algorithm=AWS4-HMAC-SHA256"
        "&X-Amz-Credential=AKIAIOSFODNN7EXAMPLE%2F20130524%2Fus-east-1%2Fs3%2Faws4_request"
        "&X-Amz-Date=20130524T000000Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=host"
        "&X-Amz-Signature="
        "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"
    )


def test_urls_are_path_style_with_encoded_keys_and_the_endpoint_port() -> None:
    url = presign_url(
        connection("http://127.0.0.1:9000/", region="eu-central-1"),
        "PUT",
        "businesses/biz 1/calls/зв.mp3",
        datetime(2026, 10, 2, 12, 30, tzinfo=UTC),
        60,
    )

    parts = urlsplit(url)
    query = parse_qs(parts.query)
    assert (parts.scheme, parts.netloc) == ("http", "127.0.0.1:9000")
    assert parts.path == ("/examplebucket/businesses/biz%201/calls/%D0%B7%D0%B2.mp3")
    assert query["X-Amz-Credential"] == [
        "AKIAIOSFODNN7EXAMPLE/20261002/eu-central-1/s3/aws4_request"
    ]
    assert query["X-Amz-Expires"] == ["60"]
    assert len(query["X-Amz-Signature"][0]) == 64
    # Each method signs differently: a GET URL cannot delete.
    assert url != presign_url(
        connection("http://127.0.0.1:9000/", region="eu-central-1"),
        "DELETE",
        "businesses/biz 1/calls/зв.mp3",
        datetime(2026, 10, 2, 12, 30, tzinfo=UTC),
        60,
    )
