"""RECORDINGS_STORAGE and RECORDINGS_S3_*: where call recordings are kept."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.storage import RecordingStorageKind
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_strings import (
    ObjectStorageBucketName,
    ObjectStorageRegion,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    parse_setting,
    read_text,
)

OBJECT_STORAGE_VARIABLES: tuple[str, ...] = (
    "RECORDINGS_S3_ENDPOINT_URL",
    "RECORDINGS_S3_REGION",
    "RECORDINGS_S3_BUCKET",
    "RECORDINGS_S3_ACCESS_KEY_ID",
    "RECORDINGS_S3_SECRET_ACCESS_KEY",
)


class RecordingStorageSettingsSection(TypedDict):
    """The `AppSettings` fields of the recording storage."""

    recording_storage_kind: RecordingStorageKind
    recordings_object_storage: ObjectStorageConnection | None


def read_recording_storage_settings(
    environment_variables: Mapping[str, str],
    has_encryption_key: bool,
) -> RecordingStorageSettingsSection:
    """
    Local files by default (development); `s3` needs every RECORDINGS_S3_*
    variable and ENCRYPTION_KEY (recordings are encrypted with keys derived
    from it), or the start is refused with the names of what is missing.
    """

    kind: RecordingStorageKind = parse_setting(
        "RECORDINGS_STORAGE",
        read_text(
            environment_variables, "RECORDINGS_STORAGE", RecordingStorageKind.LOCAL
        ),
        RecordingStorageKind,
    )
    endpoint_url = optional_setting(
        environment_variables, "RECORDINGS_S3_ENDPOINT_URL", PublicBaseUrl
    )
    region = optional_setting(
        environment_variables, "RECORDINGS_S3_REGION", ObjectStorageRegion
    )
    bucket = optional_setting(
        environment_variables, "RECORDINGS_S3_BUCKET", ObjectStorageBucketName
    )
    access_key_id = optional_setting(
        environment_variables, "RECORDINGS_S3_ACCESS_KEY_ID", PlatformIdentifier
    )
    secret_access_key = optional_setting(
        environment_variables, "RECORDINGS_S3_SECRET_ACCESS_KEY", PlatformSecret
    )
    if kind is RecordingStorageKind.LOCAL:
        return RecordingStorageSettingsSection(
            recording_storage_kind=kind, recordings_object_storage=None
        )

    values = (endpoint_url, region, bucket, access_key_id, secret_access_key)
    missing: list[str] = [
        name
        for name, value in zip(OBJECT_STORAGE_VARIABLES, values, strict=True)
        if value is None
    ]
    if not has_encryption_key:
        missing.append("ENCRYPTION_KEY")
    if (
        missing
        or endpoint_url is None
        or region is None
        or bucket is None
        or access_key_id is None
        or secret_access_key is None
    ):
        raise ValidationFailedError(
            "RECORDINGS_STORAGE=s3 needs " + ", ".join(missing) + "."
        )

    return RecordingStorageSettingsSection(
        recording_storage_kind=kind,
        recordings_object_storage=ObjectStorageConnection(
            endpoint_url=endpoint_url,
            region=region,
            bucket=bucket,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        ),
    )
