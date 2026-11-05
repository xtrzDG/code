"""
Signed notification links: version 2 carries a 128-bit MAC; links of
version 1 (a 96-bit MAC) sent before the change still open until they
expire, and no token mixes one version's byte with the other's MAC.
"""

import base64
import hashlib
import hmac
import struct
from uuid import UUID

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.notifications.staff_link_signer import (
    StaffLinkSigner,
    derive_link_key,
)

KEY = PlatformSecret("a-long-enough-encryption-key-for-the-tests")
PREVIOUS_KEY = PlatformSecret("the-key-before-the-last-rotation-of-the-ring")
EXPIRES = Microseconds(1_790_000_000_000_000)
PAYLOAD_FORMAT: str = "!B16sB16sI"
NOTIFICATIONS_CODE: int = 4


def encoded(token: bytes) -> StaffLinkToken:
    return StaffLinkToken(base64.urlsafe_b64encode(token).rstrip(b"=").decode())


def signature_of(payload: bytes, length: int, key: PlatformSecret = KEY) -> bytes:
    """HMAC-SHA256 of the payload under the link key, its first `length` bytes."""

    return hmac.new(derive_link_key(key), payload, hashlib.sha256).digest()[:length]


def payload_of(
    version: int, business_id: BusinessId, code: int = NOTIFICATIONS_CODE
) -> bytes:
    return struct.pack(
        PAYLOAD_FORMAT,
        version,
        UUID(str(business_id).removeprefix(f"{BusinessId.prefix}_")).bytes,
        code,
        bytes(16),
        int(EXPIRES) // 1_000_000,
    )


def notifications_claims(business_id: BusinessId) -> StaffLinkClaims:
    return StaffLinkClaims(
        business_id=business_id,
        target=StaffLinkTarget.NOTIFICATIONS,
        expires_at=EXPIRES,
    )


@pytest.mark.parametrize(
    "claims",
    [
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.CONVERSATION,
            conversation_id=ConversationId(),
            expires_at=EXPIRES,
        ),
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.LEAD,
            lead_id=LeadId(),
            expires_at=EXPIRES,
        ),
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.BOOKING,
            booking_id=BookingId(),
            expires_at=EXPIRES,
        ),
        notifications_claims(BusinessId()),
    ],
)
def test_signed_links_carry_their_page_and_a_128_bit_mac(
    claims: StaffLinkClaims,
) -> None:
    signer = StaffLinkSigner(KEY)

    token = signer.sign(claims)
    raw = base64.urlsafe_b64decode(str(token) + "=" * (-len(token) % 4))

    assert len(token) == 72
    assert raw[0] == 2
    assert raw[-16:] == signature_of(raw[:-16], 16)
    assert signer.read(token) == claims


def test_a_version_1_link_still_opens_until_it_expires() -> None:
    business_id = BusinessId()
    payload = payload_of(1, business_id)
    legacy = encoded(payload + signature_of(payload, 12))
    rotated = encoded(payload + signature_of(payload, 12, PREVIOUS_KEY))

    assert len(legacy) == 67
    assert StaffLinkSigner(KEY).read(legacy) == notifications_claims(business_id)
    # Signed before a key rotation: a previous key of the ring still reads it.
    assert StaffLinkSigner(KEY, [PREVIOUS_KEY]).read(rotated) == (
        notifications_claims(business_id)
    )
    assert StaffLinkSigner(KEY).read(rotated) is None


def test_no_token_mixes_one_version_with_the_other_s_mac() -> None:
    signer = StaffLinkSigner(KEY)
    business_id = BusinessId()
    current, legacy = payload_of(2, business_id), payload_of(1, business_id)
    unknown = payload_of(3, business_id)

    # A version-2 byte with the short MAC: a forger's 96-bit guess.
    assert signer.read(encoded(current + signature_of(current, 12))) is None
    assert signer.read(encoded(legacy + signature_of(legacy, 16))) is None
    assert signer.read(encoded(unknown + signature_of(unknown, 16))) is None
    assert signer.read(encoded(unknown + signature_of(unknown, 12))) is None


def test_altered_foreign_and_malformed_tokens_are_refused() -> None:
    signer = StaffLinkSigner(KEY)
    token = str(signer.sign(notifications_claims(BusinessId())))
    raw = base64.urlsafe_b64decode(token)
    altered = raw[:5] + bytes([raw[5] ^ 1]) + raw[6:]

    assert signer.read(encoded(altered)) is None
    assert StaffLinkSigner(PlatformSecret("x" * 40)).read(StaffLinkToken(token)) is None
    assert signer.read(StaffLinkToken(token[:-4])) is None
    assert signer.read(StaffLinkToken("A" * 71 + "-")) is None
    # The last character's spare bits set: the same bytes, another link.
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    legacy_payload = payload_of(1, BusinessId())
    legacy = str(encoded(legacy_payload + signature_of(legacy_payload, 12)))
    respelled = legacy[:-1] + alphabet[alphabet.index(legacy[-1]) | 0b11]
    assert base64.urlsafe_b64decode(respelled + "=") == base64.urlsafe_b64decode(
        legacy + "="
    )
    assert signer.read(StaffLinkToken(legacy)) is not None
    assert signer.read(StaffLinkToken(respelled)) is None

    unknown_target = payload_of(2, BusinessId(), code=99)
    assert (
        signer.read(encoded(unknown_target + signature_of(unknown_target, 16))) is None
    )


def test_without_an_encryption_key_links_still_work_within_the_process() -> None:
    signer = StaffLinkSigner(None)
    claims = notifications_claims(BusinessId())

    assert signer.read(signer.sign(claims)) == claims
    assert StaffLinkSigner(None).read(signer.sign(claims)) is None
