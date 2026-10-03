"""
The header of an age v1 file (https://age-encryption.org/v1): who can
open it and the MAC that binds it to its file key.

    age-encryption.org/v1
    -> X25519 <ephemeral share>
    <file key wrapped for that recipient>
    --- <HMAC-SHA256 of everything above, up to and including "---">

One X25519 stanza per recipient: the 16-byte file key is sealed with
ChaCha20-Poly1305 under HKDF-SHA256 of the X25519 shared secret (salt: the
ephemeral share and the recipient). Base64 is unpadded and stanza bodies
wrap at 64 columns, as the specification requires; other tools' stanza
types (scrypt, ssh, grease) are skipped when reading.
"""

import base64
import binascii
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

VERSION_LINE: bytes = b"age-encryption.org/v1"
STANZA_PREFIX: bytes = b"-> "
MAC_PREFIX: bytes = b"---"
X25519_STANZA_TYPE: bytes = b"X25519"
X25519_LABEL: bytes = b"age-encryption.org/v1/X25519"
HEADER_MAC_LABEL: bytes = b"header"
FILE_KEY_SIZE: int = 16
KEY_SIZE: int = 32
BODY_COLUMNS: int = 64
ZERO_NONCE: bytes = bytes(12)
# A header line or a stanza count beyond these is not a backup of ours.
MAX_LINE_BYTES: int = 4096
MAX_STANZAS: int = 64


class AgeFormatError(ValueError):
    """The bytes are not an age v1 file, or none of its stanzas opens."""


@dataclass(frozen=True)
class Stanza:
    """One recipient stanza: its type, its arguments and its body."""

    kind: bytes
    arguments: tuple[bytes, ...]
    body: bytes


@dataclass(frozen=True)
class ParsedHeader:
    """A header read from a file: its stanzas, the MACed bytes and the MAC."""

    stanzas: tuple[Stanza, ...]
    maced_bytes: bytes
    mac: bytes


def new_file_key() -> bytes:
    return os.urandom(FILE_KEY_SIZE)


def build_header(file_key: bytes, recipients: list[X25519PublicKey]) -> bytes:
    """The header for the recipients, its MAC line included."""

    if not recipients:
        raise AgeFormatError("An age file needs at least one recipient.")

    lines: list[bytes] = [VERSION_LINE]
    for recipient in recipients:
        lines.extend(wrap_for_recipient(file_key, recipient))

    maced: bytes = b"\n".join([*lines, MAC_PREFIX])
    return maced + b" " + encode_base64(header_mac(file_key, maced)) + b"\n"


def wrap_for_recipient(file_key: bytes, recipient: X25519PublicKey) -> list[bytes]:
    """The lines of one X25519 stanza that carries the file key."""

    ephemeral = X25519PrivateKey.generate()
    ephemeral_share: bytes = ephemeral.public_key().public_bytes_raw()
    recipient_bytes: bytes = recipient.public_bytes_raw()
    shared_secret: bytes = ephemeral.exchange(recipient)
    wrapped: bytes = ChaCha20Poly1305(
        wrapping_key(shared_secret, ephemeral_share, recipient_bytes)
    ).encrypt(ZERO_NONCE, file_key, None)
    return [
        STANZA_PREFIX + X25519_STANZA_TYPE + b" " + encode_base64(ephemeral_share),
        *wrap_body(encode_base64(wrapped)),
    ]


def read_header(source: BinaryIO) -> ParsedHeader:
    """Read the header and stop at the first byte of the payload."""

    try:
        version: bytes = read_line(source)
    except AgeFormatError:
        version = b""
    if version != VERSION_LINE:
        raise AgeFormatError("This is not an age v1 file.")

    maced: list[bytes] = [version]
    stanzas: list[Stanza] = []
    line: bytes = read_line(source)
    while line.startswith(STANZA_PREFIX):
        if len(stanzas) == MAX_STANZAS:
            raise AgeFormatError("The age header has too many stanzas.")

        parts: list[bytes] = line[len(STANZA_PREFIX) :].split(b" ")
        maced.append(line)
        body_lines: list[bytes] = read_body_lines(source)
        maced.extend(body_lines)
        stanzas.append(
            Stanza(
                kind=parts[0],
                arguments=tuple(parts[1:]),
                body=decode_base64(b"".join(body_lines)),
            )
        )
        line = read_line(source)

    if not line.startswith(MAC_PREFIX + b" ") or not stanzas:
        raise AgeFormatError("The age header has no stanza or no MAC line.")

    maced.append(MAC_PREFIX)
    return ParsedHeader(
        stanzas=tuple(stanzas),
        maced_bytes=b"\n".join(maced),
        mac=decode_base64(line[len(MAC_PREFIX) + 1 :]),
    )


def open_file_key(header: ParsedHeader, identity: X25519PrivateKey) -> bytes:
    """
    The file key from the identity's X25519 stanza, checked against the
    header MAC. AgeFormatError when no stanza opens with the identity or the
    header was changed.
    """

    identity_public: bytes = identity.public_key().public_bytes_raw()
    for stanza in header.stanzas:
        if stanza.kind != X25519_STANZA_TYPE or len(stanza.arguments) != 1:
            continue

        file_key: bytes | None = unwrap_x25519(stanza, identity, identity_public)
        if file_key is None:
            continue

        if not hmac.compare_digest(
            header_mac(file_key, header.maced_bytes), header.mac
        ):
            raise AgeFormatError("The age header was changed (its MAC is wrong).")

        return file_key

    raise AgeFormatError("The backup is not encrypted to this identity.")


def unwrap_x25519(
    stanza: Stanza,
    identity: X25519PrivateKey,
    identity_public: bytes,
) -> bytes | None:
    ephemeral_share: bytes = decode_base64(stanza.arguments[0])
    if len(ephemeral_share) != KEY_SIZE or len(stanza.body) != FILE_KEY_SIZE + 16:
        raise AgeFormatError("An X25519 stanza of the age header is malformed.")

    shared_secret: bytes = identity.exchange(
        X25519PublicKey.from_public_bytes(ephemeral_share)
    )
    if shared_secret == bytes(KEY_SIZE):
        raise AgeFormatError("An X25519 stanza has a low-order ephemeral share.")

    try:
        return ChaCha20Poly1305(
            wrapping_key(shared_secret, ephemeral_share, identity_public)
        ).decrypt(ZERO_NONCE, stanza.body, None)
    except InvalidTag:
        return None


def wrapping_key(
    shared_secret: bytes, ephemeral_share: bytes, recipient: bytes
) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=ephemeral_share + recipient,
        info=X25519_LABEL,
    ).derive(shared_secret)


def header_mac(file_key: bytes, maced_bytes: bytes) -> bytes:
    mac_key: bytes = HKDF(
        algorithm=hashes.SHA256(), length=KEY_SIZE, salt=None, info=HEADER_MAC_LABEL
    ).derive(file_key)
    return hmac.new(mac_key, maced_bytes, hashlib.sha256).digest()


def wrap_body(encoded: bytes) -> list[bytes]:
    """Body lines of 64 columns; the last is shorter (empty if need be)."""

    lines: list[bytes] = [
        encoded[start : start + BODY_COLUMNS]
        for start in range(0, len(encoded), BODY_COLUMNS)
    ]
    if not lines or len(lines[-1]) == BODY_COLUMNS:
        lines.append(b"")

    return lines


def read_body_lines(source: BinaryIO) -> list[bytes]:
    lines: list[bytes] = []
    while True:
        line: bytes = read_line(source)
        lines.append(line)
        if len(line) > BODY_COLUMNS:
            raise AgeFormatError("A stanza body line of the age header is too long.")
        if len(line) < BODY_COLUMNS:
            return lines


def read_line(source: BinaryIO) -> bytes:
    line: bytes = source.readline(MAX_LINE_BYTES + 1)
    if not line.endswith(b"\n") or len(line) > MAX_LINE_BYTES:
        raise AgeFormatError("The age header is cut off or has an overlong line.")

    return line[:-1]


def encode_base64(data: bytes) -> bytes:
    return base64.b64encode(data).rstrip(b"=")


def decode_base64(encoded: bytes) -> bytes:
    """Strict unpadded base64: anything a canonical encoder would not write fails."""

    try:
        decoded: bytes = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4), validate=True
        )
    except (binascii.Error, ValueError) as error:
        raise AgeFormatError("The age header has invalid base64.") from error

    if encode_base64(decoded) != encoded:
        raise AgeFormatError("The age header has non-canonical base64.")

    return decoded
