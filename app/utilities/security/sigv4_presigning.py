"""
Presigned URLs of S3-compatible object storage (AWS Signature Version 4,
query-string authentication).

A presigned URL carries its signature in the query: whoever holds it may
make that one request (method, bucket, key) until it expires, with any
`Range` header (only `host` is signed). The payload is not signed
(`UNSIGNED-PAYLOAD`): TLS protects it on the way, and the recordings are
sealed with AES-GCM before they leave the API anyway.
"""

import hashlib
import hmac
from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

from app.schemas.dto.object_storage import ObjectStorageConnection

ALGORITHM: str = "AWS4-HMAC-SHA256"
SERVICE: str = "s3"
UNSIGNED_PAYLOAD: str = "UNSIGNED-PAYLOAD"
# RFC 3986 unreserved characters stay as they are; everything else is
# percent-encoded, as SigV4 requires.
UNRESERVED: str = "-_.~"


def presign_url(
    connection: ObjectStorageConnection,
    method: str,
    object_key: str,
    signed_at: datetime,
    expires_seconds: int,
    parameters: Mapping[str, str] | None = None,
) -> str:
    """
    The presigned URL of one request on one object (path-style), or on the
    bucket itself when `object_key` is empty (a listing). `parameters` are
    the request's own query parameters (`uploadId`, `list-type`, ...); they
    are signed with the rest.
    """

    endpoint = urlsplit(str(connection.endpoint_url).rstrip("/"))
    canonical_path: str = endpoint.path + "/" + encode_segment(str(connection.bucket))
    if object_key != "":
        canonical_path += "/" + "/".join(
            encode_segment(segment) for segment in object_key.split("/")
        )
    query: str = presigned_query(
        method=method,
        host=endpoint.netloc,
        canonical_path=canonical_path,
        connection=connection,
        signed_at=signed_at,
        expires_seconds=expires_seconds,
        parameters=parameters,
    )
    return f"{endpoint.scheme}://{endpoint.netloc}{canonical_path}?{query}"


def presigned_query(
    method: str,
    host: str,
    canonical_path: str,
    connection: ObjectStorageConnection,
    signed_at: datetime,
    expires_seconds: int,
    parameters: Mapping[str, str] | None = None,
) -> str:
    """The query string of a presigned request, its signature last."""

    moment: datetime = signed_at.astimezone(UTC)
    day: str = moment.strftime("%Y%m%d")
    amz_date: str = moment.strftime("%Y%m%dT%H%M%SZ")
    scope: str = f"{day}/{connection.region}/{SERVICE}/aws4_request"
    query: dict[str, str] = {
        "X-Amz-Algorithm": ALGORITHM,
        "X-Amz-Credential": f"{connection.access_key_id}/{scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_seconds),
        "X-Amz-SignedHeaders": "host",
        **({} if parameters is None else parameters),
    }
    canonical_query: str = "&".join(
        f"{encode_segment(key)}={encode_segment(value)}"
        for key, value in sorted(query.items())
    )
    canonical_request: str = "\n".join(
        [
            method,
            canonical_path,
            canonical_query,
            f"host:{host}\n",
            "host",
            UNSIGNED_PAYLOAD,
        ]
    )
    string_to_sign: str = "\n".join(
        [ALGORITHM, amz_date, scope, sha256_hex(canonical_request.encode("utf-8"))]
    )
    signature: str = hmac.new(
        signing_key(str(connection.secret_access_key), day, str(connection.region)),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{canonical_query}&X-Amz-Signature={signature}"


def signing_key(secret_access_key: str, day: str, region: str) -> bytes:
    key: bytes = hmac_sha256(f"AWS4{secret_access_key}".encode(), day)
    for part in (region, SERVICE, "aws4_request"):
        key = hmac_sha256(key, part)

    return key


def hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def encode_segment(text: str) -> str:
    return quote(text, safe=UNRESERVED)
