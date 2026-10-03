"""BACKUP_* and RESTORE_CHECK_DATABASE_URL in the settings."""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.age.age_keys import generate_identity, recipient_of

IDENTITY = generate_identity()
BUCKET: dict[str, str] = {
    "BACKUP_S3_ENDPOINT_URL": "https://s3.eu-central-1.amazonaws.com",
    "BACKUP_S3_REGION": "eu-central-1",
    "BACKUP_S3_BUCKET": "workshop-backups-eu",
    "BACKUP_S3_ACCESS_KEY_ID": "AKIAEXAMPLE",
    "BACKUP_S3_SECRET_ACCESS_KEY": "example-secret",  # gitleaks:allow
}


def test_backups_are_off_by_default() -> None:
    backup = assemble_app_settings({}).backup

    assert backup.bucket is None
    assert backup.recipients == []
    assert str(backup.prefix) == "workshop/"
    assert (int(backup.daily_copies), int(backup.monthly_copies)) == (30, 12)
    assert int(backup.max_age_hours) == 26


def test_a_full_configuration_is_read() -> None:
    escrow = generate_identity()
    public_keys: str = f" {recipient_of(IDENTITY)} , {recipient_of(escrow)}"
    backup = assemble_app_settings(
        {
            **BUCKET,
            "BACKUP_S3_PREFIX": "prod/workshop/",
            "BACKUP_AGE_PUBLIC_KEY": public_keys,
            "BACKUP_AGE_IDENTITY": str(IDENTITY),
            "BACKUP_KEEP_DAILY": "14",
            "BACKUP_KEEP_MONTHLY": "24",
            "BACKUP_MAX_AGE_HOURS": "50",
            "RESTORE_CHECK_DATABASE_URL": "postgresql://drill@localhost/postgres",
            "POSTGRES_CLIENT_BIN_DIRECTORY": "/usr/lib/postgresql/17/bin",
        }
    ).backup

    assert backup.bucket is not None
    assert str(backup.bucket.bucket) == "workshop-backups-eu"
    assert str(backup.prefix) == "prod/workshop/"
    assert backup.recipients == [recipient_of(IDENTITY), recipient_of(escrow)]
    assert backup.identity == IDENTITY
    assert (int(backup.daily_copies), int(backup.monthly_copies)) == (14, 24)
    assert int(backup.max_age_hours) == 50
    assert str(backup.restore_check_database_url).startswith("postgresql://")
    assert str(IDENTITY) not in repr(backup)


def test_a_bucket_configured_in_part_names_what_is_missing() -> None:
    partial = {k: v for k, v in BUCKET.items() if k != "BACKUP_S3_REGION"}

    with pytest.raises(ValidationFailedError, match="needs BACKUP_S3_REGION"):
        assemble_app_settings(
            {**partial, "BACKUP_AGE_PUBLIC_KEY": str(recipient_of(IDENTITY))}
        )


def test_a_bucket_without_a_public_key_is_refused() -> None:
    with pytest.raises(ValidationFailedError, match="always encrypted"):
        assemble_app_settings(BUCKET)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BACKUP_AGE_PUBLIC_KEY", "ssh-ed25519 AAAA"),
        ("BACKUP_AGE_IDENTITY", "AGE-SECRET-KEY-1NOPE"),
        ("BACKUP_S3_PREFIX", "/absolute"),
        ("BACKUP_KEEP_DAILY", "0"),
        ("BACKUP_MAX_AGE_HOURS", "100000"),
    ],
)
def test_invalid_values_name_their_variable(name: str, value: str) -> None:
    with pytest.raises(ValidationFailedError, match=name):
        assemble_app_settings({name: value})
