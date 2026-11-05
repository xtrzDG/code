"""
Passkeys (WebAuthn): a person's phishing-resistant second factor and the
challenges of its ceremonies (platform-wide collections, migration 1201).
"""

from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.passkeys import PasskeyCeremonyPurpose, WebAuthnTransport
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId
from app.schemas.typings.passkeys.booleans import (
    IsPasskeyBackedUp,
    IsPasskeyChallengeConsumed,
    IsPasskeySynced,
)
from app.schemas.typings.passkeys.constrained_integers import WebAuthnSignCount
from app.schemas.typings.passkeys.constrained_strings import (
    PasskeyName,
    WebAuthnAaguid,
    WebAuthnChallenge,
    WebAuthnCredentialId,
    WebAuthnPublicKey,
)
from app.schemas.typings.passkeys.prefixed_id import PasskeyChallengeId, PasskeyId
from app.schemas.typings.users.prefixed_id import UserId


class PasskeyDocument(BaseDocument):
    """
    One passkey of a person: the credential id their authenticator gave
    it, its public key (not secret), the signature counter it last
    reported, and how the browser reaches it (`transports`). It signs
    the second step of a sign-in and step-up confirmations; it never
    replaces the login code.

    `sign_count` only grows: a use that reports a counter not above the
    stored one comes from a copied authenticator, is refused and marks
    the passkey `clone_suspected_at`; such a passkey signs nothing more
    until the person removes it. Synced passkeys (`is_synced`, kept by a
    password manager or a platform account) report 0 on every use.
    """

    id: PasskeyId
    user_id: UserId
    credential_id: WebAuthnCredentialId
    public_key: WebAuthnPublicKey
    sign_count: WebAuthnSignCount = WebAuthnSignCount(0)
    transports: list[WebAuthnTransport] = Field(default_factory=list[WebAuthnTransport])
    aaguid: WebAuthnAaguid | None = None
    name: PasskeyName
    is_synced: IsPasskeySynced = False
    is_backed_up: IsPasskeyBackedUp = False
    last_used_at: Microseconds | None = None
    clone_suspected_at: Microseconds | None = None


class PasskeyChallengeDocument(BaseDocument):
    """
    The random challenge of one passkey ceremony of one person, for one
    purpose. It lives five minutes and is consumed by compare-and-swap,
    so a signed answer counts once. A sign-in's challenge names its
    second step (`mfa_challenge_id`).
    """

    id: PasskeyChallengeId = Field(default_factory=PasskeyChallengeId)
    user_id: UserId
    purpose: PasskeyCeremonyPurpose
    challenge: WebAuthnChallenge
    mfa_challenge_id: MfaChallengeId | None = None
    expires_at: Microseconds
    is_consumed: IsPasskeyChallengeConsumed = False
