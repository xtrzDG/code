"""
Where a sign-in code went, as the audit log names it: an HMAC-SHA256 of the
phone number or e-mail address under a key derived from ENCRYPTION_KEY
(with its own label), so the failed checks of one destination group
together for the platform alerts while the log never holds the address.
Without ENCRYPTION_KEY (development) a fixed text keys it.
"""

import hashlib
import hmac

from app.schemas.constants.users import LoginMethod
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress

KEY_LABEL: bytes = b"assistant-workshop/audit-login-destinations/v1"
DEVELOPMENT_KEY_TEXT: str = "assistant-workshop development audit key"
DIGEST_PREFIX: str = "dest_"


def derive_destination_key(encryption_key: PlatformSecret | None) -> bytes:
    """The HMAC key of the destination digests."""

    source: str = (
        str(encryption_key).strip()
        if encryption_key is not None and str(encryption_key).strip()
        else DEVELOPMENT_KEY_TEXT
    )
    return hmac.new(source.encode("utf-8"), KEY_LABEL, hashlib.sha256).digest()


def login_destination_digest(
    key: bytes,
    login_method: LoginMethod,
    phone_number: E164PhoneNumber | None,
    email: EmailAddress | None,
) -> AuditEntityReference:
    """The digest of one destination (an e-mail compared without case)."""

    address: str = (
        str(phone_number or "")
        if login_method is LoginMethod.PHONE
        else str(email or "").strip().casefold()
    )
    message: str = f"v1|{login_method.value}|{address}"
    digest: str = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    return AuditEntityReference(f"{DIGEST_PREFIX}{digest[:32]}")
