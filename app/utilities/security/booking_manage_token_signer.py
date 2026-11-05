"""
Signed, expiring booking manage links (`{CABINET_BASE_URL}/r/{token}`).

A token names one booking of one business, the version it was issued for
(the booking's start time: a moved booking gets a new link and the old one
stops managing it), its expiry (whole seconds) and the booking's link
generation (24 bits: staff revoking the booking's links draw a new one,
and a link of another generation no longer opens), followed by an
HMAC-SHA256 over all of them truncated to 128 bits, base64url without
padding (80 characters, token version 4). Version 5 is the same shape for
a booking page's short-lived credential
(`BookingManageClaims.is_page_session`), which is never sent in a message.
Links signed before generations existed are still read, as generation 0,
until they expire or the booking's links are revoked: version 2 (76
characters) and its page credential version 3, and version 1 (a 96-bit
MAC, 71 characters). The signature proves the platform made the link; the
booking keeps only its generation. The key
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
    BookingLinkGeneration,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret

logger: logging.Logger = logging.getLogger(__name__)

TOKEN_VERSION: int = 4
PAGE_SESSION_VERSION: int = 5
# Versions read and never signed again: links (2, 1) and page credentials
# (3) from before link generations, all of generation 0.
UNGENERATIONAL_PAGE_SESSION_VERSION: int = 3
PAGE_SESSION_VERSIONS: frozenset[int] = frozenset(
    {PAGE_SESSION_VERSION, UNGENERATIONAL_PAGE_SESSION_VERSION}
)
KEY_LABEL: bytes = b"assistant-workshop/booking-manage-links/v1"
# Bytes of the MAC by token version: 128 bits now, 96 for the links of
# version 1, which are read until they expire (at most a day after their
# booking ends) and never signed again.
SIGNATURE_LENGTHS: dict[int, int] = {
    PAGE_SESSION_VERSION: 16,
    TOKEN_VERSION: 16,
    UNGENERATIONAL_PAGE_SESSION_VERSION: 16,
    2: 16,
    1: 12,
}
MICROSECONDS_PER_SECOND: int = 1_000_000
# version, business uuid, booking uuid, booking start (seconds), expiry:
# the claims of versions 1 to 3.
PAYLOAD_FORMAT: str = "!B16s16sII"
PAYLOAD_LENGTH: int = struct.calcsize(PAYLOAD_FORMAT)
# Versions 4 and 5 add the link generation (3 bytes, big-endian), so the
# token is 60 bytes: 80 characters with no spare bits.
GENERATION_LENGTH: int = 3
PAYLOAD_LENGTHS: dict[int, int] = {
    version: PAYLOAD_LENGTH
    + (GENERATION_LENGTH if version in {TOKEN_VERSION, PAGE_SESSION_VERSION} else 0)
    for version in SIGNATURE_LENGTHS
}
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
        version: int = PAGE_SESSION_VERSION if claims.is_page_session else TOKEN_VERSION
        payload: bytes = struct.pack(
            PAYLOAD_FORMAT,
            version,
            prefixed_uuid_bytes(str(claims.business_id), BusinessId.prefix),
            prefixed_uuid_bytes(str(claims.booking_id), BookingId.prefix),
            min(int(claims.booking_version), LARGEST_SECONDS),
            min(int(claims.expires_at) // MICROSECONDS_PER_SECOND, LARGEST_SECONDS),
        ) + int(claims.link_generation).to_bytes(GENERATION_LENGTH, "big")
        token: bytes = payload + sign_payload(
            self._key, payload, SIGNATURE_LENGTHS[version]
        )
        return BookingManageToken(base64.urlsafe_b64encode(token).rstrip(b"=").decode())

    def read(self, token: BookingManageToken) -> BookingManageClaims | None:
        text: str = str(token)
        try:
            raw: bytes = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        except binascii.Error, ValueError:
            return None

        signature_length: int | None = (
            SIGNATURE_LENGTHS.get(raw[0]) if len(raw) > PAYLOAD_LENGTH else None
        )
        if signature_length is None:
            return None

        payload_length: int = PAYLOAD_LENGTHS[raw[0]]
        if len(raw) != payload_length + signature_length:
            return None

        # Only the one spelling this signer writes: another (the spare low
        # bits of the last character changed) is an altered link, even
        # though it decodes to the same bytes.
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != text:
            return None

        payload, signature = raw[:payload_length], raw[payload_length:]
        if not any(
            hmac.compare_digest(signature, sign_payload(key, payload, signature_length))
            for key in self._verification_keys
        ):
            return None

        version, business, booking, starts_at, expires = struct.unpack(
            PAYLOAD_FORMAT, payload[:PAYLOAD_LENGTH]
        )

        return BookingManageClaims(
            business_id=BusinessId(UUID(bytes=business)),
            booking_id=BookingId(UUID(bytes=booking)),
            booking_version=BookingStartsAtUnixSeconds(starts_at),
            expires_at=Microseconds(expires * MICROSECONDS_PER_SECOND),
            is_page_session=version in PAGE_SESSION_VERSIONS,
            link_generation=BookingLinkGeneration(
                int.from_bytes(payload[PAYLOAD_LENGTH:], "big")
            ),
        )


def sign_payload(key: bytes, payload: bytes, length: int) -> bytes:
    """The payload's HMAC-SHA256 truncated to `length` bytes (its version's)."""

    return hmac.new(key, payload, hashlib.sha256).digest()[:length]


def prefixed_uuid_bytes(prefixed_id: str, prefix: str) -> bytes:
    return UUID(prefixed_id.removeprefix(f"{prefix}_")).bytes
