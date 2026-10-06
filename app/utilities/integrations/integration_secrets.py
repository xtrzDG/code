"""
The secrets of the public API and webhooks: API keys (shown once, stored
as SHA-256) and webhook signing secrets (shown once, stored sealed).
"""

import base64
import hashlib
import secrets
import string

from app.schemas.typings.integrations.constrained_strings import (
    ApiKeyPrefix,
    ApiKeySecretHash,
    ApiKeyToken,
    WebhookSecretHint,
    WebhookSigningSecret,
)

API_KEY_MARK: str = "awk_"
SIGNING_SECRET_MARK: str = "whsec_"
API_KEY_SECRET_LENGTH: int = 40
API_KEY_ALPHABET: str = string.ascii_letters + string.digits
# 5 random bytes are 8 characters of base32 (40 bits): the public prefix.
PREFIX_RANDOM_BYTES: int = 5
SIGNING_SECRET_BYTES: int = 32
HINT_LENGTH: int = 4


def new_api_key() -> tuple[ApiKeyToken, ApiKeyPrefix]:
    """A fresh key (`awk_<8>_<40>`, about 280 random bits) and its prefix."""

    prefix = ApiKeyPrefix(
        API_KEY_MARK
        + base64.b32encode(secrets.token_bytes(PREFIX_RANDOM_BYTES)).decode().lower()
    )
    secret_part: str = "".join(
        secrets.choice(API_KEY_ALPHABET) for _ in range(API_KEY_SECRET_LENGTH)
    )
    return ApiKeyToken(f"{prefix}_{secret_part}"), prefix


def hash_api_key(token: ApiKeyToken) -> ApiKeySecretHash:
    """
    What is stored and looked up. A plain SHA-256 is enough: the key is
    random and long, so it cannot be guessed from its hash.
    """

    return ApiKeySecretHash(hashlib.sha256(str(token).encode()).hexdigest())


def new_signing_secret() -> tuple[WebhookSigningSecret, WebhookSecretHint]:
    """A fresh signing secret and its last four characters."""

    secret = WebhookSigningSecret(
        SIGNING_SECRET_MARK + secrets.token_urlsafe(SIGNING_SECRET_BYTES)
    )
    return secret, WebhookSecretHint(str(secret)[-HINT_LENGTH:])
