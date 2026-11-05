"""
An S3-compatible object storage for tests: moto's server on localhost,
one bucket, and a transport that records what the client sent.
"""

import re
import socket
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

import httpx
from moto.server import ThreadedMotoServer
from typed_time_provider import Microseconds, WallClock

from app.clients.object_storage.s3_object_storage_client import S3ObjectStorageClient
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.constrained_strings import (
    ObjectStorageBucketName,
    ObjectStorageRegion,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

BUCKET: str = "workshop-recordings-eu"
REGION: str = "eu-central-1"
ACCESS_KEY_ID: str = "test-access-key"
SECRET_ACCESS_KEY: str = "test-secret-key"  # gitleaks:allow
CREATE_BUCKET_BODY: bytes = (
    b'<CreateBucketConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    b"<LocationConstraint>eu-central-1</LocationConstraint>"
    b"</CreateBucketConfiguration>"
)


@dataclass
class RecordingTransport(httpx.BaseTransport):
    """Sends for real and keeps every request."""

    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])
    inner: httpx.HTTPTransport = field(default_factory=httpx.HTTPTransport)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.inner.handle_request(request)


@dataclass(frozen=True)
class MotoStorage:
    """One bucket of its own (moto keeps one store for the whole process)."""

    endpoint_url: str
    bucket: str = field(default_factory=lambda: f"{BUCKET}-{uuid.uuid4().hex[:12]}")

    def connection(self) -> ObjectStorageConnection:
        return ObjectStorageConnection(
            endpoint_url=PublicBaseUrl(self.endpoint_url),
            region=ObjectStorageRegion(REGION),
            bucket=ObjectStorageBucketName(self.bucket),
            access_key_id=PlatformIdentifier(ACCESS_KEY_ID),
            secret_access_key=PlatformSecret(SECRET_ACCESS_KEY),
        )

    def client(
        self, transport: httpx.BaseTransport | None = None
    ) -> S3ObjectStorageClient:
        return S3ObjectStorageClient(
            connection=self.connection(),
            wall_clock=WallClock(preferred_time_unit_type=Microseconds),
            transport=transport,
        )

    def raw_object(self, key: str) -> bytes:
        """The object as the storage keeps it (what its operator could read)."""

        stored: bytes | None = self.client().get_object_range(
            RecordingStoragePath(key), 0, 1 << 30
        )
        assert stored is not None
        return stored

    def object_keys(self) -> list[str]:
        """The keys in the bucket (moto answers unsigned requests here)."""

        listed = httpx.get(f"{self.endpoint_url}/{self.bucket}?list-type=2", timeout=10)
        return sorted(re.findall(r"<Key>([^<]+)</Key>", listed.text))

    def create_bucket(self) -> None:
        created = httpx.put(
            f"{self.endpoint_url}/{self.bucket}",
            content=CREATE_BUCKET_BODY,
            timeout=10,
        )
        assert created.status_code == 200, created.text


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@contextmanager
def moto_storage() -> Generator[MotoStorage]:
    port = free_port()
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False)
    server.start()
    try:
        storage = MotoStorage(endpoint_url=f"http://127.0.0.1:{port}")
        storage.create_bucket()
        yield storage
    finally:
        server.stop()
