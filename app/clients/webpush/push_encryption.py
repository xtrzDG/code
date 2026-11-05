"""
Message encryption of Web Push (RFC 8291) in the aes128gcm content coding
(RFC 8188): one record, the sender's ephemeral P-256 key in the header.

The payload is readable only by the browser that owns the subscription's
private key and auth secret; the push service (Google, Mozilla, Apple)
sees ciphertext. Pure functions: tests check them against the example of
RFC 8291, appendix A.
"""

import base64
import secrets
import struct

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

RECORD_SIZE: int = 4096
SALT_LENGTH: int = 16
AUTH_SECRET_LENGTH: int = 16
KEY_LENGTH: int = 16
NONCE_LENGTH: int = 12
TAG_LENGTH: int = 16
# The last (and only) record ends with this delimiter (RFC 8188, 2).
LAST_RECORD_DELIMITER: bytes = b"\x02"
# What fits in one record: the record size less the delimiter and the tag.
MAX_PLAINTEXT_LENGTH: int = RECORD_SIZE - len(LAST_RECORD_DELIMITER) - TAG_LENGTH
WEB_PUSH_INFO: bytes = b"WebPush: info\x00"
CONTENT_KEY_INFO: bytes = b"Content-Encoding: aes128gcm\x00"
NONCE_INFO: bytes = b"Content-Encoding: nonce\x00"


def decode_base64url(text: str) -> bytes:
    """Base64url with or without padding (browsers send it without)."""

    stripped: str = text.strip().rstrip("=")
    return base64.urlsafe_b64decode(stripped + "=" * (-len(stripped) % 4))


def encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def public_key_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    """The uncompressed point (65 bytes) of a P-256 public key."""

    return key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )


def load_public_key(point: bytes) -> ec.EllipticCurvePublicKey:
    """A P-256 public key from its uncompressed point; ValueError if invalid."""

    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)


def new_sender_key() -> ec.EllipticCurvePrivateKey:
    """A fresh ephemeral key: every message uses its own."""

    return ec.generate_private_key(ec.SECP256R1())


def new_salt() -> bytes:
    return secrets.token_bytes(SALT_LENGTH)


def _derive(secret: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    ).derive(secret)


def encrypt_push_payload(
    payload: bytes,
    receiver_public_key: bytes,
    auth_secret: bytes,
    sender_key: ec.EllipticCurvePrivateKey,
    salt: bytes,
) -> bytes:
    """
    The request body for the push service: the aes128gcm header (salt,
    record size, the sender's public key) and the encrypted payload.

    Raises ValueError for a payload too long for one record, a malformed
    browser key or an auth secret of the wrong length.
    """

    if len(payload) > MAX_PLAINTEXT_LENGTH:
        raise ValueError("The push payload is longer than one record.")

    if len(auth_secret) != AUTH_SECRET_LENGTH or len(salt) != SALT_LENGTH:
        raise ValueError("The push auth secret or salt has the wrong length.")

    receiver_key: ec.EllipticCurvePublicKey = load_public_key(receiver_public_key)
    sender_public: bytes = public_key_bytes(sender_key.public_key())
    shared_secret: bytes = sender_key.exchange(ec.ECDH(), receiver_key)
    input_key: bytes = _derive(
        shared_secret,
        auth_secret,
        WEB_PUSH_INFO + receiver_public_key + sender_public,
        32,
    )
    content_key: bytes = _derive(input_key, salt, CONTENT_KEY_INFO, KEY_LENGTH)
    nonce: bytes = _derive(input_key, salt, NONCE_INFO, NONCE_LENGTH)
    ciphertext: bytes = AESGCM(content_key).encrypt(
        nonce, payload + LAST_RECORD_DELIMITER, None
    )
    header: bytes = (
        salt
        + struct.pack("!I", RECORD_SIZE)
        + struct.pack("!B", len(sender_public))
        + sender_public
    )
    return header + ciphertext
