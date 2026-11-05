"""BACKUP_*, RESTORE_CHECK_DATABASE_URL: off-site backups and the restore drill."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.backup_settings import BackupSettings
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.backups.constrained_integers import (
    BackupCopyCount,
    BackupFreshnessHours,
)
from app.schemas.typings.backups.constrained_strings import (
    AgeIdentity,
    AgeRecipient,
    BackupObjectPrefix,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_strings import (
    ObjectStorageBucketName,
    ObjectStorageRegion,
)
from app.schemas.typings.platform.strings import (
    DatabaseUrl,
    LocalDirectoryPath,
    PlatformIdentifier,
    PlatformSecret,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    optional_text,
    parse_setting,
    read_integer,
    read_raw_list,
    read_text,
)

BUCKET_VARIABLES: tuple[str, ...] = (
    "BACKUP_S3_ENDPOINT_URL",
    "BACKUP_S3_REGION",
    "BACKUP_S3_BUCKET",
    "BACKUP_S3_ACCESS_KEY_ID",
    "BACKUP_S3_SECRET_ACCESS_KEY",
)


class BackupSettingsSection(TypedDict):
    """The `AppSettings` field of the backups."""

    backup: BackupSettings


def read_backup_settings(
    environment_variables: Mapping[str, str],
) -> BackupSettingsSection:
    """
    Backups are off until the bucket is configured; a bucket configured in
    part is refused with the names of what is missing, and so is a bucket
    without a public key (archives are never stored unencrypted).
    """

    bucket: ObjectStorageConnection | None = read_bucket(environment_variables)
    recipients: list[AgeRecipient] = [
        parse_setting("BACKUP_AGE_PUBLIC_KEY", item, AgeRecipient)
        for item in read_raw_list(environment_variables, "BACKUP_AGE_PUBLIC_KEY")
    ]
    if bucket is not None and not recipients:
        raise ValidationFailedError(
            "BACKUP_S3_* needs BACKUP_AGE_PUBLIC_KEY: backups are always encrypted."
        )

    return BackupSettingsSection(
        backup=BackupSettings(
            bucket=bucket,
            prefix=parse_setting(
                "BACKUP_S3_PREFIX",
                read_text(environment_variables, "BACKUP_S3_PREFIX", "workshop/"),
                BackupObjectPrefix,
            ),
            recipients=recipients,
            identity=optional_setting(
                environment_variables, "BACKUP_AGE_IDENTITY", AgeIdentity
            ),
            daily_copies=parse_setting(
                "BACKUP_KEEP_DAILY",
                read_integer(environment_variables, "BACKUP_KEEP_DAILY", 30),
                BackupCopyCount,
            ),
            monthly_copies=parse_setting(
                "BACKUP_KEEP_MONTHLY",
                read_integer(environment_variables, "BACKUP_KEEP_MONTHLY", 12),
                BackupCopyCount,
            ),
            max_age_hours=parse_setting(
                "BACKUP_MAX_AGE_HOURS",
                read_integer(environment_variables, "BACKUP_MAX_AGE_HOURS", 26),
                BackupFreshnessHours,
            ),
            restore_check_database_url=optional_text(
                environment_variables, "RESTORE_CHECK_DATABASE_URL", DatabaseUrl
            ),
            postgres_client_directory=optional_text(
                environment_variables,
                "POSTGRES_CLIENT_BIN_DIRECTORY",
                LocalDirectoryPath,
            ),
        )
    )


def read_bucket(
    environment_variables: Mapping[str, str],
) -> ObjectStorageConnection | None:
    endpoint_url = optional_setting(
        environment_variables, "BACKUP_S3_ENDPOINT_URL", PublicBaseUrl
    )
    region = optional_setting(
        environment_variables, "BACKUP_S3_REGION", ObjectStorageRegion
    )
    bucket = optional_setting(
        environment_variables, "BACKUP_S3_BUCKET", ObjectStorageBucketName
    )
    access_key_id = optional_setting(
        environment_variables, "BACKUP_S3_ACCESS_KEY_ID", PlatformIdentifier
    )
    secret_access_key = optional_setting(
        environment_variables, "BACKUP_S3_SECRET_ACCESS_KEY", PlatformSecret
    )
    values = (endpoint_url, region, bucket, access_key_id, secret_access_key)
    if all(value is None for value in values):
        return None

    missing: list[str] = [
        name
        for name, value in zip(BUCKET_VARIABLES, values, strict=True)
        if value is None
    ]
    if (
        missing
        or endpoint_url is None
        or region is None
        or bucket is None
        or access_key_id is None
        or secret_access_key is None
    ):
        raise ValidationFailedError(
            "The backup bucket needs " + ", ".join(missing) + " as well."
        )

    return ObjectStorageConnection(
        endpoint_url=endpoint_url,
        region=region,
        bucket=bucket,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )
