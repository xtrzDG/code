"""
The two halves of a passkey ceremony as they cross the API: the options
the browser passes to `navigator.credentials.create()` or `.get()`, and
the credential it answers with. Binary values travel as unpadded
base64url; field names follow the API (snake_case), and the cabinet maps
them onto the WebAuthn dictionaries.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.passkeys import (
    WebAuthnResidentKey,
    WebAuthnTransport,
    WebAuthnUserVerification,
)
from app.schemas.typings.passkeys.constrained_integers import (
    PasskeyCeremonyTimeoutMilliseconds,
    WebAuthnCoseAlgorithm,
)
from app.schemas.typings.passkeys.constrained_strings import (
    RawWebAuthnTransport,
    WebAuthnAttestationObject,
    WebAuthnAuthenticatorData,
    WebAuthnChallenge,
    WebAuthnClientDataJson,
    WebAuthnCredentialId,
    WebAuthnRelyingPartyId,
    WebAuthnSignature,
    WebAuthnUserHandle,
)
from app.schemas.typings.passkeys.strings import (
    PasskeyAccountName,
    WebAuthnRelyingPartyName,
)


class PasskeyDescriptorView(ImmutableDTO):
    """A passkey the browser should offer (or must not create again)."""

    id: WebAuthnCredentialId
    transports: list[WebAuthnTransport] = Field(default_factory=list[WebAuthnTransport])


class PasskeyRelyingPartyView(ImmutableDTO):
    """The service passkeys are bound to: its domain and the name shown."""

    id: WebAuthnRelyingPartyId
    name: WebAuthnRelyingPartyName


class PasskeyUserView(ImmutableDTO):
    """
    The account a new passkey belongs to: an opaque handle derived from
    the user's id and the e-mail or phone number the authenticator shows.
    """

    id: WebAuthnUserHandle
    name: PasskeyAccountName
    display_name: PasskeyAccountName


class PasskeyCreationOptionsView(ImmutableDTO):
    """
    `PublicKeyCredentialCreationOptions` of a new passkey: no attestation
    is asked for, a discoverable passkey is preferred, and the person's
    passkeys are excluded so an authenticator is not added twice.
    """

    rp: PasskeyRelyingPartyView
    user: PasskeyUserView
    challenge: WebAuthnChallenge
    algorithms: list[WebAuthnCoseAlgorithm]
    timeout_ms: PasskeyCeremonyTimeoutMilliseconds
    exclude_credentials: list[PasskeyDescriptorView] = Field(
        default_factory=list[PasskeyDescriptorView]
    )
    resident_key: WebAuthnResidentKey
    user_verification: WebAuthnUserVerification


class PasskeyRequestOptionsView(ImmutableDTO):
    """
    `PublicKeyCredentialRequestOptions` of a sign-in step or a step-up:
    only the person's own passkeys are allowed.
    """

    rp_id: WebAuthnRelyingPartyId
    challenge: WebAuthnChallenge
    timeout_ms: PasskeyCeremonyTimeoutMilliseconds
    allow_credentials: list[PasskeyDescriptorView] = Field(
        default_factory=list[PasskeyDescriptorView]
    )
    user_verification: WebAuthnUserVerification


class PasskeyAttestationResponse(ImmutableDTO):
    """`AuthenticatorAttestationResponse` of a new passkey."""

    client_data_json: WebAuthnClientDataJson
    attestation_object: WebAuthnAttestationObject
    transports: list[RawWebAuthnTransport] = Field(
        default_factory=list[RawWebAuthnTransport], max_length=10
    )


class PasskeyRegistrationCredential(ImmutableDTO):
    """
    The `PublicKeyCredential` a browser created: `id` and `raw_id` are the
    same credential id.

    Example: {"id": "AbC...", "raw_id": "AbC...", "response":
    {"client_data_json": "eyJ0...", "attestation_object": "o2Nm...",
    "transports": ["internal", "hybrid"]}}.
    """

    id: WebAuthnCredentialId
    raw_id: WebAuthnCredentialId
    response: PasskeyAttestationResponse


class PasskeyAssertionResponse(ImmutableDTO):
    """`AuthenticatorAssertionResponse`: what the passkey signed, and the signature."""

    client_data_json: WebAuthnClientDataJson
    authenticator_data: WebAuthnAuthenticatorData
    signature: WebAuthnSignature
    user_handle: WebAuthnUserHandle | None = None


class PasskeyAssertionCredential(ImmutableDTO):
    """
    The `PublicKeyCredential` a browser answered a sign-in step or a
    step-up with.

    Example: {"id": "AbC...", "raw_id": "AbC...", "response":
    {"client_data_json": "eyJ0...", "authenticator_data": "SZYN...",
    "signature": "MEUC..."}}.
    """

    id: WebAuthnCredentialId
    raw_id: WebAuthnCredentialId
    response: PasskeyAssertionResponse
