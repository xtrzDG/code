"""
Which archives retention keeps: the newest backup of each of the last
BACKUP_KEEP_DAILY days that have one, and the newest of each of the last
BACKUP_KEEP_MONTHLY months (UTC). With the defaults, 30 daily and 12
monthly copies: a month of day-by-day restore points and a year of
month-end ones. The newest archive is always kept.
"""

from collections.abc import Callable
from datetime import datetime

from app.schemas.dto.backups import BackupArchive
from app.schemas.typings.backups.constrained_integers import BackupCopyCount
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.utilities.backups.backup_keys import to_datetime


def select_kept_archives(
    archives: list[BackupArchive],
    daily_copies: BackupCopyCount,
    monthly_copies: BackupCopyCount,
) -> set[BackupObjectKey]:
    if not archives:
        return set()

    newest_first: list[BackupArchive] = sorted(
        archives, key=lambda archive: int(archive.created_at), reverse=True
    )
    kept: set[BackupObjectKey] = {newest_first[0].key}
    kept |= newest_per_period(newest_first, int(daily_copies), day_of)
    kept |= newest_per_period(newest_first, int(monthly_copies), month_of)
    return kept


def newest_per_period(
    newest_first: list[BackupArchive],
    period_count: int,
    period_of: Callable[[datetime], str],
) -> set[BackupObjectKey]:
    """The newest archive of each of the `period_count` latest periods."""

    kept: dict[str, BackupObjectKey] = {}
    for archive in newest_first:
        period: str = period_of(to_datetime(archive.created_at))
        if period in kept:
            continue

        if len(kept) == period_count:
            break

        kept[period] = archive.key

    return set(kept.values())


def day_of(moment: datetime) -> str:
    return f"{moment:%Y-%m-%d}"


def month_of(moment: datetime) -> str:
    return f"{moment:%Y-%m}"
