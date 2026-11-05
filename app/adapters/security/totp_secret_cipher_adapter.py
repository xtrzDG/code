import base64

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.adapters.security.secret_cipher_adapter import resolve_fernet_key
from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.schemas.typings.mfa.strings import SealedTotpSecret
from app.schemas.typings.security.booleans import IsSealedWithCurrentKey

TOTP_KEY_DERIVATION_INFO: bytes = b"assistant-workshop/totp-secrets/fernet/v1"
FERNET_KEY_BYTES: int = 32


class TotpSecretCipherAdapter(TotpSecretCipherAdapterContract):
    """
    Seal authenticator secrets with Fernet under the platform's key ring.

    Every key of the ring (ENCRYPTION_KEYS, then ENCRYPTION_KEY, resolved as
    for channel secrets) is stretched with HKDF-SHA256 and a label of its
    own, so authenticator secrets never share a key with channel tokens.
    New secrets are sealed with the first key and open with any, and
    `reseal` moves one to the first key (the key rotation job does it for
    every factor), so an old key can be dropped once nothing needs it.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        ring_keys: list[bytes] = [
            derive_totp_key(resolve_fernet_key(key, app_settings.environment))
            for key in [
                app_settings.encryption_key,
                *app_settings.previous_encryption_keys,
            ]
        ]
        self._current: Fernet = Fernet(ring_keys[0])
        self._ring: MultiFernet = MultiFernet([Fernet(key) for key in ring_keys])

    def seal(self, secret: TotpSecret) -> SealedTotpSecret:
        token: bytes = self._ring.encrypt(str(secret).encode("ascii"))
        return SealedTotpSecret(token.decode("ascii"))

    def open(self, sealed_secret: SealedTotpSecret) -> TotpSecret:
        try:
            plaintext: bytes = self._ring.decrypt(str(sealed_secret))
        except (InvalidToken, ValueError, TypeError) as error:
            raise unreadable_totp_secret() from error

        return TotpSecret(plaintext.decode("ascii"))

    def is_current(self, sealed_secret: SealedTotpSecret) -> IsSealedWithCurrentKey:
        try:
            self._current.decrypt(str(sealed_secret))
        except InvalidToken, ValueError, TypeError:
            return False

        return True

    def reseal(self, sealed_secret: SealedTotpSecret) -> SealedTotpSecret:
        try:
            token: bytes = self._ring.rotate(str(sealed_secret).encode("ascii"))
        except (InvalidToken, ValueError, TypeError) as error:
            raise unreadable_totp_secret() from error

        return SealedTotpSecret(token.decode("ascii"))


def derive_totp_key(fernet_key: bytes) -> bytes:
    """A Fernet key of its own for authenticator secrets, from a ring key."""

    derived: bytes = HKDF(
        algorithm=hashes.SHA256(),
        length=FERNET_KEY_BYTES,
        salt=None,
        info=TOTP_KEY_DERIVATION_INFO,
    ).derive(base64.urlsafe_b64decode(fernet_key))
    return base64.urlsafe_b64encode(derived)


def unreadable_totp_secret() -> ValidationFailedError:
    return ValidationFailedError(
        "The stored authenticator secret cannot be opened with any key of "
        "ENCRYPTION_KEYS / ENCRYPTION_KEY; sign in with a recovery code and "
        "set up the authenticator again."
    )
