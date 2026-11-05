"""S3-compatible object storage (the EU bucket of call recordings)."""

from collections.abc import Iterable
from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.typings.conversations.strings import RecordingStoragePath


class ObjectStorageClientContract(ClientContract, Protocol):
    """
    Objects of one bucket. Byte offsets are inclusive, as in an HTTP
    `Range: bytes=first-last` (technical values of the transport).
    """

    def put_object(self, key: RecordingStoragePath, body: bytes) -> None:
        """Store the object (replacing one with the same key)."""
        raise NotImplementedError

    def put_object_parts(
        self, key: RecordingStoragePath, parts: Iterable[bytes]
    ) -> None:
        """
        Store an object given as consecutive parts (each but the last at
        least 5 MiB), held one at a time: one PUT when there is a single
        part, a multipart upload otherwise (aborted when a part fails, so no
        half object stays).
        """
        raise NotImplementedError

    def get_object_range(
        self,
        key: RecordingStoragePath,
        first_byte: int,
        last_byte: int,
    ) -> bytes | None:
        """
        The bytes `first_byte`-`last_byte` of the object (fewer at its end);
        None when there is no such object.
        """
        raise NotImplementedError

    def delete_object(self, key: RecordingStoragePath) -> None:
        """Delete the object; a missing object is not an error."""
        raise NotImplementedError
