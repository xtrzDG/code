"""
Signed, expiring tickets of the website chat's live stream
(`GET /v1/widget/{id}/events?ticket=...`).

EventSource cannot send headers, so the stream's address carries a ticket
instead of the visitor key: the business, the visitor (`WidgetVisitorId`,
one-way from the key) and the expiry (whole seconds), followed by a
truncated HMAC-SHA256 over them, base64url without padding (66
characters). Nothing is stored. A ticket lets its holder hear when the
visitor's answers are ready until it expires; reading the conversation
still needs the key itself. The key derives from ENCRYPTION_KEY with its
own label; after a rotation a ticket signed with a previous key still
opens until it expires.
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

from app.contracts.widget_streams import WidgetStreamTicketSignerContract
from app.schemas.dto.channels.widget_streams import WidgetStreamClaims
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.platform.strings import PlatformSecret

logger: logging.Logger = logging.getLogger(__name__)

TICKET_VERSION: int = 1
KEY_LABEL: bytes = b"assistant-workshop/widget-stream-tickets/v1"
SIGNATURE_LENGTH: int = 12
MICROSECONDS_PER_SECOND: int = 1_000_000
# version, business uuid, visitor uuid, expiry (seconds).
PAYLOAD_FORMAT: str = "!B16s16sI"
PAYLOAD_LENGTH: int = struct.calcsize(PAYLOAD_FORMAT)
LARGEST_SECONDS: int = 2**32 - 1


def derive_ticket_key(encryption_key: PlatformSecret | None) -> bytes:
    """
    The signing key: from ENCRYPTION_KEY, or a key of this process alone
    when none is set (development: open widgets get a new ticket with
    their next answer after a restart).
    """

    if encryption_key is None or str(encryption_key).strip() == "":
        logger.warning(
            "ENCRYPTION_KEY is not set; website chat stream tickets are signed "
            "with a temporary key of this process."
        )
        return secrets.token_bytes(32)

    return hmac.new(
        str(encryption_key).strip().encode("utf-8"), KEY_LABEL, hashlib.sha256
    ).digest()


class WidgetStreamTicketSigner(WidgetStreamTicketSignerContract):
    """HMAC-signed stream tickets (see the module docstring)."""

    def __init__(
        self,
        encryption_key: PlatformSecret | None,
        previous_keys: Sequence[PlatformSecret] = (),
    ) -> None:
        self._key: bytes = derive_ticket_key(encryption_key)
        self._verification_keys: list[bytes] = [
            self._key,
            *(derive_ticket_key(previous_key) for previous_key in previous_keys),
        ]

    def sign(self, claims: WidgetStreamClaims) -> WidgetStreamTicket:
        payload: bytes = struct.pack(
            PAYLOAD_FORMAT,
            TICKET_VERSION,
            uuid_bytes(str(claims.business_id), BusinessId.prefix),
            uuid_bytes(str(claims.visitor_id), WidgetVisitorId.prefix),
            min(int(claims.expires_at) // MICROSECONDS_PER_SECOND, LARGEST_SECONDS),
        )
        ticket: bytes = payload + sign_payload(self._key, payload)
        return WidgetStreamTicket(
            base64.urlsafe_b64encode(ticket).rstrip(b"=").decode()
        )

    def read(self, ticket: WidgetStreamTicket) -> WidgetStreamClaims | None:
        text: str = str(ticket)
        try:
            raw: bytes = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        except binascii.Error, ValueError:
            return None

        if len(raw) != PAYLOAD_LENGTH + SIGNATURE_LENGTH:
            return None

        # Only the one spelling this signer writes (see the manage links).
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != text:
            return None

        payload, signature = raw[:PAYLOAD_LENGTH], raw[PAYLOAD_LENGTH:]
        if not any(
            hmac.compare_digest(signature, sign_payload(key, payload))
            for key in self._verification_keys
        ):
            return None

        version, business, visitor, expires = struct.unpack(PAYLOAD_FORMAT, payload)
        if version != TICKET_VERSION:
            return None

        return WidgetStreamClaims(
            business_id=BusinessId(UUID(bytes=business)),
            visitor_id=WidgetVisitorId(UUID(bytes=visitor)),
            expires_at=Microseconds(expires * MICROSECONDS_PER_SECOND),
        )


def sign_payload(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, payload, hashlib.sha256).digest()[:SIGNATURE_LENGTH]


def uuid_bytes(prefixed_id: str, prefix: str) -> bytes:
    return UUID(prefixed_id.removeprefix(f"{prefix}_")).bytes
