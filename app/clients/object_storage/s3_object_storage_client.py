from datetime import UTC, datetime

import httpx
from typed_time_provider import Microseconds, WallClock

from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.utilities.security.sigv4_presigning import presign_url

REQUEST_TIMEOUT_SECONDS: float = 30.0
# A presigned URL is made for one request and used at once.
URL_LIFETIME_SECONDS: int = 60
MICROSECONDS_PER_SECOND: int = 1_000_000
STORED_CONTENT_TYPE: str = "application/octet-stream"
OK_STATUSES: frozenset[int] = frozenset({200, 204})
RANGE_STATUSES: frozenset[int] = frozenset({200, 206})
NOT_FOUND: int = 404
RANGE_NOT_SATISFIABLE: int = 416


class S3ObjectStorageClient(ObjectStorageClientContract):
    """
    One bucket of S3-compatible object storage in the EU (AWS S3
    eu-central-1, Cloudflare R2 with the EU jurisdiction, Hetzner, Scaleway,
    MinIO), addressed path-style.

    Every request goes to a presigned URL (Signature Version 4 in the query,
    valid for a minute): a byte range of a recording is a GET of its
    presigned URL with a `Range` header, so only the bytes a player asks for
    leave the bucket. The URLs carry credentials for one request and are
    never logged or shown; errors name the method and the status only.
    """

    def __init__(
        self,
        connection: ObjectStorageConnection,
        wall_clock: WallClock[Microseconds],
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._connection: ObjectStorageConnection = connection
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._http_client: httpx.Client = httpx.Client(
            timeout=REQUEST_TIMEOUT_SECONDS, transport=transport
        )

    def put_object(self, key: RecordingStoragePath, body: bytes) -> None:
        response: httpx.Response = self._request(
            "PUT", key, content=body, headers={"Content-Type": STORED_CONTENT_TYPE}
        )
        self._require(response, OK_STATUSES, "PUT")

    def get_object_range(
        self,
        key: RecordingStoragePath,
        first_byte: int,
        last_byte: int,
    ) -> bytes | None:
        response: httpx.Response = self._request(
            "GET", key, headers={"Range": f"bytes={first_byte}-{last_byte}"}
        )
        if response.status_code == NOT_FOUND:
            return None

        if response.status_code == RANGE_NOT_SATISFIABLE:
            return b""

        self._require(response, RANGE_STATUSES, "GET")
        if response.status_code == 200:
            # A store that ignored the range sent the whole object.
            return response.content[first_byte : last_byte + 1]

        return response.content

    def delete_object(self, key: RecordingStoragePath) -> None:
        response: httpx.Response = self._request("DELETE", key)
        if response.status_code != NOT_FOUND:
            self._require(response, OK_STATUSES, "DELETE")

    def _request(
        self,
        method: str,
        key: RecordingStoragePath,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url: str = presign_url(
            self._connection,
            method,
            str(key),
            datetime.fromtimestamp(
                int(self._wall_clock.now_unix()) / MICROSECONDS_PER_SECOND, UTC
            ),
            URL_LIFETIME_SECONDS,
        )
        try:
            return self._http_client.request(
                method, url, content=content, headers=headers
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"The recordings object storage could not be reached "
                f"({type(error).__name__})."
            ) from error

    def _require(
        self,
        response: httpx.Response,
        expected: frozenset[int],
        method: str,
    ) -> None:
        if response.status_code not in expected:
            raise ExternalServiceError(
                f"The recordings object storage refused a {method} "
                f"(HTTP {response.status_code})."
            )
