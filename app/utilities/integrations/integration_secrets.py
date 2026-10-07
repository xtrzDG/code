"""
The secrets of the public API and webhooks: API keys (shown once, stored
as a scrypt digest) and webhook signing secrets (shown once, stored
sealed).
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
PREFIX_LENGTH: int = 8
SIGNING_SECRET_BYTES: int = 32
HINT_LENGTH: int = 4
# scrypt of the whole key, salted with its public prefix (unique per key, so
# the digest stays one indexed lookup). A key has about 280 random bits, so
# the cost only has to keep a request quick: about 10 ms and 4 MiB.
KEY_DIGEST_SALT_LABEL: bytes = b"assistant-workshop/api-key/"
KEY_DIGEST_COST: int = 2**12
KEY_DIGEST_BLOCK_SIZE: int = 8
KEY_DIGEST_PARALLELISM: int = 1
KEY_DIGEST_BYTES: int = 32


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
    What is stored and looked up: the hex scrypt digest of the whole key,
    salted with the key's prefix. The same key always gives the same
    digest; a leaked digest gives nothing usable.
    """

    text: str = str(token)
    prefix: str = text[: len(API_KEY_MARK) + PREFIX_LENGTH]
    digest: bytes = hashlib.scrypt(
        text.encode(),
        salt=KEY_DIGEST_SALT_LABEL + prefix.encode(),
        n=KEY_DIGEST_COST,
        r=KEY_DIGEST_BLOCK_SIZE,
        p=KEY_DIGEST_PARALLELISM,
        dklen=KEY_DIGEST_BYTES,
    )
    return ApiKeySecretHash(digest.hex())


def new_signing_secret() -> tuple[WebhookSigningSecret, WebhookSecretHint]:
    """A fresh signing secret and its last four characters."""

    secret = WebhookSigningSecret(
        SIGNING_SECRET_MARK + secrets.token_urlsafe(SIGNING_SECRET_BYTES)
    )
    return secret, WebhookSecretHint(str(secret)[-HINT_LENGTH:])
