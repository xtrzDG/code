"""
Passkeys of the signed-in person (Account → Security), and the passkey
ceremonies of a sign-in's second step, an admin's first factor at
sign-in and the step-up confirmation.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.passkeys import WebAuthnTransport
from app.schemas.dto.passkey_ceremonies import (
    PasskeyAssertionCredential,
    PasskeyCreationOptionsView,
    PasskeyRegistrationCredential,
    PasskeyRequestOptionsView,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId
from app.schemas.typings.passkeys.booleans import (
    ArePasskeysAvailable,
    IsPasskeyBackedUp,
    IsPasskeyRecommended,
    IsPasskeySynced,
)
from app.schemas.typings.passkeys.constrained_strings import PasskeyName
from app.schemas.typings.passkeys.prefixed_id import PasskeyChallengeId, PasskeyId
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.prefixed_id import UserId


class PasskeyView(ImmutableDTO):
    """
    One passkey in the person's list: its name, when it was added and last
    used, whether a password manager or platform account keeps it in sync,
    and `clone_suspected_at` when a copy of its authenticator was used (it
    signs nothing more; remove it and add a new one).
    """

    id: PasskeyId
    name: PasskeyName
    created_at: Microseconds
    last_used_at: Microseconds | None = None
    is_synced: IsPasskeySynced = False
    is_backed_up: IsPasskeyBackedUp = False
    transports: list[WebAuthnTransport] = Field(default_factory=list[WebAuthnTransport])
    clone_suspected_at: Microseconds | None = None


class PasskeyListView(ImmutableDTO):
    """
    The person's passkeys, newest first. `is_available`: the server is
    set up for passkeys (WEBAUTHN_RP_ID); `is_recommended`: a platform
    admin without one, who should add one.
    """

    items: list[PasskeyView] = Field(default_factory=list[PasskeyView])
    is_available: ArePasskeysAvailable
    is_recommended: IsPasskeyRecommended = False


class PasskeyCommand(ImmutableDTO):
    """Start adding a passkey, or a step-up with one."""

    user_id: UserId
    client_ip_address: ClientIpAddress | None = None


class PasskeyRegistrationView(ImmutableDTO):
    """
    The options of a new passkey for `navigator.credentials.create()`;
    the answer goes back with `passkey_challenge_id` within five minutes.
    """

    passkey_challenge_id: PasskeyChallengeId
    options: PasskeyCreationOptionsView


class FinishPasskeyRegistrationRequest(ImmutableDTO):
    """
    The credential the browser created, and the name the person gave it
    (none: named after the browser and system that added it).
    """

    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyRegistrationCredential
    name: PasskeyName | None = None


class FinishPasskeyRegistrationCommand(ImmutableDTO):
    user_id: UserId
    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyRegistrationCredential
    name: PasskeyName | None = None
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None


class PasskeyAddedView(ImmutableDTO):
    """
    The new passkey; with the person's first second factor, a new set of
    recovery codes too (shown once).
    """

    passkey: PasskeyView
    recovery_codes: list[RecoveryCode] = Field(default_factory=list[RecoveryCode])


class RenamePasskeyRequest(ImmutableDTO):
    """
    A new name for a passkey.

    Example: {"name": "Work laptop"}.
    """

    name: PasskeyName


class RenamePasskeyCommand(ImmutableDTO):
    user_id: UserId
    passkey_id: PasskeyId
    name: PasskeyName


class RemovePasskeyCommand(ImmutableDTO):
    user_id: UserId
    passkey_id: PasskeyId
    client_ip_address: ClientIpAddress | None = None


class PasskeyAssertionOptionsView(ImmutableDTO):
    """
    The options of `navigator.credentials.get()` for a sign-in step or a
    step-up; the answer goes back with `passkey_challenge_id`.
    """

    passkey_challenge_id: PasskeyChallengeId
    options: PasskeyRequestOptionsView


class PasskeySignInStepRequest(ImmutableDTO):
    """
    The second step of a sign-in asks for passkey options.

    Example: {"mfa_challenge_id": "mfa_challenge_..."}.
    """

    mfa_challenge_id: MfaChallengeId


class PasskeySignInStepCommand(ImmutableDTO):
    mfa_challenge_id: MfaChallengeId
    client_ip_address: ClientIpAddress | None = None


class VerifyPasskeySignInRequest(ImmutableDTO):
    """The passkey's answer to the second step of a sign-in."""

    mfa_challenge_id: MfaChallengeId
    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyAssertionCredential


class VerifyPasskeySignInCommand(ImmutableDTO):
    mfa_challenge_id: MfaChallengeId
    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyAssertionCredential
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None


class FinishPasskeyEnrollmentRequest(ImmutableDTO):
    """
    A platform admin without a second factor adds a passkey while signing
    in: the created credential and an optional name.
    """

    mfa_challenge_id: MfaChallengeId
    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyRegistrationCredential
    name: PasskeyName | None = None


class FinishPasskeyEnrollmentCommand(ImmutableDTO):
    mfa_challenge_id: MfaChallengeId
    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyRegistrationCredential
    name: PasskeyName | None = None
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None


class VerifyPasskeyStepUpRequest(ImmutableDTO):
    """The passkey's answer to a step-up."""

    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyAssertionCredential


class VerifyPasskeyStepUpCommand(ImmutableDTO):
    user_id: UserId
    passkey_challenge_id: PasskeyChallengeId
    credential: PasskeyAssertionCredential
    client_ip_address: ClientIpAddress | None = None
