"""ENCRYPTION_KEYS and ENCRYPTION_KEY: the platform's key ring."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    read_raw_list,
)


class EncryptionKeySettingsSection(TypedDict):
    """The `AppSettings` fields of the key ring."""

    encryption_key: PlatformSecret | None
    previous_encryption_keys: list[PlatformSecret]


def read_encryption_key_settings(
    environment_variables: Mapping[str, str],
) -> EncryptionKeySettingsSection:
    """
    ENCRYPTION_KEYS lists the keys newest first; ENCRYPTION_KEY, when set
    and not listed already, follows as the oldest. The first key encrypts
    and signs everything new; the others only open and verify what they
    sealed before, until `rotate_encrypted_secrets` moved it to the first
    key (docs/operations/backup-restore.md, "Key rotation").
    """

    ring: list[PlatformSecret] = [
        PlatformSecret(key)
        for key in read_raw_list(environment_variables, "ENCRYPTION_KEYS")
    ]
    fallback: PlatformSecret | None = optional_text(
        environment_variables, "ENCRYPTION_KEY", PlatformSecret
    )
    if fallback is not None and fallback not in ring:
        ring.append(fallback)

    return EncryptionKeySettingsSection(
        encryption_key=ring[0] if ring else None,
        previous_encryption_keys=list(dict.fromkeys(ring[1:])),
    )
