from collections.abc import Iterator, Mapping
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import httpx
from typed_time_provider import Microseconds, WallClock

from app.clients.object_storage.s3_xml_replies import (
    ListingPage,
    build_completion,
    element_text,
    read_error_code,
    read_listing_page,
)
from app.contracts.backups import BackupBucketClientContract
from app.schemas.dto.backups import BackupObjectListing
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_integers import BackupArchiveSize
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.security.sigv4_presigning import presign_url

# A part of a multipart upload is held in memory: 32 MiB parts keep the
# cron instance's memory low and still allow archives of 320 GB.
DEFAULT_PART_SIZE: int = 32 * 1024 * 1024
STREAM_BLOCK_SIZE: int = 1024 * 1024
REQUEST_TIMEOUT: httpx.Timeout = httpx.Timeout(60.0, connect=15.0)
URL_LIFETIME_SECONDS: int = 15 * 60
MICROSECONDS_PER_SECOND: int = 1_000_000
OK_STATUSES: frozenset[int] = frozenset({200, 204})
NOT_FOUND: int = 404


class S3BackupBucketClient(BackupBucketClientContract):
    """
    The backup bucket in S3-compatible object storage (AWS S3 eu-central-1,
    Cloudflare R2 with the EU jurisdiction, Hetzner, Scaleway, MinIO),
    path-style, every request on a presigned URL (Signature Version 4).

    Files stream from and to disk, so an archive never sits in memory:
    a file up to one part goes up in one PUT, a bigger one as a multipart
    upload of 32 MiB parts (aborted on failure, so no orphaned parts are
    billed). Errors name the method, the status and S3's error code only;
    the URLs carry credentials and are never logged.
    """

    def __init__(
        self,
        connection: ObjectStorageConnection,
        wall_clock: WallClock[Microseconds],
        transport: httpx.BaseTransport | None = None,
        part_size: int = DEFAULT_PART_SIZE,
    ) -> None:
        self._connection: ObjectStorageConnection = connection
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._part_size: int = part_size
        self._http_client: httpx.Client = httpx.Client(
            timeout=REQUEST_TIMEOUT, transport=transport
        )

    def upload_file(self, key: BackupObjectKey, source: LocalFilePath) -> None:
        path = Path(str(source))
        size: int = path.stat().st_size
        if size <= self._part_size:
            with path.open("rb") as stream:
                response = self._send(
                    "PUT",
                    str(key),
                    content=read_blocks(stream, size),
                    headers={"Content-Length": str(size)},
                )
            self._require(response, "PUT")
            return

        self._upload_in_parts(str(key), path)

    def download_file(self, key: BackupObjectKey, target: LocalFilePath) -> bool:
        url: str = self._url("GET", str(key))
        try:
            with self._http_client.stream("GET", url) as response:
                if response.status_code == NOT_FOUND:
                    return False

                if response.status_code not in OK_STATUSES:
                    response.read()
                    self._require(response, "GET")

                with Path(str(target)).open("wb") as stream:
                    for block in response.iter_bytes(STREAM_BLOCK_SIZE):
                        stream.write(block)
        except httpx.HTTPError as error:
            raise unreachable(error) from error

        return True

    def list_objects(self, prefix: BackupObjectPrefix) -> list[BackupObjectListing]:
        listed: list[BackupObjectListing] = []
        token: str | None = None
        while True:
            parameters: dict[str, str] = {"list-type": "2", "prefix": str(prefix)}
            if token is not None:
                parameters["continuation-token"] = token

            response = self._send("GET", "", parameters=parameters)
            self._require(response, "LIST")
            page: ListingPage = read_listing_page(response.text)
            listed.extend(
                BackupObjectListing(
                    key=BackupObjectKey(item.key), size=BackupArchiveSize(item.size)
                )
                for item in page.objects
            )
            if page.next_token is None:
                return sorted(listed, key=lambda item: str(item.key))

            token = page.next_token

    def delete_object(self, key: BackupObjectKey) -> None:
        response = self._send("DELETE", str(key))
        if response.status_code != NOT_FOUND:
            self._require(response, "DELETE")

    def _upload_in_parts(self, key: str, path: Path) -> None:
        started = self._send("POST", key, parameters={"uploads": ""})
        self._require(started, "POST")
        upload_id: str | None = element_text(started.text, "UploadId")
        if upload_id is None:
            raise ExternalServiceError("The backup bucket gave no multipart upload id.")

        try:
            etags: list[str] = []
            with path.open("rb") as stream:
                while part := stream.read(self._part_size):
                    response = self._send(
                        "PUT",
                        key,
                        parameters={
                            "partNumber": str(len(etags) + 1),
                            "uploadId": upload_id,
                        },
                        content=part,
                    )
                    self._require(response, "PUT part")
                    etags.append(response.headers.get("ETag", ""))

            completed = self._send(
                "POST",
                key,
                parameters={"uploadId": upload_id},
                content=build_completion(etags),
            )
            # S3 may answer 200 and still report an error in the body.
            if read_error_code(completed.text) is not None:
                raise refusal(completed, "POST complete")
            self._require(completed, "POST complete")
        except Exception:
            self._abort(key, upload_id)
            raise

    def _abort(self, key: str, upload_id: str) -> None:
        # If even the abort fails, the bucket's lifecycle rule removes the
        # parts (docs/operations/backup-restore.md).
        with suppress(ExternalServiceError):
            self._send("DELETE", key, parameters={"uploadId": upload_id})

    def _send(
        self,
        method: str,
        key: str,
        parameters: Mapping[str, str] | None = None,
        content: bytes | Iterator[bytes] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            return self._http_client.request(
                method,
                self._url(method, key, parameters),
                content=content,
                headers=headers,
            )
        except httpx.HTTPError as error:
            raise unreachable(error) from error

    def _url(
        self, method: str, key: str, parameters: Mapping[str, str] | None = None
    ) -> str:
        return presign_url(
            self._connection,
            method,
            key,
            datetime.fromtimestamp(
                int(self._wall_clock.now_unix()) / MICROSECONDS_PER_SECOND, UTC
            ),
            URL_LIFETIME_SECONDS,
            parameters,
        )

    def _require(self, response: httpx.Response, action: str) -> None:
        if response.status_code not in OK_STATUSES:
            raise refusal(response, action)


def refusal(response: httpx.Response, action: str) -> ExternalServiceError:
    code: str | None = read_error_code(response.text)
    return ExternalServiceError(
        f"The backup bucket refused a {action} (HTTP {response.status_code}"
        + ("" if code is None else f", {code}")
        + ")."
    )


def read_blocks(stream: BinaryIO, size: int) -> Iterator[bytes]:
    """The file's bytes in 1 MiB blocks (the request body of one PUT)."""

    remaining: int = size
    while remaining > 0:
        block: bytes = stream.read(min(STREAM_BLOCK_SIZE, remaining))
        if not block:
            return

        remaining -= len(block)
        yield block


def unreachable(error: httpx.HTTPError) -> ExternalServiceError:
    return ExternalServiceError(
        f"The backup bucket could not be reached ({type(error).__name__})."
    )
