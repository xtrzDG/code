"""What a checked passkey ceremony yields (internal, never sent to the cabinet)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.passkeys import WebAuthnTransport
from app.schemas.typings.passkeys.booleans import IsPasskeyBackedUp, IsPasskeySynced
from app.schemas.typings.passkeys.constrained_integers import WebAuthnSignCount
from app.schemas.typings.passkeys.constrained_strings import (
    WebAuthnAaguid,
    WebAuthnCredentialId,
    WebAuthnPublicKey,
)


class CheckedRegistration(ImmutableDTO):
    """A new passkey whose attestation checked out."""

    credential_id: WebAuthnCredentialId
    public_key: WebAuthnPublicKey
    sign_count: WebAuthnSignCount
    aaguid: WebAuthnAaguid | None = None
    transports: list[WebAuthnTransport] = Field(default_factory=list[WebAuthnTransport])
    is_synced: IsPasskeySynced = False
    is_backed_up: IsPasskeyBackedUp = False


class CheckedAssertion(ImmutableDTO):
    """A passkey signature that checked out, and the counter it reported."""

    credential_id: WebAuthnCredentialId
    sign_count: WebAuthnSignCount
