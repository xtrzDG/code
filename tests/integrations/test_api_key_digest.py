"""An API key is stored as a salted scrypt digest, never as the key."""

import hashlib

from app.schemas.typings.integrations.constrained_strings import ApiKeyToken
from app.utilities.integrations.integration_secrets import hash_api_key, new_api_key

KEY: ApiKeyToken = ApiKeyToken("awk_abcd2345_" + "A" * 40)
SAME_SECRET_OTHER_PREFIX: ApiKeyToken = ApiKeyToken("awk_wxyz2345_" + "A" * 40)


def test_the_digest_is_scrypt_salted_with_the_keys_prefix() -> None:
    expected: str = hashlib.scrypt(
        str(KEY).encode(),
        salt=b"assistant-workshop/api-key/awk_abcd2345",
        n=2**12,
        r=8,
        p=1,
        dklen=32,
    ).hex()

    assert str(hash_api_key(KEY)) == expected


def test_one_key_always_gives_one_digest_and_two_keys_two() -> None:
    token, _prefix = new_api_key()

    assert hash_api_key(token) == hash_api_key(token)
    assert hash_api_key(token) != hash_api_key(KEY)
    assert hash_api_key(KEY) != hash_api_key(SAME_SECRET_OTHER_PREFIX)


def test_the_digest_does_not_contain_the_key() -> None:
    digest: str = str(hash_api_key(KEY))

    assert len(digest) == 64
    assert "A" * 8 not in digest
    assert "abcd2345" not in digest
