"""
Encrypt and decrypt whole files in the age v1 format, streaming.

The payload after the header is a 16-byte nonce and the plaintext in
64 KiB chunks, each sealed with ChaCha20-Poly1305 under HKDF-SHA256 of the
file key and the nonce; a chunk's nonce is its number and a "last chunk"
flag, so a cut, reordered or extended file fails to open. Memory stays at
two chunks whatever the size of the database dump.
"""

import os
from typing import BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.utilities.security.age.age_header import (
    AgeFormatError,
    build_header,
    new_file_key,
    open_file_key,
    read_header,
)

CHUNK_SIZE: int = 64 * 1024
TAG_SIZE: int = 16
SEALED_CHUNK_SIZE: int = CHUNK_SIZE + TAG_SIZE
PAYLOAD_NONCE_SIZE: int = 16
PAYLOAD_LABEL: bytes = b"payload"
COUNTER_BYTES: int = 11


def encrypt_stream(
    source: BinaryIO,
    target: BinaryIO,
    recipients: list[X25519PublicKey],
) -> None:
    """Write `source` to `target` encrypted to every recipient."""

    file_key: bytes = new_file_key()
    nonce: bytes = os.urandom(PAYLOAD_NONCE_SIZE)
    target.write(build_header(file_key, recipients))
    target.write(nonce)
    cipher = ChaCha20Poly1305(payload_key(file_key, nonce))
    chunk: bytes = read_exactly(source, CHUNK_SIZE)
    counter: int = 0
    while True:
        following: bytes = (
            read_exactly(source, CHUNK_SIZE) if len(chunk) == CHUNK_SIZE else b""
        )
        is_last: bool = following == b""
        target.write(cipher.encrypt(chunk_nonce(counter, is_last), chunk, None))
        if is_last:
            return

        chunk = following
        counter += 1


def decrypt_stream(
    source: BinaryIO,
    target: BinaryIO,
    identity: X25519PrivateKey,
) -> None:
    """
    Write the plaintext of the age file in `source` to `target`.

    Raises:
        AgeFormatError: not an age file, not for this identity, or changed,
            cut off or extended anywhere (the plaintext written so far must
            then be thrown away).
    """

    file_key: bytes = open_file_key(read_header(source), identity)
    nonce: bytes = read_exactly(source, PAYLOAD_NONCE_SIZE)
    if len(nonce) != PAYLOAD_NONCE_SIZE:
        raise AgeFormatError("The age payload is cut off before its nonce.")

    cipher = ChaCha20Poly1305(payload_key(file_key, nonce))
    sealed: bytes = read_exactly(source, SEALED_CHUNK_SIZE)
    counter: int = 0
    while True:
        following: bytes = (
            read_exactly(source, SEALED_CHUNK_SIZE)
            if len(sealed) == SEALED_CHUNK_SIZE
            else b""
        )
        is_last: bool = following == b""
        try:
            plaintext: bytes = cipher.decrypt(
                chunk_nonce(counter, is_last), sealed, None
            )
        except InvalidTag as error:
            raise AgeFormatError(
                "The backup archive was changed or cut off (chunk "
                f"{counter} does not open)."
            ) from error

        if is_last and plaintext == b"" and counter > 0:
            raise AgeFormatError("The age payload ends with an empty chunk.")

        target.write(plaintext)
        if is_last:
            return

        sealed = following
        counter += 1


def payload_key(file_key: bytes, nonce: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=nonce, info=PAYLOAD_LABEL
    ).derive(file_key)


def chunk_nonce(counter: int, is_last: bool) -> bytes:
    return counter.to_bytes(COUNTER_BYTES, "big") + (b"\x01" if is_last else b"\x00")


def read_exactly(source: BinaryIO, size: int) -> bytes:
    """Up to `size` bytes; fewer only at the end of the stream."""

    parts: list[bytes] = []
    remaining: int = size
    while remaining > 0:
        part: bytes = source.read(remaining)
        if not part:
            break

        parts.append(part)
        remaining -= len(part)

    return b"".join(parts)
