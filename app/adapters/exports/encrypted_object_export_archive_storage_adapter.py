import os
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import BinaryIO

from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.utilities.security.export_encryption import SALT_SIZE
from app.utilities.security.export_stream_encryption import (
    NONCE_PREFIX_SIZE,
    open_sealed_archive,
    seal_stream,
)
from app.utilities.security.recording_encryption import master_key_id

# Larger than any archive: a read asks for the whole object (the client
# returns fewer bytes at its end).
WHOLE_OBJECT_LAST_BYTE: int = 2**40
# Sealed segments go up in parts of 8 MiB (S3 wants at least 5 MiB a part):
# one part and one segment in memory at a time.
UPLOAD_PART_SIZE: int = 8 * 1024 * 1024


class EncryptedObjectExportArchiveStorageAdapter(ExportArchiveStorageContract):
    """
    Full business exports in the recordings' S3-compatible EU bucket (keys
    under `business-exports/`), each sealed with its business's key
    (`export_encryption`), so the bucket only ever sees ciphertext. New
    archives are sealed under the current key of the ring; an archive's
    header names its key, so one sealed before a rotation still opens while
    that key is in the ring (archives live a day). An archive is sealed in
    segments as it is read from its file and uploaded in parts
    (`export_stream_encryption`), never whole in memory.
    """

    def __init__(
        self,
        client: ObjectStorageClientContract,
        master_secret: PlatformSecret,
        random_bytes: Callable[[int], bytes] = os.urandom,
        previous_master_secrets: Sequence[PlatformSecret] = (),
    ) -> None:
        self._client: ObjectStorageClientContract = client
        self._master_secret: PlatformSecret = master_secret
        self._secrets_by_key_id: dict[bytes, PlatformSecret] = {
            master_key_id(secret): secret
            for secret in reversed([master_secret, *previous_master_secrets])
        }
        self._random_bytes: Callable[[int], bytes] = random_bytes

    def store(
        self, business_id: BusinessId, path: ExportArchivePath, archive: BinaryIO
    ) -> None:
        key: RecordingStoragePath = object_key(path)
        archive.seek(0)
        segments: Iterator[bytes] = seal_stream(
            self._master_secret,
            business_id,
            path,
            archive,
            self._random_bytes(SALT_SIZE),
            self._random_bytes(NONCE_PREFIX_SIZE),
        )
        self._client.put_object_parts(key, upload_parts(segments, UPLOAD_PART_SIZE))

    def read(self, business_id: BusinessId, path: ExportArchivePath) -> bytes | None:
        sealed: bytes | None = self._client.get_object_range(
            object_key(path), 0, WHOLE_OBJECT_LAST_BYTE
        )
        if sealed is None:
            return None

        return open_sealed_archive(self._secrets_by_key_id, business_id, path, sealed)

    def delete(self, business_id: BusinessId, path: ExportArchivePath) -> None:
        self._client.delete_object(object_key(path))


def object_key(path: ExportArchivePath) -> RecordingStoragePath:
    """
    The bucket key of an archive (the bucket is the recordings' one, so its
    keys are recording storage paths); refuses an empty, absolute or `..`
    path.
    """

    text: str = str(path)
    if text == "" or text.startswith("/") or "\x00" in text or ".." in text.split("/"):
        raise ValidationFailedError(f"Invalid export path {text!r}.")

    return RecordingStoragePath(text)


def upload_parts(segments: Iterable[bytes], part_size: int) -> Iterator[bytes]:
    """
    The sealed segments regrouped into upload parts of `part_size` bytes
    (the last one shorter); at least one part, so an upload always happens.
    """

    buffer = bytearray()
    has_yielded: bool = False
    for segment in segments:
        buffer += segment
        while len(buffer) >= part_size:
            yield bytes(buffer[:part_size])
            del buffer[:part_size]
            has_yielded = True

    if buffer or not has_yielded:
        yield bytes(buffer)
