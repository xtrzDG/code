"""
VAPID (RFC 8292): the platform proves to push services that it is the
sender a browser subscribed for, with an ES256 JWT signed by the platform
key, valid for one push service origin and a few hours.
"""

import json
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from app.clients.webpush.push_encryption import (
    decode_base64url,
    encode_base64url,
    load_public_key,
    public_key_bytes,
)

PRIVATE_KEY_LENGTH: int = 32
COORDINATE_LENGTH: int = 32
# Push services refuse tokens valid for more than 24 hours.
TOKEN_LIFETIME_SECONDS: int = 12 * 60 * 60
JWT_HEADER: dict[str, str] = {"typ": "JWT", "alg": "ES256"}


def load_vapid_private_key(encoded_key: str) -> ec.EllipticCurvePrivateKey:
    """
    The platform key from WEB_PUSH_VAPID_PRIVATE_KEY: the 32-byte P-256
    scalar in base64url, as `npx web-push generate-vapid-keys` prints it.
    Raises ValueError for anything else.
    """

    raw_key: bytes = decode_base64url(encoded_key)
    if len(raw_key) != PRIVATE_KEY_LENGTH:
        raise ValueError("A VAPID private key is 32 bytes in base64url.")

    return ec.derive_private_key(int.from_bytes(raw_key, "big"), ec.SECP256R1())


def check_vapid_key_pair(
    private_key: ec.EllipticCurvePrivateKey,
    encoded_public_key: str,
) -> None:
    """ValueError unless the public key belongs to the private key."""

    stated: bytes = public_key_bytes(
        load_public_key(decode_base64url(encoded_public_key))
    )
    if stated != public_key_bytes(private_key.public_key()):
        raise ValueError(
            "WEB_PUSH_VAPID_PUBLIC_KEY does not belong to WEB_PUSH_VAPID_PRIVATE_KEY."
        )


def push_service_origin(endpoint: str) -> str:
    """The `aud` of the token: scheme and host of the subscription endpoint."""

    parts = urlsplit(endpoint)
    return f"{parts.scheme}://{parts.netloc}"


def sign_vapid_token(
    private_key: ec.EllipticCurvePrivateKey,
    audience: str,
    subject: str,
    now_seconds: int,
) -> str:
    """A compact ES256 JWT for one push service origin."""

    claims: dict[str, str | int] = {
        "aud": audience,
        "exp": now_seconds + TOKEN_LIFETIME_SECONDS,
        "sub": subject,
    }
    signing_input: str = (
        encode_base64url(json.dumps(JWT_HEADER, separators=(",", ":")).encode())
        + "."
        + encode_base64url(json.dumps(claims, separators=(",", ":")).encode())
    )
    der_signature: bytes = private_key.sign(
        signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256())
    )
    r, s = decode_dss_signature(der_signature)
    raw_signature: bytes = r.to_bytes(COORDINATE_LENGTH, "big") + s.to_bytes(
        COORDINATE_LENGTH, "big"
    )
    return f"{signing_input}.{encode_base64url(raw_signature)}"


def vapid_authorization(token: str, encoded_public_key: str) -> str:
    """The Authorization header value of RFC 8292 (`vapid t=..., k=...`)."""

    public_key: str = encoded_public_key.strip().rstrip("=")
    return f"vapid t={token}, k={public_key}"
