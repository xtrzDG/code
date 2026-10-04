"""
Signed, expiring download links of full business exports
(`/v1/business-exports/{business_id}/{export_id}/download?token=...`).

The token carries the expiry (whole seconds) and a truncated HMAC-SHA256
over the version, the business, the export and the expiry, base64url
without padding. It is the permission itself (the browser downloads the
archive without the cabinet's session), so it names exactly one export of
one business and stops working at its expiry (BUSINESS_EXPORT_LINK_HOURS)
or when its export is purged. The key derives from ENCRYPTION_KEY with its
own label; a link signed with a previous key of the ring still opens until
it expires. Without ENCRYPTION_KEY (development) the key lives in this
process only, so links stop working after a restart.
"""

import base64
import binascii
import hashlib
import hmac
import logging
import secrets
import struct
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.privacy import BusinessExportLinkSignerContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_strings import BusinessExportToken
from app.schemas.typings.privacy.prefixed_id import BusinessExportId

logger: logging.Logger = logging.getLogger(__name__)

TOKEN_VERSION: int = 1
KEY_LABEL: bytes = b"assistant-workshop/business-export-links/v1"
SIGNATURE_LENGTH: int = 20
MICROSECONDS_PER_SECOND: int = 1_000_000
# version, expiry (seconds since 1970).
PAYLOAD_FORMAT: str = "!BQ"
PAYLOAD_LENGTH: int = struct.calcsize(PAYLOAD_FORMAT)


def derive_export_link_key(encryption_key: PlatformSecret | None) -> bytes:
    if encryption_key is None or str(encryption_key).strip() == "":
        logger.warning(
            "ENCRYPTION_KEY is not set; export download links are signed with a "
            "temporary key and stop working after a restart."
        )
        return secrets.token_bytes(32)

    return hmac.new(
        str(encryption_key).strip().encode("utf-8"), KEY_LABEL, hashlib.sha256
    ).digest()


class BusinessExportLinkSigner(BusinessExportLinkSignerContract):
    """HMAC-signed download tokens (see the module docstring)."""

    def __init__(
        self,
        encryption_key: PlatformSecret | None,
        previous_keys: Sequence[PlatformSecret] = (),
    ) -> None:
        self._key: bytes = derive_export_link_key(encryption_key)
        self._verification_keys: list[bytes] = [
            self._key,
            *(derive_export_link_key(previous_key) for previous_key in previous_keys),
        ]

    def sign(
        self,
        business_id: BusinessId,
        export_id: BusinessExportId,
        expires_at: Microseconds,
    ) -> BusinessExportToken:
        payload: bytes = struct.pack(
            PAYLOAD_FORMAT,
            TOKEN_VERSION,
            int(expires_at) // MICROSECONDS_PER_SECOND,
        )
        token: bytes = payload + signature(self._key, business_id, export_id, payload)
        return BusinessExportToken(
            base64.urlsafe_b64encode(token).rstrip(b"=").decode("ascii")
        )

    def expiry_of(
        self,
        business_id: BusinessId,
        export_id: BusinessExportId,
        token: BusinessExportToken,
    ) -> Microseconds | None:
        text: str = str(token)
        try:
            raw: bytes = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        except binascii.Error, ValueError:
            return None

        if len(raw) != PAYLOAD_LENGTH + SIGNATURE_LENGTH:
            return None

        payload, signed = raw[:PAYLOAD_LENGTH], raw[PAYLOAD_LENGTH:]
        if not any(
            hmac.compare_digest(signed, signature(key, business_id, export_id, payload))
            for key in self._verification_keys
        ):
            return None

        version, expires_seconds = struct.unpack(PAYLOAD_FORMAT, payload)
        if version != TOKEN_VERSION:
            return None

        return Microseconds(expires_seconds * MICROSECONDS_PER_SECOND)


def signature(
    key: bytes,
    business_id: BusinessId,
    export_id: BusinessExportId,
    payload: bytes,
) -> bytes:
    message: bytes = f"{business_id}|{export_id}|".encode() + payload
    return hmac.new(key, message, hashlib.sha256).digest()[:SIGNATURE_LENGTH]
