"""A backup or restore drill as the command that ran it reports it."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import MaintenanceRunKind, MaintenanceRunOutcome
from app.schemas.typings.backups.constrained_integers import BackupArchiveSize
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.schemas.typings.monitoring.constrained_integers import ArchivedRowCount
from app.schemas.typings.monitoring.strings import MaintenanceErrorText


class RecordMaintenanceRunCommand(ImmutableDTO):
    """
    `workshop backup` or `workshop restore-check` ended: when it ran, how it
    ended, the archive it uploaded or restored (its key, size and rows),
    and why it failed.
    """

    kind: MaintenanceRunKind
    outcome: MaintenanceRunOutcome
    started_at: Microseconds
    finished_at: Microseconds
    archive_key: BackupObjectKey | None = None
    archive_size: BackupArchiveSize | None = None
    row_count: ArchivedRowCount | None = None
    error: MaintenanceErrorText | None = None
