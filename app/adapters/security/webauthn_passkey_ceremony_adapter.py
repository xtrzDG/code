"""Passkey ceremonies checked with py_webauthn (no attestation asked for)."""

import secrets
from collections.abc import Sequence

from webauthn import verify_authentication_response, verify_registration_response
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticationCredential,
    AuthenticatorAssertionResponse,
    AuthenticatorAttestationResponse,
    CredentialDeviceType,
    RegistrationCredential,
)

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.passkeys import (
    WebAuthnResidentKey,
    WebAuthnTransport,
    WebAuthnUserVerification,
)
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.dto.passkey_ceremonies import (
    PasskeyAssertionCredential,
    PasskeyCreationOptionsView,
    PasskeyDescriptorView,
    PasskeyRegistrationCredential,
    PasskeyRelyingPartyView,
    PasskeyRequestOptionsView,
    PasskeyUserView,
)
from app.schemas.dto.passkey_checks import CheckedAssertion, CheckedRegistration
from app.schemas.typings.passkeys.booleans import ArePasskeysAvailable
from app.schemas.typings.passkeys.constrained_integers import (
    PasskeyCeremonyTimeoutMilliseconds,
    WebAuthnCoseAlgorithm,
    WebAuthnSignCount,
)
from app.schemas.typings.passkeys.constrained_strings import (
    RawWebAuthnTransport,
    WebAuthnAaguid,
    WebAuthnChallenge,
    WebAuthnCredentialId,
    WebAuthnPublicKey,
    WebAuthnRelyingPartyId,
)
from app.schemas.typings.passkeys.strings import (
    PasskeyAccountName,
    WebAuthnRelyingPartyName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.passkey_identity import user_handle_for
from app.utilities.security.passkey_policy import passkey_rejected, passkeys_unavailable
from app.utilities.security.webauthn_relying_party import cabinet_origin

CHALLENGE_BYTES: int = 32
CEREMONY_TIMEOUT: PasskeyCeremonyTimeoutMilliseconds = (
    PasskeyCeremonyTimeoutMilliseconds(120_000)
)
# EdDSA, ES256 and RS256: every passkey provider signs with one of them.
ALGORITHMS: tuple[COSEAlgorithmIdentifier, ...] = (
    COSEAlgorithmIdentifier.EDDSA,
    COSEAlgorithmIdentifier.ECDSA_SHA_256,
    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
)
UNKNOWN_AAGUID: str = "00000000-0000-0000-0000-000000000000"
KNOWN_TRANSPORTS: frozenset[str] = frozenset(item.value for item in WebAuthnTransport)


class WebAuthnPasskeyCeremonyAdapter(PasskeyCeremonyAdapterContract):
    """
    Passkeys of the relying party `sessions.webauthn_rp_id`, answered from
    the cabinet's origin (CABINET_BASE_URL) only. A passkey is a second
    factor after the login code, so the authenticator must show the
    person was present; checking who it is (fingerprint, PIN) is preferred,
    not required. No attestation is asked for: any authenticator will do.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._rp_id: WebAuthnRelyingPartyId | None = (
            app_settings.sessions.webauthn_rp_id
        )
        self._origin: str | None = cabinet_origin(app_settings.cabinet_base_url)
        self._rp_name: WebAuthnRelyingPartyName = WebAuthnRelyingPartyName(
            str(app_settings.mfa_issuer_name)
        )

    def is_available(self) -> ArePasskeysAvailable:
        return self._rp_id is not None and self._origin is not None

    def new_challenge(self) -> WebAuthnChallenge:
        return WebAuthnChallenge(
            bytes_to_base64url(secrets.token_bytes(CHALLENGE_BYTES))
        )

    def creation_options(
        self,
        user_id: UserId,
        account_name: PasskeyAccountName,
        challenge: WebAuthnChallenge,
        existing: Sequence[PasskeyDocument],
    ) -> PasskeyCreationOptionsView:
        rp_id, _ = self._relying_party()
        return PasskeyCreationOptionsView(
            rp=PasskeyRelyingPartyView(id=rp_id, name=self._rp_name),
            user=PasskeyUserView(
                id=user_handle_for(user_id),
                name=account_name,
                display_name=account_name,
            ),
            challenge=challenge,
            algorithms=[WebAuthnCoseAlgorithm(int(item)) for item in ALGORITHMS],
            timeout_ms=CEREMONY_TIMEOUT,
            exclude_credentials=[describe(passkey) for passkey in existing],
            resident_key=WebAuthnResidentKey.PREFERRED,
            user_verification=WebAuthnUserVerification.PREFERRED,
        )

    def request_options(
        self,
        challenge: WebAuthnChallenge,
        passkeys: Sequence[PasskeyDocument],
    ) -> PasskeyRequestOptionsView:
        rp_id, _ = self._relying_party()
        return PasskeyRequestOptionsView(
            rp_id=rp_id,
            challenge=challenge,
            timeout_ms=CEREMONY_TIMEOUT,
            allow_credentials=[describe(passkey) for passkey in passkeys],
            user_verification=WebAuthnUserVerification.PREFERRED,
        )

    def check_registration(
        self,
        credential: PasskeyRegistrationCredential,
        challenge: WebAuthnChallenge,
    ) -> CheckedRegistration:
        rp_id, origin = self._relying_party()
        try:
            verified = verify_registration_response(
                credential=RegistrationCredential(
                    id=str(credential.id),
                    raw_id=base64url_to_bytes(str(credential.raw_id)),
                    response=AuthenticatorAttestationResponse(
                        client_data_json=base64url_to_bytes(
                            str(credential.response.client_data_json)
                        ),
                        attestation_object=base64url_to_bytes(
                            str(credential.response.attestation_object)
                        ),
                    ),
                ),
                expected_challenge=base64url_to_bytes(str(challenge)),
                expected_rp_id=str(rp_id),
                expected_origin=origin,
                supported_pub_key_algs=list(ALGORITHMS),
            )
            return CheckedRegistration(
                credential_id=WebAuthnCredentialId(
                    bytes_to_base64url(verified.credential_id)
                ),
                public_key=WebAuthnPublicKey(
                    bytes_to_base64url(verified.credential_public_key)
                ),
                sign_count=WebAuthnSignCount(verified.sign_count),
                aaguid=None
                if verified.aaguid == UNKNOWN_AAGUID
                else WebAuthnAaguid(verified.aaguid),
                transports=known_transports(credential.response.transports),
                is_synced=verified.credential_device_type
                is CredentialDeviceType.MULTI_DEVICE,
                is_backed_up=verified.credential_backed_up,
            )
        except (WebAuthnException, ValueError, KeyError, TypeError) as error:
            raise passkey_rejected() from error

    def check_assertion(
        self,
        credential: PasskeyAssertionCredential,
        challenge: WebAuthnChallenge,
        passkey: PasskeyDocument,
    ) -> CheckedAssertion:
        rp_id, origin = self._relying_party()
        if credential.id != passkey.credential_id:
            raise passkey_rejected()

        response = credential.response
        try:
            verified = verify_authentication_response(
                credential=AuthenticationCredential(
                    id=str(credential.id),
                    raw_id=base64url_to_bytes(str(credential.raw_id)),
                    response=AuthenticatorAssertionResponse(
                        client_data_json=base64url_to_bytes(
                            str(response.client_data_json)
                        ),
                        authenticator_data=base64url_to_bytes(
                            str(response.authenticator_data)
                        ),
                        signature=base64url_to_bytes(str(response.signature)),
                        user_handle=None
                        if response.user_handle is None
                        else base64url_to_bytes(str(response.user_handle)),
                    ),
                ),
                expected_challenge=base64url_to_bytes(str(challenge)),
                expected_rp_id=str(rp_id),
                expected_origin=origin,
                credential_public_key=base64url_to_bytes(str(passkey.public_key)),
                # The counter is judged by the caller against the stored one
                # (passkey_policy.is_sign_count_regressed), after the
                # signature proved the answer came from this passkey's key.
                credential_current_sign_count=0,
            )
        except (WebAuthnException, ValueError, KeyError, TypeError) as error:
            raise passkey_rejected() from error

        return CheckedAssertion(
            credential_id=passkey.credential_id,
            sign_count=WebAuthnSignCount(verified.new_sign_count),
        )

    def _relying_party(self) -> tuple[WebAuthnRelyingPartyId, str]:
        if self._rp_id is None or self._origin is None:
            raise passkeys_unavailable()

        return self._rp_id, self._origin


def describe(passkey: PasskeyDocument) -> PasskeyDescriptorView:
    return PasskeyDescriptorView(
        id=passkey.credential_id, transports=passkey.transports
    )


def known_transports(
    reported: Sequence[RawWebAuthnTransport],
) -> list[WebAuthnTransport]:
    """The transports the browser reported that this release knows, once each."""

    known: list[WebAuthnTransport] = []
    for name in reported:
        if str(name) in KNOWN_TRANSPORTS and WebAuthnTransport(str(name)) not in known:
            known.append(WebAuthnTransport(str(name)))
    return known
