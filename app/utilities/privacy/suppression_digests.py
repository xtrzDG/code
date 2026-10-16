"""
The digests of the suppression list: an HMAC-SHA256 of one customer
identity under the platform's suppression key and the business, so an
entry matches the identity it was made from and reveals nothing about it.

The key is SUPPRESSION_LIST_KEY; without it, it derives from ENCRYPTION_KEY
(with its own label), and without that from a fixed development text, so
the list keeps working across restarts in development.
"""

import hashlib
import hmac
import logging
from uuid import UUID, uuid5

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_strings import SuppressionDigest
from app.schemas.typings.privacy.prefixed_id import SuppressionEntryId

logger: logging.Logger = logging.getLogger(__name__)

KEY_LABEL: bytes = b"assistant-workshop/suppression-list/v1"
DEVELOPMENT_KEY_TEXT: str = "assistant-workshop development suppression key"
# Fixed namespace of the entries' derived ids (never change it).
SUPPRESSION_ENTRY_NAMESPACE: UUID = UUID("3d1f6c2a-9b7e-4c51-8a0d-62e4f1b9c735")


def derive_suppression_key(
    suppression_list_key: PlatformSecret | None,
    encryption_key: PlatformSecret | None,
) -> bytes:
    """The HMAC key of the digests (see the module text for the fallbacks)."""

    if suppression_list_key is not None and str(suppression_list_key).strip():
        source: str = str(suppression_list_key).strip()
    elif encryption_key is not None and str(encryption_key).strip():
        logger.warning(
            "SUPPRESSION_LIST_KEY is not set; the suppression list hashes "
            "under a key derived from ENCRYPTION_KEY, which a key rotation "
            "would change."
        )
        source = str(encryption_key).strip()
    else:
        source = DEVELOPMENT_KEY_TEXT

    return hmac.new(source.encode("utf-8"), KEY_LABEL, hashlib.sha256).digest()


def normalized_identity(identity: SuppressedIdentity) -> str:
    """
    The identity as hashed: a number by its E.164 digits (a WhatsApp
    account is the same number without the plus), an account id as given.
    """

    value: str = str(identity.value).strip()
    if identity.channel in (ChannelKind.PHONE, ChannelKind.WHATSAPP):
        digits: str = "".join(character for character in value if character.isdigit())
        return digits or value

    return value


def suppression_digest(
    key: bytes, business_id: BusinessId, identity: SuppressedIdentity
) -> SuppressionDigest:
    """The digest of one identity in one business."""

    message: str = (
        f"v1|{business_id}|{identity.channel.value}|{normalized_identity(identity)}"
    )
    return SuppressionDigest(
        hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    )


def suppression_entry_id(
    business_id: BusinessId, digest: SuppressionDigest
) -> SuppressionEntryId:
    """One entry per identity and business."""

    return SuppressionEntryId(
        uuid5(SUPPRESSION_ENTRY_NAMESPACE, f"{business_id}|{digest}")
    )
