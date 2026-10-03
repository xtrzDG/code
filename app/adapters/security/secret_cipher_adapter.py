import base64
import logging
import re

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.contracts.secret_cipher import (
    SecretCipherAdapterContract,
    SecretRotationAdapterContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.security.booleans import IsSealedWithCurrentKey
from app.schemas.typings.security.constrained_integers import EncryptionKeyCount

logger: logging.Logger = logging.getLogger(__name__)

FERNET_KEY_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_\-]{43}=$")
FERNET_KEY_BYTES: int = 32
MIN_DERIVED_KEY_TEXT_LENGTH: int = 32
KEY_DERIVATION_INFO: bytes = b"assistant-workshop/channel-secrets/fernet/v1"
# Defaults printed in the repository (docker-compose.yml) for a local run:
# anyone can read them, so production refuses them like a missing key.
PUBLIC_ENCRYPTION_KEYS: frozenset[str] = frozenset(
    {"local-compose-key-for-this-machine-only"}
)


class SecretCipherAdapter(SecretCipherAdapterContract, SecretRotationAdapterContract):
    """
    Encrypt channel and calendar credentials (bot, page and OAuth tokens)
    with Fernet under the platform's key ring.

    Fernet is AES-128-CBC with an HMAC-SHA256 tag, so tampered ciphertext is
    rejected. The ring is ENCRYPTION_KEYS (newest first) followed by
    ENCRYPTION_KEY: new secrets are sealed with the first key, stored ones
    open with any key (MultiFernet), and `rotate` re-seals one with the
    first key, so an old key can be dropped once nothing needs it. A Fernet
    key (`Fernet.generate_key()`) is used as is; any other secret of at
    least 32 characters is stretched into one with HKDF-SHA256. Production
    refuses to start without a key, with the public default of
    docker-compose.yml or with a short secret; development uses a temporary
    key and warns, so secrets stored then do not survive a restart.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        environment: DeploymentEnvironment = app_settings.environment
        keys: list[bytes] = [
            resolve_fernet_key(app_settings.encryption_key, environment),
            *(
                resolve_fernet_key(previous_key, environment)
                for previous_key in app_settings.previous_encryption_keys
            ),
        ]
        self._current: Fernet = Fernet(keys[0])
        self._ring: MultiFernet = MultiFernet([Fernet(key) for key in keys])
        self._key_count: EncryptionKeyCount = EncryptionKeyCount(len(keys))

    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        token: bytes = self._ring.encrypt(str(secret).encode("utf-8"))
        return EncryptedChannelSecret(token.decode("ascii"))

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        try:
            plaintext: bytes = self._ring.decrypt(str(encrypted_secret))
            return ChannelSecret(plaintext.decode("utf-8"))
        except (InvalidToken, ValueError, TypeError) as error:
            raise unreadable_secret() from error

    def key_count(self) -> EncryptionKeyCount:
        return self._key_count

    def is_current(
        self, encrypted_secret: EncryptedChannelSecret
    ) -> IsSealedWithCurrentKey:
        try:
            self._current.decrypt(str(encrypted_secret))
        except InvalidToken, ValueError, TypeError:
            return False

        return True

    def rotate(
        self, encrypted_secret: EncryptedChannelSecret
    ) -> EncryptedChannelSecret:
        try:
            token: bytes = self._ring.rotate(str(encrypted_secret).encode("ascii"))
        except (InvalidToken, ValueError, TypeError) as error:
            raise unreadable_secret() from error

        return EncryptedChannelSecret(token.decode("ascii"))


def unreadable_secret() -> ValidationFailedError:
    return ValidationFailedError(
        "The stored channel secret cannot be decrypted with any key of "
        "ENCRYPTION_KEYS / ENCRYPTION_KEY; reconnect the channel."
    )


def resolve_fernet_key(
    encryption_key: PlatformSecret | None,
    environment: DeploymentEnvironment,
) -> bytes:
    """Return the Fernet key for the configured secret (see the class doc)."""

    is_production: bool = environment is DeploymentEnvironment.PRODUCTION
    secret_text: str = "" if encryption_key is None else encryption_key.strip()
    if secret_text == "":
        if is_production:
            raise ValidationFailedError(
                "ENCRYPTION_KEY must be set in production to store channel "
                "credentials encrypted."
            )

        logger.warning(
            "ENCRYPTION_KEY is not set; channel secrets are encrypted with a "
            "temporary key and become unreadable after a restart."
        )
        return Fernet.generate_key()

    if is_production and secret_text in PUBLIC_ENCRYPTION_KEYS:
        raise ValidationFailedError(
            "ENCRYPTION_KEY is the public default of docker-compose.yml; set your "
            "own key in .env for production."
        )

    if FERNET_KEY_PATTERN.fullmatch(secret_text) is not None:
        return secret_text.encode("ascii")

    if len(secret_text) < MIN_DERIVED_KEY_TEXT_LENGTH:
        if is_production:
            raise ValidationFailedError(
                f"ENCRYPTION_KEY must be a Fernet key or a secret of at least "
                f"{MIN_DERIVED_KEY_TEXT_LENGTH} characters in production."
            )

        logger.warning(
            "ENCRYPTION_KEY is shorter than %s characters; use a Fernet key or a "
            "long random secret outside development.",
            MIN_DERIVED_KEY_TEXT_LENGTH,
        )

    derived_key: bytes = HKDF(
        algorithm=hashes.SHA256(),
        length=FERNET_KEY_BYTES,
        salt=None,
        info=KEY_DERIVATION_INFO,
    ).derive(secret_text.encode("utf-8"))
    return base64.urlsafe_b64encode(derived_key)
