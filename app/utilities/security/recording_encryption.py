"""
Encryption of call recordings at rest, with a key of each business.

Keys (HKDF-SHA256): the business key is derived from the platform's master
secret (ENCRYPTION_KEY) and the business id; each recording gets its own
key from the business key, a random salt and its path. A recording copied
to another business or another path cannot be opened there, and no stored
key exists to leak.

An encrypted recording is a fixed header and the audio in chunks of
`CHUNK_SIZE` bytes, each sealed with AES-256-GCM (nonce: the chunk number).
A media player's byte range therefore needs only the chunks it covers: the
ranges map to ciphertext ranges without reading the rest. The header (the
plaintext length, the media type) and each chunk's number and "last chunk"
mark are authenticated with every chunk, so a reordered, cut or edited
recording fails to open instead of playing something else.

    header  = magic(4) key id(8) salt(16) chunk size(4) length(8) media type(64)
    chunk i = AES-GCM(object key, nonce=i, aad=header|i|is_last) of bytes
              [i * chunk size, (i + 1) * chunk size)
"""

import hashlib
import hmac
import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.schemas.dto.call_recordings import RecordingAudio, RecordingLocation
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.platform.strings import PlatformSecret

MAGIC: bytes = b"AWR1"
CHUNK_SIZE: int = 64 * 1024
TAG_SIZE: int = 16
SALT_SIZE: int = 16
KEY_ID_SIZE: int = 8
MEDIA_TYPE_SIZE: int = 64
HEADER_FORMAT: str = f">4s{KEY_ID_SIZE}s{SALT_SIZE}sIQ{MEDIA_TYPE_SIZE}s"
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)
BUSINESS_KEY_SALT: bytes = b"assistant-workshop/recordings/v1"
KEY_ID_LABEL: bytes = b"assistant-workshop/recordings/key-id"


@dataclass(frozen=True)
class RecordingCipherHeader:
    """The header of an encrypted recording, read back."""

    raw: bytes
    key_id: bytes
    salt: bytes
    chunk_size: int
    plaintext_length: int
    media_type: RecordingMediaType

    @property
    def chunk_count(self) -> int:
        """At least one chunk: an empty recording is one empty sealed chunk."""

        return max(1, -(-self.plaintext_length // self.chunk_size))


def master_key_id(master_secret: PlatformSecret) -> bytes:
    """A short fingerprint of the master secret (tells a wrong key apart)."""

    return hmac.new(
        str(master_secret).encode("utf-8"), KEY_ID_LABEL, hashlib.sha256
    ).digest()[:KEY_ID_SIZE]


def derive_business_key(
    master_secret: PlatformSecret, location: RecordingLocation
) -> bytes:
    """The business's recording key: HKDF of the master secret and its id."""

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=BUSINESS_KEY_SALT,
        info=f"business:{location.business_id}".encode(),
    ).derive(str(master_secret).encode("utf-8"))


def derive_object_key(
    master_secret: PlatformSecret,
    location: RecordingLocation,
    salt: bytes,
) -> bytes:
    """One recording's key: HKDF of the business key, its salt and its path."""

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=f"recording:{location.path}".encode(),
    ).derive(derive_business_key(master_secret, location))


def seal_recording(
    master_secret: PlatformSecret,
    location: RecordingLocation,
    audio: RecordingAudio,
    salt: bytes,
) -> bytes:
    """The encrypted recording: the header and every sealed chunk."""

    media_type: bytes = str(audio.media_type).encode("ascii")
    header: bytes = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        master_key_id(master_secret),
        salt,
        CHUNK_SIZE,
        len(audio.content),
        media_type.ljust(MEDIA_TYPE_SIZE, b"\x00"),
    )
    cipher = AESGCM(derive_object_key(master_secret, location, salt))
    parsed: RecordingCipherHeader = read_header(header)
    sealed: list[bytes] = [header]
    for index in range(parsed.chunk_count):
        chunk: bytes = audio.content[index * CHUNK_SIZE : (index + 1) * CHUNK_SIZE]
        sealed.append(
            cipher.encrypt(chunk_nonce(index), chunk, chunk_aad(parsed, index))
        )

    return b"".join(sealed)


def read_header(header: bytes) -> RecordingCipherHeader:
    """Parse a header; ExternalServiceError when it is not one of ours."""

    if len(header) < HEADER_SIZE or not header.startswith(MAGIC):
        raise ExternalServiceError(
            "The stored recording is not an encrypted recording."
        )

    magic, key_id, salt, chunk_size, length, media_type = struct.unpack(
        HEADER_FORMAT, header[:HEADER_SIZE]
    )
    del magic
    if chunk_size < 1:
        raise ExternalServiceError("The stored recording has a broken header.")

    return RecordingCipherHeader(
        raw=header[:HEADER_SIZE],
        key_id=key_id,
        salt=salt,
        chunk_size=chunk_size,
        plaintext_length=length,
        media_type=RecordingMediaType(media_type.rstrip(b"\x00").decode("ascii")),
    )


def sealed_chunk_span(
    header: RecordingCipherHeader,
    first_byte: int,
    last_byte: int,
) -> tuple[int, int, int]:
    """
    The first chunk number and the first and last stored byte (inclusive)
    of the sealed chunks that hold plaintext bytes `first_byte`-`last_byte`.
    """

    sealed_size: int = header.chunk_size + TAG_SIZE
    first_chunk: int = first_byte // header.chunk_size
    last_chunk: int = min(last_byte // header.chunk_size, header.chunk_count - 1)
    stored_length: int = (
        HEADER_SIZE + header.plaintext_length + header.chunk_count * TAG_SIZE
    )
    return (
        first_chunk,
        HEADER_SIZE + first_chunk * sealed_size,
        min(HEADER_SIZE + (last_chunk + 1) * sealed_size, stored_length) - 1,
    )


def open_chunks(
    master_secret: PlatformSecret,
    location: RecordingLocation,
    header: RecordingCipherHeader,
    first_chunk: int,
    sealed: bytes,
) -> bytes:
    """
    The plaintext of consecutive sealed chunks starting at `first_chunk`.

    Raises:
        ExternalServiceError: a chunk fails to open (another key, another
            business or path, or changed bytes).
    """

    if header.key_id != master_key_id(master_secret):
        raise ExternalServiceError(
            "The recording was encrypted with another ENCRYPTION_KEY."
        )

    cipher = AESGCM(derive_object_key(master_secret, location, header.salt))
    sealed_size: int = header.chunk_size + TAG_SIZE
    plaintext: list[bytes] = []
    for offset in range(0, len(sealed), sealed_size):
        index: int = first_chunk + offset // sealed_size
        try:
            plaintext.append(
                cipher.decrypt(
                    chunk_nonce(index),
                    sealed[offset : offset + sealed_size],
                    chunk_aad(header, index),
                )
            )
        except InvalidTag as error:
            raise ExternalServiceError(
                "The stored recording does not open with its business's key."
            ) from error

    return b"".join(plaintext)


def chunk_nonce(index: int) -> bytes:
    return index.to_bytes(12, "big")


def chunk_aad(header: RecordingCipherHeader, index: int) -> bytes:
    is_last: bool = index == header.chunk_count - 1
    return header.raw + index.to_bytes(8, "big") + (b"\x01" if is_last else b"\x00")
