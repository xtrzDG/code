"""The WebAuthn ceremonies of passkeys: their options and the checks of answers."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.dto.passkey_ceremonies import (
    PasskeyAssertionCredential,
    PasskeyCreationOptionsView,
    PasskeyRegistrationCredential,
    PasskeyRequestOptionsView,
)
from app.schemas.dto.passkey_checks import CheckedAssertion, CheckedRegistration
from app.schemas.typings.passkeys.booleans import ArePasskeysAvailable
from app.schemas.typings.passkeys.constrained_strings import WebAuthnChallenge
from app.schemas.typings.passkeys.strings import PasskeyAccountName
from app.schemas.typings.users.prefixed_id import UserId


class PasskeyCeremonyAdapterContract(AdapterContract, Protocol):
    """
    Passkeys are bound to the relying party (WEBAUTHN_RP_ID) and answered
    only from the cabinet's origin (CABINET_BASE_URL). Without both, the
    server offers no passkeys (`is_available` False) and every ceremony is
    refused with PasskeysUnavailableError.
    """

    def is_available(self) -> ArePasskeysAvailable:
        raise NotImplementedError

    def new_challenge(self) -> WebAuthnChallenge:
        """32 random bytes for one ceremony."""
        raise NotImplementedError

    def creation_options(
        self,
        user_id: UserId,
        account_name: PasskeyAccountName,
        challenge: WebAuthnChallenge,
        existing: Sequence[PasskeyDocument],
    ) -> PasskeyCreationOptionsView:
        raise NotImplementedError

    def request_options(
        self,
        challenge: WebAuthnChallenge,
        passkeys: Sequence[PasskeyDocument],
    ) -> PasskeyRequestOptionsView:
        raise NotImplementedError

    def check_registration(
        self,
        credential: PasskeyRegistrationCredential,
        challenge: WebAuthnChallenge,
    ) -> CheckedRegistration:
        """
        Check a new passkey's attestation against the challenge, the
        relying party and the cabinet's origin (user presence required).

        Raises:
            PasskeyRejectedError: it does not check out.
        """
        raise NotImplementedError

    def check_assertion(
        self,
        credential: PasskeyAssertionCredential,
        challenge: WebAuthnChallenge,
        passkey: PasskeyDocument,
    ) -> CheckedAssertion:
        """
        Check a passkey's signature against the challenge, the relying
        party, the cabinet's origin and the stored public key. The counter
        it reports is returned, not judged: the caller compares it with the
        stored one (a copied authenticator).

        Raises:
            PasskeyRejectedError: the signature or the data do not check out.
        """
        raise NotImplementedError
