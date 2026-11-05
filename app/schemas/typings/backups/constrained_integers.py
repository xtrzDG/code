"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BackupArchiveSize(BaseConstrainedTypedInt):
    """The size of an encrypted backup archive in the bucket, in bytes."""

    ge = 0


class BackupCopyCount(BaseConstrainedTypedInt):
    """
    How many backups one retention tier keeps: the newest of each of that
    many recent days (BACKUP_KEEP_DAILY) or months (BACKUP_KEEP_MONTHLY).
    """

    ge = 1
    le = 1000


class BackupFreshnessHours(BaseConstrainedTypedInt):
    """
    How old the newest backup may be before the restore drill fails
    (BACKUP_MAX_AGE_HOURS): a day and a bit for the daily backup job.
    """

    ge = 1
    le = 8760


class DatabasePolicyCount(BaseConstrainedTypedInt):
    """How many row-level security policies a database has."""

    ge = 0


class TableRowCount(BaseConstrainedTypedInt):
    """How many rows one table of the database holds."""

    ge = 0


# Keep abc order for all non example types, if possible.
