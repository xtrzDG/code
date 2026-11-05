"""
Which browser push subscriptions the platform accepts: endpoints of the
known push services only (the server posts to the address a browser
gives, so any other host would let a member make the server call it),
and keys that are a real P-256 point and a 16-byte secret.
"""

import base64
import binascii
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric import ec

from app.schemas.constants.environment import DeploymentEnvironment

# Push services of Chrome/Edge/Android (FCM), Firefox (Mozilla autopush),
# Safari and iOS (Apple) and legacy Edge (WNS); a host matches itself or
# any subdomain.
PUSH_SERVICE_HOSTS: tuple[str, ...] = (
    "fcm.googleapis.com",
    "push.services.mozilla.com",
    "push.apple.com",
    "notify.windows.com",
)
LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
AUTH_SECRET_LENGTH: int = 16


def is_supported_push_endpoint(
    endpoint: str,
    environment: DeploymentEnvironment,
) -> bool:
    """
    An https address of a known push service (outside production also a
    local test push service).
    """

    parts = urlsplit(endpoint)
    host: str = (parts.hostname or "").lower()
    if parts.username is not None or parts.password is not None:
        return False

    if environment is not DeploymentEnvironment.PRODUCTION and host in LOCAL_HOSTS:
        return parts.scheme in ("http", "https")

    if parts.scheme != "https" or parts.port not in (None, 443):
        return False

    return any(
        host == known or host.endswith(f".{known}") for known in PUSH_SERVICE_HOSTS
    )


def decode_key(text: str) -> bytes | None:
    stripped: str = text.strip().rstrip("=")
    try:
        return base64.urlsafe_b64decode(stripped + "=" * (-len(stripped) % 4))
    except binascii.Error, ValueError:
        return None


def are_valid_push_keys(p256dh: str, auth: str) -> bool:
    """The browser's public key is a P-256 point and its secret 16 bytes."""

    point: bytes | None = decode_key(p256dh)
    secret: bytes | None = decode_key(auth)
    if point is None or secret is None or len(secret) != AUTH_SECRET_LENGTH:
        return False

    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)
    except ValueError:
        return False

    return True
