"""
Signed, expiring notification links (`{CABINET_BASE_URL}/n/{token}`).

A token is short enough for an SMS: version, business, target page and its
id, expiry (whole seconds) and a truncated HMAC-SHA256 over all of them,
base64url without padding (about 67 characters). It grants nothing by
itself: the cabinet still signs the user in and checks their access to the
business; the signature only proves the platform made the link and when it
stops working. The key derives from ENCRYPTION_KEY with its own label, so
it is never the key that encrypts channel secrets. After a key rotation a
link signed with a previous key of the ring still opens until it expires.
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

from app.contracts.notification_utilities import StaffLinkSignerContract
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.value.prefixed_id import ValueReportId

logger: logging.Logger = logging.getLogger(__name__)

TOKEN_VERSION: int = 1
KEY_LABEL: bytes = b"assistant-workshop/staff-notification-links/v1"
SIGNATURE_LENGTH: int = 12
MICROSECONDS_PER_SECOND: int = 1_000_000
# version, business uuid, target code, target uuid, expiry (seconds).
PAYLOAD_FORMAT: str = "!B16sB16sI"
PAYLOAD_LENGTH: int = struct.calcsize(PAYLOAD_FORMAT)
NO_TARGET_ID: bytes = bytes(16)
TARGET_CODES: dict[StaffLinkTarget, int] = {
    StaffLinkTarget.CONVERSATION: 1,
    StaffLinkTarget.LEAD: 2,
    StaffLinkTarget.BOOKING: 3,
    StaffLinkTarget.NOTIFICATIONS: 4,
    StaffLinkTarget.REPORT: 5,
}
TARGETS_BY_CODE: dict[int, StaffLinkTarget] = {
    code: target for target, code in TARGET_CODES.items()
}


def derive_link_key(encryption_key: PlatformSecret | None) -> bytes:
    """
    The signing key: from ENCRYPTION_KEY, or a key of this process alone
    when none is set (development: links stop working after a restart).
    """

    if encryption_key is None or str(encryption_key).strip() == "":
        logger.warning(
            "ENCRYPTION_KEY is not set; notification links are signed with a "
            "temporary key and stop working after a restart."
        )
        return secrets.token_bytes(32)

    return hmac.new(
        str(encryption_key).strip().encode("utf-8"), KEY_LABEL, hashlib.sha256
    ).digest()


def uuid_bytes(prefixed_id: str, prefix: str) -> bytes:
    return UUID(prefixed_id.removeprefix(f"{prefix}_")).bytes


class StaffLinkSigner(StaffLinkSignerContract):
    """HMAC-signed link tokens (see the module docstring)."""

    def __init__(
        self,
        encryption_key: PlatformSecret | None,
        previous_keys: Sequence[PlatformSecret] = (),
    ) -> None:
        self._key: bytes = derive_link_key(encryption_key)
        self._verification_keys: list[bytes] = [
            self._key,
            *(derive_link_key(previous_key) for previous_key in previous_keys),
        ]

    def sign(self, claims: StaffLinkClaims) -> StaffLinkToken:
        payload: bytes = struct.pack(
            PAYLOAD_FORMAT,
            TOKEN_VERSION,
            uuid_bytes(str(claims.business_id), BusinessId.prefix),
            TARGET_CODES[claims.target],
            target_id_bytes(claims),
            int(claims.expires_at) // MICROSECONDS_PER_SECOND,
        )
        token: bytes = payload + self._signature(payload)
        return StaffLinkToken(base64.urlsafe_b64encode(token).rstrip(b"=").decode())

    def read(self, token: StaffLinkToken) -> StaffLinkClaims | None:
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

        version, business, code, target_id, expires = struct.unpack(
            PAYLOAD_FORMAT, payload
        )
        target: StaffLinkTarget | None = TARGETS_BY_CODE.get(code)
        if version != TOKEN_VERSION or target is None:
            return None

        return build_claims(
            BusinessId(UUID(bytes=business)),
            target,
            target_id,
            Microseconds(expires * MICROSECONDS_PER_SECOND),
        )

    def _signature(self, payload: bytes) -> bytes:
        return sign_payload(self._key, payload)


def sign_payload(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, payload, hashlib.sha256).digest()[:SIGNATURE_LENGTH]


def target_id_bytes(claims: StaffLinkClaims) -> bytes:
    if claims.target is StaffLinkTarget.CONVERSATION and claims.conversation_id:
        return uuid_bytes(str(claims.conversation_id), ConversationId.prefix)

    if claims.target is StaffLinkTarget.LEAD and claims.lead_id:
        return uuid_bytes(str(claims.lead_id), LeadId.prefix)

    if claims.target is StaffLinkTarget.BOOKING and claims.booking_id:
        return uuid_bytes(str(claims.booking_id), BookingId.prefix)

    if claims.target is StaffLinkTarget.REPORT and claims.value_report_id:
        return uuid_bytes(str(claims.value_report_id), ValueReportId.prefix)

    return NO_TARGET_ID


def build_claims(
    business_id: BusinessId,
    target: StaffLinkTarget,
    target_id: bytes,
    expires_at: Microseconds,
) -> StaffLinkClaims:
    has_id: bool = target_id != NO_TARGET_ID
    identifier: UUID = UUID(bytes=target_id)
    return StaffLinkClaims(
        business_id=business_id,
        target=target,
        conversation_id=(
            ConversationId(identifier)
            if has_id and target is StaffLinkTarget.CONVERSATION
            else None
        ),
        lead_id=(
            LeadId(identifier) if has_id and target is StaffLinkTarget.LEAD else None
        ),
        booking_id=(
            BookingId(identifier)
            if has_id and target is StaffLinkTarget.BOOKING
            else None
        ),
        value_report_id=(
            ValueReportId(identifier)
            if has_id and target is StaffLinkTarget.REPORT
            else None
        ),
        expires_at=expires_at,
    )
