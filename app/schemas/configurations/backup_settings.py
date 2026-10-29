from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.typings.backups.constrained_integers import (
    BackupCopyCount,
    BackupFreshnessHours,
)
from app.schemas.typings.backups.constrained_strings import (
    AgeIdentity,
    AgeRecipient,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import DatabaseUrl, LocalDirectoryPath


class BackupSettings(ImmutableDTO):
    """
    Off-site database backups and the restore drill
    (docs/operations/backup-restore.md). Production's backup job needs the
    bucket and the public keys only; the private identity and the drill's
    throwaway server belong to wherever the drill runs.
    """

    # The EU bucket (BACKUP_S3_*); None: backups are not configured.
    bucket: ObjectStorageConnection | None = None
    prefix: BackupObjectPrefix = BackupObjectPrefix("workshop/")
    # Who can open an archive (BACKUP_AGE_PUBLIC_KEY): the drill's key and
    # the offline escrow key.
    recipients: list[AgeRecipient] = Field(default_factory=list[AgeRecipient])
    identity: AgeIdentity | None = Field(default=None, repr=False)
    daily_copies: BackupCopyCount = BackupCopyCount(30)
    monthly_copies: BackupCopyCount = BackupCopyCount(12)
    max_age_hours: BackupFreshnessHours = BackupFreshnessHours(26)
    restore_check_database_url: DatabaseUrl | None = Field(default=None, repr=False)
    postgres_client_directory: LocalDirectoryPath | None = None
