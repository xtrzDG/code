from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import MaintenanceRunKind, MaintenanceRunOutcome
from app.schemas.typings.backups.constrained_integers import BackupArchiveSize
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.schemas.typings.monitoring.constrained_integers import ArchivedRowCount
from app.schemas.typings.monitoring.prefixed_id import MaintenanceRunId
from app.schemas.typings.monitoring.strings import MaintenanceErrorText
from app.schemas.typings.platform.constrained_strings import ReleaseVersion


class MaintenanceRunDocument(BaseDocument):
    """
    One off-site backup (`workshop backup`) or restore drill (`workshop
    restore-check`) as it ended, recorded by the command in the database it
    serves (a platform collection), so the admin system page shows the
    last of each and how old it is.

    `archive_key`, `archive_size` and `row_count` describe the archive a
    backup uploaded or a drill restored; `error` is why a failed run failed.
    """

    id: MaintenanceRunId = Field(default_factory=MaintenanceRunId)
    kind: MaintenanceRunKind
    outcome: MaintenanceRunOutcome
    started_at: Microseconds
    finished_at: Microseconds
    archive_key: BackupObjectKey | None = None
    archive_size: BackupArchiveSize | None = None
    row_count: ArchivedRowCount | None = None
    error: MaintenanceErrorText | None = None
    release: ReleaseVersion | None = None
