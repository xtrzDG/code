"""
Encryption of customer files (voice notes, photos) at rest, with a key of
each business, like call recordings (`recording_encryption`).

Keys (HKDF-SHA256): the business key is derived from the platform's master
secret (ENCRYPTION_KEY) and the business id; each file gets its own key
from the business key, a random salt and its path, so a file copied to
another business or path does not open there and no stored key can leak.
A file is small (a voice note, a photo): it is sealed whole with
AES-256-GCM, the header authenticated with it.

    header = magic(4) key id(8) salt(16) nonce(12) media type(64)
    body   = AES-GCM(file key, nonce, aad=header) of the bytes
"""

import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.security.recording_encryption import master_key_id

MAGIC: bytes = b"AWM1"
KEY_ID_SIZE: int = 8
SALT_SIZE: int = 16
NONCE_SIZE: int = 12
MEDIA_TYPE_SIZE: int = 64
HEADER_FORMAT: str = f">4s{KEY_ID_SIZE}s{SALT_SIZE}s{NONCE_SIZE}s{MEDIA_TYPE_SIZE}s"
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)
BUSINESS_KEY_SALT: bytes = b"assistant-workshop/message-media/v1"


@dataclass(frozen=True)
class MediaCipherHeader:
    """The header of a sealed file, read back."""

    raw: bytes
    key_id: bytes
    salt: bytes
    nonce: bytes
    media_type: MessageMediaType


def derive_file_key(
    master_secret: PlatformSecret, location: MediaLocation, salt: bytes
) -> bytes:
    """One file's key: HKDF of the business key, its salt and its path."""

    business_key: bytes = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=BUSINESS_KEY_SALT,
        info=f"business:{location.business_id}".encode(),
    ).derive(str(master_secret).encode("utf-8"))
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=f"media:{location.path}".encode(),
    ).derive(business_key)


def seal_media(
    master_secret: PlatformSecret,
    location: MediaLocation,
    media: StoredMediaFile,
    salt: bytes,
    nonce: bytes,
) -> bytes:
    """The sealed file: the header, then the encrypted bytes."""

    header: bytes = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        master_key_id(master_secret),
        salt,
        nonce,
        str(media.media_type).encode("ascii").ljust(MEDIA_TYPE_SIZE, b"\x00"),
    )
    cipher = AESGCM(derive_file_key(master_secret, location, salt))
    return header + cipher.encrypt(nonce, media.content, header)


def read_media_header(sealed: bytes) -> MediaCipherHeader:
    """Parse a header; ExternalServiceError when it is not one of ours."""

    if len(sealed) < HEADER_SIZE or not sealed.startswith(MAGIC):
        raise ExternalServiceError("The stored file is not an encrypted media file.")

    magic, key_id, salt, nonce, media_type = struct.unpack(
        HEADER_FORMAT, sealed[:HEADER_SIZE]
    )
    del magic
    try:
        parsed_type = MessageMediaType(media_type.rstrip(b"\x00").decode("ascii"))
    except ValueError as error:
        raise ExternalServiceError("The stored file has a broken header.") from error

    return MediaCipherHeader(
        raw=sealed[:HEADER_SIZE],
        key_id=key_id,
        salt=salt,
        nonce=nonce,
        media_type=parsed_type,
    )


def open_media(
    master_secret: PlatformSecret,
    location: MediaLocation,
    sealed: bytes,
) -> StoredMediaFile:
    """
    The file's bytes and type.

    Raises:
        ExternalServiceError: another key, another business or path, or
            changed bytes.
    """

    header: MediaCipherHeader = read_media_header(sealed)
    if header.key_id != master_key_id(master_secret):
        raise ExternalServiceError("The file was encrypted with another ENCRYPTION_KEY.")

    cipher = AESGCM(derive_file_key(master_secret, location, header.salt))
    try:
        content: bytes = cipher.decrypt(
            header.nonce, sealed[HEADER_SIZE:], header.raw
        )
    except InvalidTag as error:
        raise ExternalServiceError("The stored file does not open.") from error

    return StoredMediaFile(content=content, media_type=header.media_type)
