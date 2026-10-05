"""
Signed, expiring booking manage links (`{CABINET_BASE_URL}/r/{token}`).

A token names one booking of one business, the version it was issued for
(the booking's start time: a moved booking gets a new link and the old one
stops managing it) and its expiry (whole seconds), followed by a truncated
HMAC-SHA256 over all of them, base64url without padding (71 characters).
Nothing is stored: the signature proves the platform made the link. The key
derives from ENCRYPTION_KEY with its own label, so it is never the key that
encrypts channel secrets nor the one of staff notification links; after a
key rotation a link signed with a previous key of the ring still opens
until it expires.
"""

import base64
import binascii
import hashlib
import hmac
import logging
import secrets
import struct
from collections.abc import Sequence
from uuid import UUID

from typed_time_provider import Microseconds

from app.contracts.booking_links import BookingManageTokenSignerContract
from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret

logger: logging.Logger = logging.getLogger(__name__)

TOKEN_VERSION: int = 1
KEY_LABEL: bytes = b"assistant-workshop/booking-manage-links/v1"
SIGNATURE_LENGTH: int = 12
MICROSECONDS_PER_SECOND: int = 1_000_000
# version, business uuid, booking uuid, booking start (seconds), expiry.
PAYLOAD_FORMAT: str = "!B16s16sII"
PAYLOAD_LENGTH: int = struct.calcsize(PAYLOAD_FORMAT)
LARGEST_SECONDS: int = 2**32 - 1


def derive_manage_link_key(encryption_key: PlatformSecret | None) -> bytes:
    """
    The signing key: from ENCRYPTION_KEY, or a key of this process alone
    when none is set (development: links stop working after a restart).
    """

    if encryption_key is None or str(encryption_key).strip() == "":
        logger.warning(
            "ENCRYPTION_KEY is not set; booking manage links are signed with a "
            "temporary key and stop working after a restart."
        )
        return secrets.token_bytes(32)

    return hmac.new(
        str(encryption_key).strip().encode("utf-8"), KEY_LABEL, hashlib.sha256
    ).digest()


class BookingManageTokenSigner(BookingManageTokenSignerContract):
    """HMAC-signed manage link tokens (see the module docstring)."""

    def __init__(
        self,
        encryption_key: PlatformSecret | None,
        previous_keys: Sequence[PlatformSecret] = (),
    ) -> None:
        self._key: bytes = derive_manage_link_key(encryption_key)
        self._verification_keys: list[bytes] = [
            self._key,
            *(derive_manage_link_key(previous_key) for previous_key in previous_keys),
        ]

    def sign(self, claims: BookingManageClaims) -> BookingManageToken:
        payload: bytes = struct.pack(
            PAYLOAD_FORMAT,
            TOKEN_VERSION,
            prefixed_uuid_bytes(str(claims.business_id), BusinessId.prefix),
            prefixed_uuid_bytes(str(claims.booking_id), BookingId.prefix),
            min(int(claims.booking_version), LARGEST_SECONDS),
            min(int(claims.expires_at) // MICROSECONDS_PER_SECOND, LARGEST_SECONDS),
        )
        token: bytes = payload + sign_payload(self._key, payload)
        return BookingManageToken(base64.urlsafe_b64encode(token).rstrip(b"=").decode())

    def read(self, token: BookingManageToken) -> BookingManageClaims | None:
        text: str = str(token)
        try:
            raw: bytes = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        except binascii.Error, ValueError:
            return None

        if len(raw) != PAYLOAD_LENGTH + SIGNATURE_LENGTH:
            return None

        payload, signature = raw[:PAYLOAD_LENGTH], raw[PAYLOAD_LENGTH:]
        if not any(
            hmac.compare_digest(signature, sign_payload(key, payload))
            for key in self._verification_keys
        ):
            return None

        version, business, booking, starts_at, expires = struct.unpack(
            PAYLOAD_FORMAT, payload
        )
        if version != TOKEN_VERSION:
            return None

        return BookingManageClaims(
            business_id=BusinessId(UUID(bytes=business)),
            booking_id=BookingId(UUID(bytes=booking)),
            booking_version=BookingStartsAtUnixSeconds(starts_at),
            expires_at=Microseconds(expires * MICROSECONDS_PER_SECOND),
        )


def sign_payload(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, payload, hashlib.sha256).digest()[:SIGNATURE_LENGTH]


def prefixed_uuid_bytes(prefixed_id: str, prefix: str) -> bytes:
    return UUID(prefixed_id.removeprefix(f"{prefix}_")).bytes
