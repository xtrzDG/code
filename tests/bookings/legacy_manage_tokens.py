"""
Booking manage links as earlier versions signed them: version 1 (a 96-bit
MAC, 71 characters) and version 2 (128 bits, 76 characters; its page
credential version 3), both from before link generations.
"""

import base64
import struct

from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.security.booking_manage_token_signer import (
    MICROSECONDS_PER_SECOND,
    PAYLOAD_FORMAT,
    derive_manage_link_key,
    prefixed_uuid_bytes,
    sign_payload,
)

LEGACY_VERSION: int = 1
LEGACY_SIGNATURE_LENGTH: int = 12
UNGENERATIONAL_VERSION: int = 2
UNGENERATIONAL_SIGNATURE_LENGTH: int = 16


def legacy_token(
    key: PlatformSecret,
    claims: BookingManageClaims,
    version: int = LEGACY_VERSION,
    signature_length: int = LEGACY_SIGNATURE_LENGTH,
) -> BookingManageToken:
    payload: bytes = struct.pack(
        PAYLOAD_FORMAT,
        version,
        prefixed_uuid_bytes(str(claims.business_id), BusinessId.prefix),
        prefixed_uuid_bytes(str(claims.booking_id), BookingId.prefix),
        int(claims.booking_version),
        int(claims.expires_at) // MICROSECONDS_PER_SECOND,
    )
    signature: bytes = sign_payload(
        derive_manage_link_key(key), payload, signature_length
    )
    return BookingManageToken(
        base64.urlsafe_b64encode(payload + signature).rstrip(b"=").decode()
    )


def ungenerational_token(
    key: PlatformSecret, claims: BookingManageClaims
) -> BookingManageToken:
    """A link of version 2 (or its page credential, version 3)."""

    return legacy_token(
        key,
        claims,
        UNGENERATIONAL_VERSION + (1 if claims.is_page_session else 0),
        UNGENERATIONAL_SIGNATURE_LENGTH,
    )
