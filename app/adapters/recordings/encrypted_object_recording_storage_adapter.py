import os
from collections.abc import Callable, Sequence

from app.contracts.object_storage import ObjectStorageClientContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.recordings.recording_byte_ranges import resolve_byte_span
from app.utilities.security.recording_encryption import (
    HEADER_SIZE,
    SALT_SIZE,
    RecordingCipherHeader,
    master_key_id,
    open_chunks,
    read_header,
    seal_recording,
    sealed_chunk_span,
)

# A player that asks for "the rest" (bytes=N-) gets at most this much at a
# time and asks for the next part: memory and latency stay bounded however
# long the call was.
OPEN_RANGE_PART_BYTES: int = 4 * 1024 * 1024


class EncryptedObjectRecordingStorageAdapter(RecordingStorageAdapterContract):
    """
    Call recordings in S3-compatible object storage in the EU, encrypted
    with the key of their business (`recording_encryption`: AES-256-GCM in
    64 KiB chunks, keys derived by HKDF from ENCRYPTION_KEY).

    The object storage only ever sees ciphertext. A read fetches the
    header, then only the sealed chunks of the asked range (a byte-range GET
    of a presigned URL) and opens them with the business's key, so a seek
    in a long call costs a chunk or two, in any API instance alike, with
    no copy on any server's disk. New recordings are sealed under the
    current key of the ring; a recording's header names the key it was
    sealed under, so recordings of a previous key (ENCRYPTION_KEYS) still
    play while that key is in the ring.
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

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        stored_header: bytes | None = self._client.get_object_range(
            require_object_key(location), 0, HEADER_SIZE - 1
        )
        if stored_header is None:
            return None

        header: RecordingCipherHeader = read_header(stored_header)
        total: int = header.plaintext_length
        span: tuple[int, int] | None = (
            (0, total - 1)
            if wanted is None
            else resolve_byte_span(limit_open_range(wanted), total)
        )
        if span is None or total == 0:
            return self._part(header, b"", total if span is None else 0)

        first_byte, last_byte = span
        first_chunk, stored_first, stored_last = sealed_chunk_span(
            header, first_byte, last_byte
        )
        sealed: bytes | None = self._client.get_object_range(
            location.path, stored_first, stored_last
        )
        if sealed is None:
            return None

        plaintext: bytes = open_chunks(
            self._secrets_by_key_id.get(header.key_id, self._master_secret),
            location,
            header,
            first_chunk,
            sealed,
        )
        start: int = first_byte - first_chunk * header.chunk_size
        return self._part(
            header, plaintext[start : start + last_byte - first_byte + 1], first_byte
        )

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        self._client.put_object(
            require_object_key(location),
            seal_recording(
                self._master_secret, location, audio, self._random_bytes(SALT_SIZE)
            ),
        )

    def delete(self, location: RecordingLocation) -> None:
        self._client.delete_object(require_object_key(location))

    def _part(
        self, header: RecordingCipherHeader, content: bytes, first_byte: int
    ) -> RecordingPart:
        return RecordingPart(
            content=content,
            media_type=header.media_type,
            first_byte=RecordingByteOffset(first_byte),
            total_bytes=RecordingByteCount(header.plaintext_length),
        )


def limit_open_range(wanted: RecordingByteRange) -> RecordingByteRange:
    """An open range ("from N to the end") cut to OPEN_RANGE_PART_BYTES."""

    if wanted.suffix_length is not None or wanted.last_byte is not None:
        return wanted

    first_byte: int = 0 if wanted.first_byte is None else int(wanted.first_byte)
    return RecordingByteRange(
        first_byte=RecordingByteOffset(first_byte),
        last_byte=RecordingByteOffset(first_byte + OPEN_RANGE_PART_BYTES - 1),
    )


def require_object_key(location: RecordingLocation) -> RecordingStoragePath:
    """The object key of a location; refuses an empty, absolute or `..` path."""

    path: str = str(location.path)
    if path == "" or path.startswith("/") or "\x00" in path or ".." in path.split("/"):
        raise ValidationFailedError(f"Invalid recording path {path!r}.")

    return location.path
