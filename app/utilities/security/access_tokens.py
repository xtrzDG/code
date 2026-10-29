"""Bearer access tokens: generation and the stored hash.

A token carries 256 random bits, so a fast unsalted SHA-256 is enough to
make a leaked session table useless; the token itself is never stored.
"""

import secrets
from hashlib import sha256

from app.schemas.typings.users.strings import AccessToken, AccessTokenHash

ACCESS_TOKEN_RANDOM_BYTES: int = 32


def generate_access_token() -> AccessToken:
    """Return a new URL-safe bearer token with 256 random bits."""

    return AccessToken(secrets.token_urlsafe(ACCESS_TOKEN_RANDOM_BYTES))


def hash_access_token(access_token: AccessToken) -> AccessTokenHash:
    """Return the SHA-256 hex digest of a token, the only stored form."""

    return AccessTokenHash(sha256(str(access_token).encode("utf-8")).hexdigest())
