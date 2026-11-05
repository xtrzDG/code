"""
The derived parts of a passkey: its id from its credential (one
credential is one passkey), the opaque account handle stored with it, and
the name it gets when the person gives none.

The namespace is fixed: stored ids depend on it, never change it.
"""

import base64
from uuid import UUID, uuid5

from app.schemas.typings.passkeys.constrained_strings import (
    PasskeyName,
    WebAuthnCredentialId,
    WebAuthnUserHandle,
)
from app.schemas.typings.passkeys.prefixed_id import PasskeyId
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.user_agents import describe_device

PASSKEY_NAMESPACE: UUID = UUID("7d2c9a4e-3b18-4f6a-9e05-c1a8b74d2f63")
FALLBACK_PASSKEY_NAME: PasskeyName = PasskeyName("Passkey")


def passkey_id_for(credential_id: WebAuthnCredentialId) -> PasskeyId:
    return PasskeyId(uuid5(PASSKEY_NAMESPACE, str(credential_id)))


def user_handle_for(user_id: UserId) -> WebAuthnUserHandle:
    """
    The account handle of a person's passkeys: their user id (random, not
    personal data) as base64url, the same for every passkey of theirs.
    """

    encoded: str = base64.urlsafe_b64encode(str(user_id).encode()).decode()
    return WebAuthnUserHandle(encoded.rstrip("="))


def default_passkey_name(user_agent: SessionUserAgent | None) -> PasskeyName:
    """
    "Chrome · macOS" from the browser that added it (proper names, the
    same in every language); "Passkey" when it names neither.
    """

    device = describe_device(user_agent)
    parts: list[str] = [
        str(part)
        for part in (device.browser, device.operating_system)
        if part is not None
    ]
    if not parts:
        return FALLBACK_PASSKEY_NAME

    return PasskeyName(" · ".join(parts))
