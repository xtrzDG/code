import logging

import pytest
from cryptography.fernet import Fernet

from app.adapters.security.secret_cipher_adapter import (
    PUBLIC_ENCRYPTION_KEYS,
    SecretCipherAdapter,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings

LONG_PASSPHRASE: str = "correct horse battery staple, Tbilisi 2026!"


def build_cipher(environment_variables: dict[str, str]) -> SecretCipherAdapter:
    return SecretCipherAdapter(assemble_app_settings(environment_variables))


@pytest.mark.parametrize(
    "secret",
    [
        "123456789:AAH-telegram-bot-token_example",
        "EAAG" + "x" * 200,
        "ტოკენი-ქართულად",
        "סוד-בעברית",
        "",
    ],
)
def test_round_trip_keeps_any_secret(secret: str) -> None:
    cipher = build_cipher({"ENCRYPTION_KEY": LONG_PASSPHRASE})

    encrypted = cipher.encrypt(ChannelSecret(secret))

    assert isinstance(encrypted, EncryptedChannelSecret)
    assert encrypted.isascii()
    if secret:
        assert secret not in encrypted
    assert cipher.decrypt(encrypted) == secret
    assert type(cipher.decrypt(encrypted)) is ChannelSecret


def test_each_encryption_uses_a_fresh_nonce() -> None:
    cipher = build_cipher({"ENCRYPTION_KEY": LONG_PASSPHRASE})

    first = cipher.encrypt(ChannelSecret("same token"))
    second = cipher.encrypt(ChannelSecret("same token"))

    assert first != second
    assert cipher.decrypt(first) == cipher.decrypt(second) == "same token"


def test_a_fernet_key_is_used_as_is() -> None:
    fernet_key = Fernet.generate_key()
    cipher = build_cipher({"ENCRYPTION_KEY": fernet_key.decode()})

    encrypted = cipher.encrypt(ChannelSecret("page-token"))

    assert Fernet(fernet_key).decrypt(encrypted.encode()) == b"page-token"
    foreign_token = Fernet(fernet_key).encrypt(b"from another service").decode()
    assert cipher.decrypt(EncryptedChannelSecret(foreign_token)) == (
        "from another service"
    )


def test_any_other_secret_is_derived_deterministically() -> None:
    first_process = build_cipher({"ENCRYPTION_KEY": LONG_PASSPHRASE})
    second_process = build_cipher({"ENCRYPTION_KEY": f"  {LONG_PASSPHRASE}  "})
    other_key = build_cipher({"ENCRYPTION_KEY": LONG_PASSPHRASE + "?"})

    encrypted = first_process.encrypt(ChannelSecret("whatsapp-token"))

    assert second_process.decrypt(encrypted) == "whatsapp-token"
    with pytest.raises(ValidationFailedError):
        other_key.decrypt(encrypted)


@pytest.mark.parametrize(
    "ciphertext",
    ["not-a-token", "", "токен", "gAAAAA" + "A" * 80],
)
def test_invalid_ciphertext_is_a_validation_error(ciphertext: str) -> None:
    cipher = build_cipher({"ENCRYPTION_KEY": LONG_PASSPHRASE})

    with pytest.raises(ValidationFailedError):
        cipher.decrypt(EncryptedChannelSecret(ciphertext))


def test_tampered_ciphertext_is_rejected() -> None:
    cipher = build_cipher({"ENCRYPTION_KEY": LONG_PASSPHRASE})
    encrypted = cipher.encrypt(ChannelSecret("bot-token"))
    replacement = "A" if encrypted[20] != "A" else "B"
    tampered = encrypted[:20] + replacement + encrypted[21:]

    with pytest.raises(ValidationFailedError):
        cipher.decrypt(EncryptedChannelSecret(tampered))


def test_production_refuses_to_start_without_a_strong_key() -> None:
    with pytest.raises(ValidationFailedError, match="ENCRYPTION_KEY"):
        build_cipher({"APP_ENV": "production"})
    with pytest.raises(ValidationFailedError, match="ENCRYPTION_KEY"):
        build_cipher({"APP_ENV": "production", "ENCRYPTION_KEY": "short-secret"})

    production_cipher = build_cipher(
        {"APP_ENV": "production", "ENCRYPTION_KEY": LONG_PASSPHRASE}
    )
    encrypted = production_cipher.encrypt(ChannelSecret("token"))
    assert production_cipher.decrypt(encrypted) == "token"


def test_production_refuses_the_public_compose_key() -> None:
    for public_key in PUBLIC_ENCRYPTION_KEYS:
        with pytest.raises(ValidationFailedError, match="docker-compose"):
            build_cipher({"APP_ENV": "production", "ENCRYPTION_KEY": public_key})
        with pytest.raises(ValidationFailedError, match="docker-compose"):
            build_cipher(
                {"APP_ENV": "production", "ENCRYPTION_KEY": f"  {public_key} "}
            )

        # A local run keeps working with it.
        development_cipher = build_cipher({"ENCRYPTION_KEY": public_key})
        encrypted = development_cipher.encrypt(ChannelSecret("token"))
        assert development_cipher.decrypt(encrypted) == "token"


def test_development_without_a_key_uses_a_temporary_one_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        first_cipher = build_cipher({})
        second_cipher = build_cipher({})
        short_key_cipher = build_cipher({"ENCRYPTION_KEY": "dev"})

    encrypted = first_cipher.encrypt(ChannelSecret("token"))
    assert first_cipher.decrypt(encrypted) == "token"
    with pytest.raises(ValidationFailedError):
        second_cipher.decrypt(encrypted)
    assert short_key_cipher.decrypt(short_key_cipher.encrypt(ChannelSecret("x"))) == "x"
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "temporary key" in messages
    assert "shorter than 32 characters" in messages
