"""
Encryption of full business export archives at rest, with a key of each
business, like customer files (`media_encryption`).

Keys (HKDF-SHA256): the business key is derived from the platform's master
secret (ENCRYPTION_KEY) and the business id; each archive gets its own key
from the business key, a random salt and its path, so an archive copied to
another business or path does not open there. The archive is sealed whole
with AES-256-GCM, the header authenticated with it.

    header = magic(4) key id(8) salt(16) nonce(12)
    body   = AES-GCM(archive key, nonce, aad=header) of the ZIP
"""

import struct
from collections.abc import Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.utilities.security.recording_encryption import master_key_id

MAGIC: bytes = b"AWX1"
KEY_ID_SIZE: int = 8
SALT_SIZE: int = 16
NONCE_SIZE: int = 12
HEADER_FORMAT: str = f">4s{KEY_ID_SIZE}s{SALT_SIZE}s{NONCE_SIZE}s"
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)
BUSINESS_KEY_SALT: bytes = b"assistant-workshop/business-exports/v1"


def derive_archive_key(
    master_secret: PlatformSecret,
    business_id: BusinessId,
    path: ExportArchivePath,
    salt: bytes,
) -> bytes:
    """One archive's key: HKDF of the business key, its salt and its path."""

    business_key: bytes = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=BUSINESS_KEY_SALT,
        info=f"business:{business_id}".encode(),
    ).derive(str(master_secret).encode("utf-8"))
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=f"export:{path}".encode(),
    ).derive(business_key)


def seal_archive(
    master_secret: PlatformSecret,
    business_id: BusinessId,
    path: ExportArchivePath,
    archive: bytes,
    salt: bytes,
    nonce: bytes,
) -> bytes:
    """The sealed archive: the header, then the encrypted ZIP."""

    header: bytes = struct.pack(
        HEADER_FORMAT, MAGIC, master_key_id(master_secret), salt, nonce
    )
    cipher = AESGCM(derive_archive_key(master_secret, business_id, path, salt))
    return header + cipher.encrypt(nonce, archive, header)


def open_archive(
    secrets_by_key_id: Mapping[bytes, PlatformSecret],
    business_id: BusinessId,
    path: ExportArchivePath,
    sealed: bytes,
) -> bytes:
    """
    The archive's bytes, opened with the key of the ring it was sealed under.

    Raises:
        ExternalServiceError: not an archive of ours, a key no longer in the
            ring, another business or path, or changed bytes.
    """

    if len(sealed) < HEADER_SIZE or not sealed.startswith(MAGIC):
        raise ExternalServiceError("The stored export is not an encrypted archive.")

    _, key_id, salt, nonce = struct.unpack(HEADER_FORMAT, sealed[:HEADER_SIZE])
    secret: PlatformSecret | None = secrets_by_key_id.get(key_id)
    if secret is None:
        raise ExternalServiceError(
            "The export was encrypted with a key no longer in ENCRYPTION_KEYS."
        )

    cipher = AESGCM(derive_archive_key(secret, business_id, path, salt))
    try:
        return cipher.decrypt(nonce, sealed[HEADER_SIZE:], sealed[:HEADER_SIZE])
    except InvalidTag as error:
        raise ExternalServiceError("The stored export does not open.") from error
