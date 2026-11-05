"""
The key ring (ENCRYPTION_KEYS, then ENCRYPTION_KEY): decrypt with the old
key, rotate to the new one, drop the old key.
"""

import pytest

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.key_ring import key_ring

OLD_KEY: str = "old-key-of-the-platform-0123456789abcdef"
NEW_KEY: str = "new-key-of-the-platform-fedcba9876543210"
TOKEN: ChannelSecret = ChannelSecret("123456789:AAH-telegram-bot-token")


def cipher(environment: dict[str, str]) -> SecretCipherAdapter:
    return SecretCipherAdapter(assemble_app_settings(environment))


@pytest.mark.parametrize(
    ("environment", "ring"),
    [
        ({}, []),
        ({"ENCRYPTION_KEY": OLD_KEY}, [OLD_KEY]),
        ({"ENCRYPTION_KEYS": NEW_KEY}, [NEW_KEY]),
        (
            {"ENCRYPTION_KEYS": f" {NEW_KEY} ,", "ENCRYPTION_KEY": OLD_KEY},
            [NEW_KEY, OLD_KEY],
        ),
        (
            {"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}", "ENCRYPTION_KEY": OLD_KEY},
            [NEW_KEY, OLD_KEY],
        ),
        ({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY},{OLD_KEY}"}, [NEW_KEY, OLD_KEY]),
    ],
)
def test_the_ring_lists_the_newest_key_first(
    environment: dict[str, str], ring: list[str]
) -> None:
    assert key_ring(assemble_app_settings(environment)) == [
        PlatformSecret(key) for key in ring
    ]


def test_decrypt_with_the_old_key_rotate_then_drop_the_old_key() -> None:
    before = cipher({"ENCRYPTION_KEY": OLD_KEY})
    during = cipher({"ENCRYPTION_KEYS": NEW_KEY, "ENCRYPTION_KEY": OLD_KEY})
    after = cipher({"ENCRYPTION_KEYS": NEW_KEY})
    stored = before.encrypt(TOKEN)

    assert int(during.key_count()) == 2
    assert during.decrypt(stored) == TOKEN
    assert not during.is_current(stored)
    rotated = during.rotate(stored)
    assert during.is_current(rotated)
    assert during.rotate(rotated) != rotated  # re-sealed, still current
    assert after.decrypt(rotated) == TOKEN
    assert after.is_current(rotated)
    with pytest.raises(ValidationFailedError, match="any key of"):
        after.decrypt(stored)
    with pytest.raises(ValidationFailedError, match="any key of"):
        after.rotate(stored)
    assert not after.is_current(stored)


def test_new_secrets_are_sealed_with_the_newest_key() -> None:
    during = cipher({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})

    sealed = during.encrypt(TOKEN)

    assert cipher({"ENCRYPTION_KEYS": NEW_KEY}).decrypt(sealed) == TOKEN
    with pytest.raises(ValidationFailedError):
        cipher({"ENCRYPTION_KEY": OLD_KEY}).decrypt(sealed)


def test_production_refuses_a_weak_or_public_key_anywhere_in_the_ring() -> None:
    production = {"APP_ENV": "production", "ENCRYPTION_KEYS": NEW_KEY}

    with pytest.raises(ValidationFailedError, match="public default"):
        cipher(
            {**production, "ENCRYPTION_KEY": "local-compose-key-for-this-machine-only"}
        )
    with pytest.raises(ValidationFailedError, match="at least 32"):
        cipher({**production, "ENCRYPTION_KEY": "short"})
    assert int(cipher(production).key_count()) == 1
