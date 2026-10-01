import base64
import logging
import re

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret

logger: logging.Logger = logging.getLogger(__name__)

FERNET_KEY_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_\-]{43}=$")
FERNET_KEY_BYTES: int = 32
MIN_DERIVED_SECRET_LENGTH: int = 32
KEY_DERIVATION_INFO: bytes = b"assistant-workshop/channel-secrets/fernet/v1"


class SecretCipherAdapter(SecretCipherAdapterContract):
    """
    Encrypt channel credentials (bot and page tokens) with Fernet.

    Fernet is AES-128-CBC with an HMAC-SHA256 tag, so tampered ciphertext is
    rejected. The key comes from `ENCRYPTION_KEY`: a Fernet key
    (`Fernet.generate_key()`) is used as is; any other secret of at least 32
    characters is stretched into one with HKDF-SHA256. Production refuses to
    start without a key; development uses a temporary key and warns, so
    secrets stored then do not survive a restart.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._fernet: Fernet = Fernet(
            resolve_fernet_key(app_settings.encryption_key, app_settings.environment)
        )

    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        token: bytes = self._fernet.encrypt(str(secret).encode("utf-8"))
        return EncryptedChannelSecret(token.decode("ascii"))

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        try:
            plaintext: bytes = self._fernet.decrypt(str(encrypted_secret))
            return ChannelSecret(plaintext.decode("utf-8"))
        except (InvalidToken, ValueError, TypeError) as error:
            raise ValidationFailedError(
                "The stored channel secret cannot be decrypted with the current "
                "ENCRYPTION_KEY; reconnect the channel."
            ) from error


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

    if FERNET_KEY_PATTERN.fullmatch(secret_text) is not None:
        return secret_text.encode("ascii")

    if len(secret_text) < MIN_DERIVED_SECRET_LENGTH:
        if is_production:
            raise ValidationFailedError(
                f"ENCRYPTION_KEY must be a Fernet key or a secret of at least "
                f"{MIN_DERIVED_SECRET_LENGTH} characters in production."
            )

        logger.warning(
            "ENCRYPTION_KEY is shorter than %s characters; use a Fernet key or a "
            "long random secret outside development.",
            MIN_DERIVED_SECRET_LENGTH,
        )

    derived_key: bytes = HKDF(
        algorithm=hashes.SHA256(),
        length=FERNET_KEY_BYTES,
        salt=None,
        info=KEY_DERIVATION_INFO,
    ).derive(secret_text.encode("utf-8"))
    return base64.urlsafe_b64encode(derived_key)
