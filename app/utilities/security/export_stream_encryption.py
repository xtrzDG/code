"""
Streamed encryption of full business export archives (format AWX2): the
archive is sealed segment by segment while it is read from its temporary
file, so neither the archive nor its ciphertext is ever held in memory.

Keys are those of `export_encryption` (per business and per archive).
Each segment of `segment_size` plaintext bytes (the last one shorter, or
empty for an empty archive) is sealed with AES-256-GCM under its own nonce,
the STREAM construction: a random 7-byte prefix, the segment's number
(4 bytes) and a last-segment flag (1 byte), with the header as associated
data. Segments cannot be reordered, dropped, cut off at the end or moved
to another archive without failing to open.

    header  = magic "AWX2"(4) key id(8) salt(16) nonce prefix(7) segment size(4)
    segment = AES-GCM(archive key, prefix | number | last, aad=header)
"""

import struct
from collections.abc import Iterator, Mapping
from typing import BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.utilities.security.export_encryption import (
    KEY_ID_SIZE,
    SALT_SIZE,
    derive_archive_key,
    open_archive,
)
from app.utilities.security.recording_encryption import master_key_id

STREAM_MAGIC: bytes = b"AWX2"
NONCE_PREFIX_SIZE: int = 7
# 1 MiB of the archive per segment: 16 bytes of tag each, a megabyte held
# at a time while sealing.
SEGMENT_SIZE: int = 1024 * 1024
TAG_SIZE: int = 16
STREAM_HEADER_FORMAT: str = f">4s{KEY_ID_SIZE}s{SALT_SIZE}s{NONCE_PREFIX_SIZE}sI"
STREAM_HEADER_SIZE: int = struct.calcsize(STREAM_HEADER_FORMAT)
LAST_SEGMENT: bytes = b"\x01"
MORE_SEGMENTS: bytes = b"\x00"


def segment_nonce(prefix: bytes, number: int, is_last: bool) -> bytes:
    """The 12-byte nonce of one segment."""

    return (
        prefix
        + number.to_bytes(4, "big")
        + (LAST_SEGMENT if is_last else MORE_SEGMENTS)
    )


def seal_stream(
    master_secret: PlatformSecret,
    business_id: BusinessId,
    path: ExportArchivePath,
    source: BinaryIO,
    salt: bytes,
    nonce_prefix: bytes,
    segment_size: int = SEGMENT_SIZE,
) -> Iterator[bytes]:
    """
    The sealed archive, a piece at a time: the header, then each sealed
    segment of `source` (read from where it stands to its end).
    """

    header: bytes = struct.pack(
        STREAM_HEADER_FORMAT,
        STREAM_MAGIC,
        master_key_id(master_secret),
        salt,
        nonce_prefix,
        segment_size,
    )
    yield header
    cipher = AESGCM(derive_archive_key(master_secret, business_id, path, salt))
    number: int = 0
    current: bytes = source.read(segment_size)
    while True:
        following: bytes = source.read(segment_size)
        is_last: bool = not following
        yield cipher.encrypt(
            segment_nonce(nonce_prefix, number, is_last), current, header
        )
        if is_last:
            return

        current = following
        number += 1


def open_stream(
    secrets_by_key_id: Mapping[bytes, PlatformSecret],
    business_id: BusinessId,
    path: ExportArchivePath,
    sealed: bytes,
) -> bytes:
    """
    The archive's bytes from a sealed AWX2 archive.

    Raises:
        ExternalServiceError: a key no longer in the ring, another business
            or path, or changed, reordered or cut-off segments.
    """

    if len(sealed) < STREAM_HEADER_SIZE + TAG_SIZE:
        raise ExternalServiceError("The stored export is cut off.")

    header: bytes = sealed[:STREAM_HEADER_SIZE]
    _, key_id, salt, prefix, segment_size = struct.unpack(STREAM_HEADER_FORMAT, header)
    secret: PlatformSecret | None = secrets_by_key_id.get(key_id)
    if secret is None:
        raise ExternalServiceError(
            "The export was encrypted with a key no longer in ENCRYPTION_KEYS."
        )

    cipher = AESGCM(derive_archive_key(secret, business_id, path, salt))
    body: bytes = sealed[STREAM_HEADER_SIZE:]
    step: int = int(segment_size) + TAG_SIZE
    starts: list[int] = list(range(0, len(body), step))
    plain: list[bytes] = []
    try:
        for number, start in enumerate(starts):
            is_last: bool = number == len(starts) - 1
            plain.append(
                cipher.decrypt(
                    segment_nonce(prefix, number, is_last),
                    body[start : start + step],
                    header,
                )
            )
    except InvalidTag as error:
        raise ExternalServiceError("The stored export does not open.") from error

    return b"".join(plain)


def open_sealed_archive(
    secrets_by_key_id: Mapping[bytes, PlatformSecret],
    business_id: BusinessId,
    path: ExportArchivePath,
    sealed: bytes,
) -> bytes:
    """
    The archive's bytes, whichever way it was sealed: in segments (AWX2)
    or, written before segments, whole (AWX1, `open_archive`).
    """

    if sealed.startswith(STREAM_MAGIC):
        return open_stream(secrets_by_key_id, business_id, path, sealed)

    return open_archive(secrets_by_key_id, business_id, path, sealed)
