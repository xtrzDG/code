"""
Guessing API keys costs the guesser, not the platform: a client network
that sent too many keys that are not valid is refused before the next
key's scrypt digest is computed, and a found key must match its digest in
full (a constant-time comparison), whatever the store's lookup answered.
"""

import pytest

from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.typings.integrations.constrained_strings import (
    ApiKeySecretHash,
    ApiKeyToken,
)
from app.use_cases.integrations import authenticate_api_key_use_case
from app.use_cases.integrations.authenticate_api_key_use_case import (
    REFUSED_KEYS_PER_NETWORK,
)
from app.utilities.integrations.integration_secrets import hash_api_key
from tests.integrations.integration_shop import open_integration_shop

GUESS_PREFIX: str = "awk_abcd2345_"


def guess(number: int) -> str:
    return f"{GUESS_PREFIX}{number:040d}"


def test_a_network_guessing_keys_is_stopped_before_the_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digests: list[str] = []

    def counting_digest(token: ApiKeyToken) -> ApiKeySecretHash:
        digests.append(str(token))
        return hash_api_key(token)

    monkeypatch.setattr(authenticate_api_key_use_case, "hash_api_key", counting_digest)
    with open_integration_shop() as shop:
        token = shop.add_api_key()
        guesses = {
            shop.api("GET", "/me", guess(number)).status_code
            for number in range(int(REFUSED_KEYS_PER_NETWORK))
        }
        computed = len(digests)
        stopped = shop.api("GET", "/me", guess(999))
        valid_meanwhile = shop.api("GET", "/me", token)
        computed_after = len(digests)
        shop.workshop.clock.advance(121)
        later = shop.api("GET", "/me", token)

    assert guesses == {401}
    assert computed == int(REFUSED_KEYS_PER_NETWORK)
    assert stopped.status_code == 429
    assert stopped.json()["error"] == "rate_limited"
    assert int(stopped.headers["Retry-After"]) >= 1
    # Over the budget even a valid key waits (no digest is computed at all).
    assert valid_meanwhile.status_code == 429
    assert computed_after == computed
    assert later.status_code == 200, later.text


def test_valid_keys_do_not_use_the_budget() -> None:
    with open_integration_shop() as shop:
        token = shop.add_api_key()
        answers = {
            shop.api("GET", "/me", token).status_code
            for _ in range(int(REFUSED_KEYS_PER_NETWORK) + 5)
        }

    assert answers == {200}


def test_a_found_key_must_match_its_digest_in_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A store whose lookup matched loosely still lets no other key in."""

    exact_lookup = ApiKeyRepository.find_by_secret_hash
    seen: list[ApiKeyDocument] = []

    def loose_lookup(
        repository: ApiKeyRepository, secret_hash: ApiKeySecretHash
    ) -> ApiKeyDocument | None:
        exact: ApiKeyDocument | None = exact_lookup(repository, secret_hash)
        if exact is not None:
            seen.append(exact)
        return exact or (seen[-1] if seen else None)

    monkeypatch.setattr(ApiKeyRepository, "find_by_secret_hash", loose_lookup)
    with open_integration_shop() as shop:
        token = shop.add_api_key()
        own = shop.api("GET", "/me", token)
        other = shop.api("GET", "/me", guess(1))

    assert own.status_code == 200, own.text
    assert seen != []
    assert other.status_code == 401
