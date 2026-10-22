"""Secrets sealed with the platform's key ring."""

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.security.totp_secret_cipher_adapter import TotpSecretCipherAdapter
from app.adapters.security.webauthn_passkey_ceremony_adapter import (
    WebAuthnPasskeyCeremonyAdapter,
)
from app.containers.config import ConfigContainer


class SecurityAdaptersContainer(containers.DeclarativeContainer):
    """
    Channel and calendar tokens (and their key rotation), and the secrets of
    people's authenticator apps (two-factor sign-in), each under keys of its
    own derived from the ring; the passkey ceremonies (WEBAUTHN_RP_ID).
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]

    secret_cipher: Singleton[SecretCipherAdapter] = Singleton(
        SecretCipherAdapter,
        app_settings=config.app_settings,
    )
    totp_secret_cipher: Singleton[TotpSecretCipherAdapter] = Singleton(
        TotpSecretCipherAdapter,
        app_settings=config.app_settings,
    )
    passkey_ceremony: Singleton[WebAuthnPasskeyCeremonyAdapter] = Singleton(
        WebAuthnPasskeyCeremonyAdapter,
        app_settings=config.app_settings,
    )
